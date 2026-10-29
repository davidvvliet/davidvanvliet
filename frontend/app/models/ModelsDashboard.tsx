"use client";

import { Component, ReactNode, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { OrbitControls, useGLTF } from "@react-three/drei";
import StudioLights from "./StudioLights";
import styles from "./models.module.css";

type Check = { name: string; ok: boolean; measured: number | null; expected: number; unit: string; detail?: string; source?: string | null };
type Build = {
  started: number; ok?: boolean; error?: string; seconds?: number; checks?: Check[];
  sheet?: string; glb?: string; grid_m?: Record<string, number>; size_m?: number[];
  history?: string[]; baseline?: { diff: number; changed: boolean } | null; approved?: number;
  closeups?: string[];
};
type Probe = {
  name: string; title: string; fixture: boolean; note: string | null;
  kind?: "circuit"; // a /circuit board (scripts/circuit/build.py): no sheet, its blocks instead
  sources: { title?: string; url?: string }[]; referenceModel: { url?: string; note?: string } | null;
  // Each git worktree that has this probe, newest build first (app/api/models/[...path]/route.ts).
  worktrees: Source[];
  // Never approved: null. Else what changed since approve (scripts/blender/lib/published.py).
  published: { own: string[]; shared: string[] } | null;
};
// out/<probe>/ref/explode.json, written by `run.py explode` (the reference split into our parts).
type Breakdown = {
  build_started: number | null;
  families: Record<string, { ref: { pieces: number; size: number[] } | null; centre_offset?: number[]; ours: { size: number[] } }>;
};
// `working`: that worktree has changes to the probe's own files (someone is working on it there).
type Source = { worktree: string; label: string; branch: string | null; working: boolean; build: Build | null; refs: string[] };
type Current = { probe: string; step: string; state: string; message: string | null; session: string; at: number; worktree: string; label: string };
type Status = { updated: number | null; current: Current | null; probes: Probe[] };

const STEPS = ["spec", "model", "checks", "render", "export", "done"];
const SELECTED_KEY = "models-dashboard-probe";
const file = (worktree: string, rel: string, v?: number) => `/api/models/file/${worktree}/${rel}${v ? `?v=${v}` : ""}`;

function ago(t: number, now: number) {
  const s = Math.max(0, Math.round(now / 1000 - t));
  return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)}m ago` : `${Math.round(s / 3600)}h ago`;
}

// Part family, as explode.py groups them: rtg_1 and rtg_1_fins -> rtg, feed_leg_3 -> feed_leg.
const family = (name: string) => name.replace(/_fins$/, "").replace(/_\d+$/, "");

// A part's group: the assembly it was built in (glTF extras, from parts.assembly), else for
// untagged models its top-level node's name family.
const tagged = (o: THREE.Object3D) => {
  for (let x: THREE.Object3D | null = o; x; x = x.parent) if (typeof x.userData.assembly === "string") return x;
  return null;
};
function groupOf(o: THREE.Object3D, scene: THREE.Object3D) {
  const t = tagged(o);
  if (t) return t.userData.assembly as string;
  while (o.parent && o.parent !== scene) o = o.parent;
  return family(o.name);
}

// A unit is one node that moves when exploding: an assembly's outermost node (its parent
// is in another assembly or is the scene), or a top-level node of an untagged model.
type Unit = { node: THREE.Object3D; rest: THREE.Vector3; group: string; local: THREE.Vector3 };
type Part = { group: string; meshes: THREE.Mesh[] };

// Each group is pushed away from the core (the assembly tagged core, else "bus", else the
// largest group): a fixed step plus a share of its distance, capped so parts stay in view.
function useParts(scene: THREE.Object3D) {
  return useMemo(() => {
    scene.updateMatrixWorld(true);
    const parts = new Map<string, Part>();
    const boxes = new Map<string, THREE.Box3>();
    let core: string | null = null;
    scene.traverse((o) => {
      if (o.userData.core && typeof o.userData.assembly === "string") core = o.userData.assembly;
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      // Parts share materials ("black" etc.): give each mesh its own so a highlight stays on one part.
      m.material = Array.isArray(m.material) ? m.material.map((x) => x.clone()) : m.material.clone();
      const g = groupOf(m, scene);
      const p = parts.get(g) ?? { group: g, meshes: [] };
      p.meshes.push(m);
      parts.set(g, p);
      const box = boxes.get(g) ?? new THREE.Box3();
      boxes.set(g, box.union(new THREE.Box3().setFromObject(m)));
    });
    let largest = "", size = -1;
    for (const [g, b] of boxes) { const l = b.getSize(new THREE.Vector3()).length(); if (l > size) { size = l; largest = g; } }
    const centreGroup: string = core ?? (boxes.has("bus") ? "bus" : largest);
    const coreBox = boxes.get(centreGroup) ?? new THREE.Box3().setFromObject(scene);
    const centre = coreBox.getCenter(new THREE.Vector3());
    const step = coreBox.getSize(new THREE.Vector3()).length() * 1.0;
    const reach = new THREE.Box3().setFromObject(scene).getBoundingSphere(new THREE.Sphere()).radius * 1.1;
    const offsets = new Map<string, THREE.Vector3>();
    for (const [g, box] of boxes) {
      const d = box.getCenter(new THREE.Vector3()).sub(centre);
      const len = d.length();
      if (g === centreGroup || len < 1e-6) { offsets.set(g, new THREE.Vector3()); continue; }
      // Keep exploded parts near the assembled model's bounds so they stay in view.
      const push = Math.min(step + Math.min(len, step * 2) * 0.8, Math.max(reach - len, step * 0.3));
      offsets.set(g, d.normalize().multiplyScalar(push));
    }
    // Units, and each unit's offset in its parent's frame, less what it inherits from an
    // ancestor unit that moves too.
    const units: Unit[] = [];
    const zero = new THREE.Vector3();
    const visit = (o: THREE.Object3D, inherited: THREE.Vector3) => {
      for (const c of o.children) {
        const g = c.userData.assembly as string | undefined;
        const outer = typeof g === "string" ? g !== (tagged(o)?.userData.assembly) : o === scene;
        if (!outer) { visit(c, inherited); continue; }
        const group = typeof g === "string" ? g : groupOf(c, scene);
        const want = offsets.get(group) ?? zero;
        const world = want.clone().sub(inherited);
        const inv = new THREE.Matrix3().setFromMatrix4(o.matrixWorld).invert();
        units.push({ node: c, rest: c.position.clone(), group, local: world.applyMatrix3(inv) });
        visit(c, want);
      }
    };
    visit(scene, zero);
    return { parts: [...parts.values()], units, offsets, boxes, centre };
  }, [scene]);
}

const HIGHLIGHT = new THREE.Color("#1d4f66");
const FADED = 0.12; // opacity of the other parts while one is focused
const HOVER_FADED = 0.35; // a faded part under the pointer
const smooth = (t: number) => t * t * (3 - 2 * t);

type Controls = { target: THREE.Vector3; update: () => void };

// Frames the model once it loads: camera on a fixed three-quarter line, as far as its
// bounding sphere needs, orbiting the core's centre (the body, not the middle of a long
// boom). Explodes on `exploded`.
// A clicked part (`focus`) gets the camera: it flies in keeping the current viewing
// direction, orbits that part, follows it through explode/assemble, and flies back home
// when the focus clears.
function Model({ url, exploded, focus, setFocus, onLabel, onReady, explore = true }: {
  url: string; exploded: boolean; focus: string | null; setFocus: (f: string | null) => void; explore?: boolean;
  onLabel: (label: { name: string; size: THREE.Vector3 } | null) => void; onReady?: () => void;
}) {
  const gltf = useGLTF(url, "/draco/"); // compressed models (the /circuit boards) decode with the copy in public/draco
  // A copy per mount (geometry is shared): explode, fades and Suspense hiding change the
  // objects, and useGLTF's cached scene is reused by the next mount and the /models grid.
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const { parts, units, offsets, boxes, centre } = useParts(scene);
  const readyRef = useRef(onReady);
  readyRef.current = onReady;
  useEffect(() => { readyRef.current?.(); }, [scene]);
  const [hover, setHover] = useState<string | null>(null);
  const hinges = useHinges(scene);
  const t = useRef(0);
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const controls = useThree((s) => s.controls) as unknown as Controls | null;
  const gl = useThree((s) => s.gl);
  // Sharpest texture filtering the GPU offers: the default blurs textures seen at an angle.
  useEffect(() => {
    const max = gl.capabilities.getMaxAnisotropy();
    gltf.scene.traverse((o) => {
      const mats = (o as THREE.Mesh).material;
      for (const m of (Array.isArray(mats) ? mats : mats ? [mats] : []) as THREE.MeshStandardMaterial[]) {
        for (const tex of [m.map, m.normalMap, m.roughnessMap, m.metalnessMap]) {
          if (tex && tex.anisotropy !== max) { tex.anisotropy = max; tex.needsUpdate = true; }
        }
      }
    });
  }, [gltf.scene, gl]);
  const home = useRef<{ pos: THREE.Vector3; target: THREE.Vector3; near: number } | null>(null);
  const flight = useRef({ flying: false, dir: new THREE.Vector3(), last: new THREE.Vector3() });

  useEffect(() => {
    const sphere = new THREE.Box3().setFromObject(scene).getBoundingSphere(new THREE.Sphere());
    const fov = THREE.MathUtils.degToRad(camera.fov) * Math.min(1, camera.aspect);
    const dist = (sphere.radius * 1.15) / Math.sin(fov / 2);
    camera.position.copy(centre).addScaledVector(new THREE.Vector3(0.6, 0.45, 0.66).normalize(), dist);
    camera.near = dist / 100;
    camera.far = dist * 10;
    camera.updateProjectionMatrix();
    home.current = { pos: camera.position.clone(), target: centre.clone(), near: camera.near };
    if (controls) { controls.target.copy(centre); controls.update(); }
    else camera.lookAt(centre);
  }, [scene, camera, controls, centre]);

  // A focused part that isn't in this build (renamed or removed) clears the focus.
  useEffect(() => { if (focus && !boxes.has(focus)) setFocus(null); }, [focus, boxes, setFocus]);

  useEffect(() => {
    const f = flight.current;
    f.flying = true;
    if (controls) f.dir.copy(camera.position).sub(controls.target).normalize();
    if (focus && boxes.has(focus)) {
      const box = boxes.get(focus)!;
      f.last.copy(box.getCenter(new THREE.Vector3())).addScaledVector(offsets.get(focus)!, smooth(t.current));
      const fov = THREE.MathUtils.degToRad(camera.fov) * Math.min(1, camera.aspect);
      const dist = Math.max(box.getSize(new THREE.Vector3()).length() * 0.65, 0.05) / Math.sin(fov / 2);
      camera.near = Math.min(home.current?.near ?? dist / 100, dist / 100);
    } else if (home.current) camera.near = home.current.near;
    camera.updateProjectionMatrix();
    // Fade every other part; restore when the focus clears.
    for (const p of parts) for (const m of p.meshes) {
      for (const mat of (Array.isArray(m.material) ? m.material : [m.material]) as THREE.MeshStandardMaterial[]) {
        if (mat.userData.restOpacity === undefined) {
          mat.userData.restOpacity = mat.opacity;
          mat.userData.restTransparent = mat.transparent;
        }
        const fade = !!focus && p.group !== focus;
        mat.transparent = fade || mat.userData.restTransparent;
        mat.opacity = fade ? FADED : mat.userData.restOpacity;
        mat.depthWrite = !fade;
        mat.needsUpdate = true;
      }
    }
  }, [focus, boxes, offsets, parts, camera, controls]);

  useFrame((_, dt) => {
    const goal = exploded ? 1 : 0;
    if (Math.abs(goal - t.current) < 1e-4) { t.current = goal; } else t.current += (goal - t.current) * Math.min(1, dt * 5);
    const k = smooth(t.current);
    for (const u of units) u.node.position.copy(u.rest).addScaledVector(u.local, k);
    if (!controls || !home.current) return;
    const f = flight.current;
    let goalTarget: THREE.Vector3, goalPos: THREE.Vector3;
    if (focus && boxes.has(focus)) {
      const box = boxes.get(focus)!;
      goalTarget = box.getCenter(new THREE.Vector3()).addScaledVector(offsets.get(focus)!, k);
      if (!f.flying) {
        // Settled: follow the part as it moves, keeping whatever view the user orbited to.
        const delta = goalTarget.clone().sub(f.last);
        camera.position.add(delta);
        controls.target.add(delta);
        f.last.copy(goalTarget);
        controls.update();
        return;
      }
      const fov = THREE.MathUtils.degToRad(camera.fov) * Math.min(1, camera.aspect);
      const dist = Math.max(box.getSize(new THREE.Vector3()).length() * 0.65, 0.05) / Math.sin(fov / 2);
      goalPos = goalTarget.clone().addScaledVector(f.dir, dist);
      f.last.copy(goalTarget);
    } else {
      if (!f.flying) return;
      goalTarget = home.current.target;
      goalPos = home.current.pos;
    }
    const a = 1 - Math.exp(-dt * 5);
    camera.position.lerp(goalPos, a);
    controls.target.lerp(goalTarget, a);
    controls.update();
    const scale = goalPos.distanceTo(goalTarget);
    if (camera.position.distanceTo(goalPos) < scale * 0.002 && controls.target.distanceTo(goalTarget) < scale * 0.002) {
      camera.position.copy(goalPos);
      controls.target.copy(goalTarget);
      f.flying = false;
    }
  });

  useEffect(() => {
    for (const p of parts) for (const m of p.meshes) {
      for (const mat of (Array.isArray(m.material) ? m.material : [m.material]) as THREE.MeshStandardMaterial[]) {
        // A hovered faded part shows a little more of itself, so it reads as clickable.
        if (focus && p.group !== focus && mat.userData.restOpacity !== undefined)
          mat.opacity = p.group === hover ? HOVER_FADED : FADED;
        if (!mat.emissive) continue;
        if (!mat.userData.rest) mat.userData.rest = mat.emissive.clone();
        mat.emissive.copy(explore && p.group === hover ? HIGHLIGHT : mat.userData.rest);
      }
    }
    // Without explore, `hover` is a hinge group: light up the parts that move.
    if (!explore) for (const m of hinges.meshes(hover)) {
      for (const mat of (Array.isArray(m.material) ? m.material : [m.material]) as THREE.MeshStandardMaterial[]) {
        if (mat.emissive && mat.userData.rest) mat.emissive.copy(HIGHLIGHT);
      }
    }
  }, [hover, focus, parts, explore, hinges]);
  // The part under the pointer. While one is focused, the others are see-through, so a ray
  // that reaches the focused part picks it even through faded parts in front of it.
  const pick = (e: ThreeEvent<PointerEvent | MouseEvent>) => {
    const groups = e.intersections.map((i) => groupOf(i.object, scene));
    return focus && groups.includes(focus) ? focus : groups[0] ?? groupOf(e.object, scene);
  };
  const onMove = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    const h = hingeGroup(e.intersections[0]?.object ?? e.object, scene);
    setHover(explore ? pick(e) : h);
    gl.domElement.style.cursor = h ? "pointer" : "";
  };
  const onClick = (e: ThreeEvent<MouseEvent>) => {
    if (e.delta > 4) return; // the end of an orbit drag, not a click
    e.stopPropagation();
    // A part on a hinge with somewhere to go (its joint's move_to) moves instead of focusing.
    const h = hingeGroup(e.intersections[0]?.object ?? e.object, scene);
    if (h) { hinges.toggle(h); return; }
    if (!explore) return; // a plain model: only the moving parts answer clicks
    const g = pick(e);
    setFocus(g === focus ? null : g); // another part moves the focus to it
  };
  // The label is drawn by the Viewer in a fixed panel, so it never covers the part.
  const label = explore ? hover ?? focus : null;
  useEffect(() => {
    const box = label ? boxes.get(label) : undefined;
    onLabel(label && box ? { name: label, size: box.getSize(new THREE.Vector3()) } : null);
  }, [label, boxes, onLabel]);
  return <primitive object={scene} onPointerMove={onMove} onClick={onClick}
    onPointerOut={() => { setHover(null); gl.domElement.style.cursor = ""; }} />;
}

// Hinged parts: joints the build exported with a "joint_move_to" (the spec's joints). A click
// on a part under one turns every joint in its group to that angle, or back to rest. The axis
// is stored in Blender's frame (z up); the glTF is y up, so (x, y, z) -> (x, z, -y).
type Hinge = { node: THREE.Object3D; axis: THREE.Vector3; rest: THREE.Quaternion; restDeg: number; to: number; group: string; now: number };

function hingeGroup(o: THREE.Object3D | null, scene: THREE.Object3D): string | null {
  for (let n = o; n && n !== scene; n = n.parent) {
    if (typeof n.userData.joint_move_to === "number") return (n.userData.joint_group as string | undefined) ?? n.name;
  }
  return null;
}

function useHinges(scene: THREE.Object3D) {
  const hinges = useMemo(() => {
    const hs: Hinge[] = [];
    scene.traverse((o) => {
      const u = o.userData;
      if (!Array.isArray(u.joint_axis) || typeof u.joint_move_to !== "number") return;
      const restDeg = typeof u.angle_deg === "number" ? u.angle_deg : 0;
      hs.push({ node: o, axis: new THREE.Vector3(u.joint_axis[0], u.joint_axis[2], -u.joint_axis[1]).normalize(),
        rest: o.quaternion.clone(), restDeg, to: u.joint_move_to, group: u.joint_group ?? o.name, now: restDeg });
    });
    return hs;
  }, [scene]);
  const moved = useRef(new Set<string>());
  useEffect(() => { moved.current = new Set(); }, [scene]);
  const q = useMemo(() => new THREE.Quaternion(), []);
  useFrame((_, dt) => {
    const a = Math.min(1, dt * 6);
    for (const h of hinges) {
      const goal = moved.current.has(h.group) ? h.to : h.restDeg;
      if (Math.abs(goal - h.now) < 1e-3) { if (h.now === goal) continue; h.now = goal; } else h.now += (goal - h.now) * a;
      // About the axis in the parent's frame, from the exported pose.
      h.node.quaternion.copy(q.setFromAxisAngle(h.axis, THREE.MathUtils.degToRad(h.now - h.restDeg)).multiply(h.rest));
    }
  });
  const byGroup = useMemo(() => {
    const m = new Map<string, THREE.Mesh[]>();
    for (const h of hinges) h.node.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) m.set(h.group, [...(m.get(h.group) ?? []), o as THREE.Mesh]);
    });
    return m;
  }, [hinges]);
  return useMemo(() => ({
    meshes: (group: string | null) => (group ? byGroup.get(group) ?? [] : []),
    toggle: (group: string) => {
      const s = moved.current;
      if (s.has(group)) s.delete(group); else s.add(group);
    },
  }), [byGroup]);
}

// Blender's axes from the glTF's (exported y-up): x, -z, y; sizes just swap y and z.
const blenderSize = (v: THREE.Vector3) => [v.x, v.z, v.y];
const m2 = (v: number) => (v >= 1 ? `${v.toFixed(2)} m` : v >= 0.01 ? `${Math.round(v * 100)} cm` : `${(v * 1000).toFixed(1)} mm`);

function PartLabel({ name, size, row, hasBreakdown, stale }: {
  name: string; size: THREE.Vector3; row?: Breakdown["families"][string]; hasBreakdown: boolean; stale: boolean;
}) {
  const off = row?.centre_offset ? Math.hypot(...row.centre_offset) : null;
  return (
    <div className={styles.partLabel}>
      <div>{name}</div>
      <div className={styles.dim}>{blenderSize(size).map(m2).join(" × ")}</div>
      {hasBreakdown && (
        row?.ref && off !== null
          ? <div className={off > 0.15 ? styles.bad : styles.ok}>NASA: {m2(off)} off · {row.ref.pieces} pieces</div>
          : <div className={styles.bad}>not matched in NASA&apos;s model</div>
      )}
      {hasBreakdown && stale && <div className={styles.dim}>breakdown is from an older build</div>}
    </div>
  );
}

class ViewerBoundary extends Component<{ children: ReactNode; resetKey: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidUpdate(prev: { resetKey: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false });
  }
  render() { return this.state.failed ? <div className={styles.empty}>Could not load the model.</div> : this.props.children; }
}

// `compact`: embedded in a scrolling page (the terminal): no wheel zoom, so the wheel scrolls the page.
// `focus`/`onFocus`: the focused part, when the page around the viewer also picks it (the /circuit block list).
export function Viewer({ probe, url, breakdown, stale, compact, onReady, focus: shown, onFocus, explore = true }: {
  probe: string; url: string; breakdown: Breakdown | null; stale: boolean; compact?: boolean; onReady?: () => void;
  focus?: string | null; onFocus?: (f: string | null) => void; explore?: boolean;
}) {
  const [exploded, setExploded] = useState(false);
  const [own, setOwn] = useState<string | null>(null);
  const focus = shown !== undefined ? shown : own;
  const setFocus = onFocus ?? setOwn;
  // Another model starts from its overview; a rebuild of the same one keeps the focus.
  useEffect(() => setFocus(null), [probe]); // eslint-disable-line react-hooks/exhaustive-deps
  const [label, setLabel] = useState<{ name: string; size: THREE.Vector3 } | null>(null);
  const down = useRef<{ x: number; y: number } | null>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setFocus(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <ViewerBoundary resetKey={url}>
      {explore && (
        <button className={`${styles.explode} ${exploded ? styles.active : ""}`} onClick={() => setExploded((x) => !x)}>
          {exploded ? "Assemble" : "Explode"}
        </button>
      )}
      {label && (
        <PartLabel name={label.name} size={label.size} row={breakdown?.families[label.name]}
          hasBreakdown={!!breakdown} stale={stale} />
      )}
      <Canvas camera={{ fov: 35, position: [6, 4, 8] }} dpr={[1, 2]}
        onPointerDown={(e) => { down.current = { x: e.clientX, y: e.clientY }; }}
        onPointerMissed={(e) => {
          // A click on empty space unfocuses; the end of an orbit drag doesn't.
          const d = down.current;
          if (d && Math.hypot(e.clientX - d.x, e.clientY - d.y) <= 4) setFocus(null);
        }}>
        <color attach="background" args={["#090909"]} />
        <StudioLights />
        <Suspense fallback={null}>
          <Model key={url} url={url} exploded={exploded} focus={focus} setFocus={setFocus} onLabel={setLabel} onReady={onReady} explore={explore} />
        </Suspense>
        <OrbitControls makeDefault enableZoom={!compact} />
      </Canvas>
    </ViewerBoundary>
  );
}

function fmt(v: number | null, unit: string) {
  if (v === null) return "—";
  if (unit === "bytes") return `${(v / 1e6).toFixed(2)} MB`;
  if (unit === "tris") return v.toLocaleString();
  return `${v} ${unit}`;
}

// The live site's copy of this probe: current, behind (its own files changed since approve), or
// possibly behind (shared harness code changed: a rebuild shows whether the model differs).
function Published({ p }: { p: Probe["published"] }) {
  if (!p) return <span className={styles.dim}>not published</span>;
  if (p.own.length) return <span className={styles.bad} title={p.own.join("\n")}>live version behind ({p.own.length} files)</span>;
  if (p.shared.length) return <span className={styles.stepNow} title={p.shared.join("\n")}>shared code changed since approve</span>;
  return <span className={styles.ok}>live version current</span>;
}

// A circuit board's blocks (out/<board>/<board>.json): click one to focus it on the board.
function BoardBlocks({ url, focus, setFocus }: { url: string; focus: string | null; setFocus: (f: string | null) => void }) {
  const [data, setData] = useState<{ blocks: { name: string; parts: { ref: string; value: string; package: string }[] }[] } | null>(null);
  useEffect(() => {
    let alive = true;
    fetch(url, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).then((d) => { if (alive) setData(d); }).catch(() => {});
    return () => { alive = false; };
  }, [url]);
  const block = data?.blocks.find((x) => x.name === focus);
  return (
    <div className={styles.boardBlocks}>
      {data?.blocks.map((x) => (
        <button key={x.name} onClick={() => setFocus(x.name === focus ? null : x.name)} className={x.name === focus ? styles.active : ""}>
          {x.name} <span className={styles.dim}>{x.parts.length}</span>
        </button>
      ))}
      {block && <div className={styles.dim}>{block.parts.map((p) => `${p.ref} ${p.value}`).join(" · ")}</div>}
    </div>
  );
}

export default function ModelsDashboard() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  // Which worktree's build to show, per probe, when the user picked one (else the newest).
  const [picked, setPicked] = useState<Record<string, string>>({});
  const [view, setView] = useState<"build" | "reference" | "close-ups">("build");
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("probe");
    if (fromUrl) setSelected(fromUrl);
    else try { setSelected(localStorage.getItem(SELECTED_KEY)); } catch { /* storage unavailable */ }
    let alive = true;
    const poll = async () => {
      try {
        const res = await fetch("/api/models/status", { cache: "no-store" });
        if (!res.ok) throw new Error();
        const next: Status = await res.json();
        if (alive) { setStatus(next); setError(false); }
      } catch { if (alive) setError(true); }
      if (alive) setNow(Date.now());
    };
    poll();
    const id = setInterval(poll, 1000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // Follow a probe when a build of it starts, so the page shows whatever is happening
  // now; the build that was already finished when the page loaded doesn't count.
  const currentProbe = status?.current?.probe;
  const currentTree = status?.current?.worktree;
  const currentAt = status?.current?.at;
  const seenAt = useRef<number | null | undefined>(undefined);
  useEffect(() => {
    if (currentAt === undefined) return;
    if (seenAt.current === undefined) { seenAt.current = currentAt; return; }
    if (currentAt !== seenAt.current && currentProbe) {
      setSelected(currentProbe);
      if (currentTree) setPicked((p) => ({ ...p, [currentProbe]: currentTree }));
    }
    seenAt.current = currentAt;
  }, [currentProbe, currentTree, currentAt]);

  const choose = (name: string) => {
    setSelected(name);
    setView("build");
    try { localStorage.setItem(SELECTED_KEY, name); } catch { /* storage unavailable */ }
  };

  const probe = status?.probes.find((p) => p.name === selected) ?? status?.probes[0];
  const src = probe?.worktrees.find((w) => w.worktree === picked[probe.name]) ?? probe?.worktrees[0];
  const wt = src?.worktree ?? "";
  const cur = status?.current?.probe === probe?.name && status?.current?.worktree === wt ? status?.current : null;
  const b = src?.build;
  const hasRef = !!src?.refs.includes("reference-sheet.png");
  // Until a probe has its own build, its reference sheet is all there is to show.
  const views = [b?.sheet && "build", hasRef && "reference", b?.closeups?.length && "close-ups"]
    .filter(Boolean) as ("build" | "reference" | "close-ups")[];
  const shown = views.includes(view) ? view : views[0];
  const sheetUrl = !probe ? null
    : shown === "reference" ? file(wt, `refs/${probe.name}/reference-sheet.png`)
    : shown === "close-ups" ? file(wt, `out/${probe.name}/closeups.png`, b?.started)
    : b?.sheet ? file(wt, `out/${probe.name}/sheet.png`, b.started) : null;
  const board = probe?.kind === "circuit";
  const glbUrl = probe && b?.glb ? file(wt, board ? `circuit/${probe.name}/${b.glb}` : `out/${probe.name}/${probe.name}.glb`, b.started) : null;
  const [focus, setFocus] = useState<string | null>(null); // a board's block, picked in its list or on the board
  useEffect(() => setFocus(null), [probe?.name]);

  // The reference breakdown, if `run.py explode` has been run for this probe; re-read every
  // few seconds since it is written outside the build. Needs a measured reference model.
  const [breakdown, setBreakdown] = useState<Breakdown | null>(null);
  const probeName = probe?.name;
  useEffect(() => {
    if (!probeName || !hasRef || !wt) return;
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch(file(wt, `out/${probeName}/ref/explode.json`), { cache: "no-store" });
        const next = res.ok ? await res.json() : null;
        if (alive) setBreakdown(next);
      } catch { if (alive) setBreakdown(null); }
    };
    load();
    const id = setInterval(load, 5000);
    return () => { alive = false; clearInterval(id); setBreakdown(null); };
  }, [probeName, hasRef, wt]);
  const stale = !!breakdown && !!b && breakdown.build_started !== b.started;
  const state = !status ? (error ? "offline" : "") : cur?.state === "running" ? "building"
    : b?.error ? "error" : b ? (b.ok ? "pass" : "fail") : "not built";
  const dot = cur?.state === "running" ? styles.running : b?.ok ? styles.ok : b ? styles.bad : "";

  const live = cur ?? null; // telemetry follows the tab and the worktree shown
  const running = live?.state === "running";
  const anyRunning = status?.current?.state === "running";
  const passed = b?.checks?.filter((c) => c.ok).length ?? 0;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <nav className={styles.tabs}>
          {status?.probes.map((p) => {
            const pb = p.worktrees[0]?.build;
            const busy = anyRunning && status.current?.probe === p.name;
            return (
              <button key={p.name} onClick={() => choose(p.name)} className={p.name === probe?.name ? styles.active : ""}>
                <span className={`${styles.dot} ${busy ? styles.running : !pb ? "" : pb.ok ? styles.ok : styles.bad}`} />
                {p.name}
              </button>
            );
          })}
        </nav>
        <div className={styles.telemetry}>
          {live && running ? (
            <span className={styles.stepNow}>building {Math.max(1, STEPS.indexOf(live.step) + 1)}/{STEPS.length}</span>
          ) : live?.step === "error" ? (
            <span className={styles.bad}>build error</span>
          ) : null}
          {b ? (
            <>
              {b.checks && <span className={passed === b.checks.length ? styles.ok : styles.bad}>{passed}/{b.checks.length} checks</span>}
              <span className={styles.dim}>
                {b.seconds !== undefined ? `${b.seconds}s build · ` : ""}{ago(b.started, now)}{live ? ` · ${live.session}` : ""}
              </span>
            </>
          ) : probe ? <span className={styles.dim}>not built yet{hasRef ? " · showing reference" : ""}</span> : null}
          {probe && src && (probe.worktrees.length > 1 ? (
            <span className={styles.trees} title="worktree this build is from">
              {probe.worktrees.map((w) => (
                <button key={w.worktree} onClick={() => setPicked((p) => ({ ...p, [probe.name]: w.worktree }))}
                  className={w.worktree === wt ? styles.active : ""} title={w.branch ? `branch ${w.branch}` : undefined}>
                  {w.label}{w.working ? " (changing)" : ""}{w.worktree === wt ? "" : w.build ? ` · ${ago(w.build.started, now)}` : " · not built"}
                </button>
              ))}
            </span>
          ) : <span className={styles.dim} title={src.branch ? `branch ${src.branch}` : undefined}>from {src.label}{src.working ? " (changing)" : ""}</span>)}
          {probe && !probe.fixture && !board && <Published p={probe.published} />}
          {anyRunning && !running && (
            <span className={styles.dim}>building {status?.current?.probe} in {status?.current?.label}</span>
          )}
          {error && <span className={styles.bad}>offline</span>}
        </div>
      </header>
      <div className={styles.grid}>
        <div className={styles.viewCell}>
          {glbUrl ? <Viewer probe={probe!.name} url={glbUrl} breakdown={breakdown} stale={stale}
            {...(board ? { focus, onFocus: setFocus } : {})} /> : <div className={styles.empty}>{probe ? "no export" : ""}</div>}
        </div>
        <div className={styles.side}>
          <div className={styles.sheetCell}>
            {board && b?.glb ? <BoardBlocks url={file(wt, `circuit/${probe!.name}/${probe!.name}.json`, b.started)} focus={focus} setFocus={setFocus} />
              : sheetUrl ? <img className={styles.sheet} src={sheetUrl} alt="" /> : <div className={styles.empty}>no sheet</div>}
            {views.length > 1 && (
              <div className={styles.toggle}>
                {views.map((v) => (
                  <button key={v} onClick={() => setView(v)} className={v === shown ? styles.active : ""}>{v}</button>
                ))}
              </div>
            )}
          </div>
          <div className={styles.statusCell}>
            <div className={styles.statusLine}>
              <span className={`${styles.dot} ${dot}`} />
              <span>{probe?.name ?? "—"}</span>
              <span className={styles.dim}>{state}{b && cur?.state !== "running" ? ` · ${ago(b.started, now)}` : ""}</span>
            </div>
            {b?.error && <pre className={styles.error}>{b.error.trim().split("\n").slice(-3).join("\n")}</pre>}
            {b?.checks && (
              <table className={styles.checks}>
                <tbody>
                  {b.checks.map((c) => (
                    <tr key={c.name} className={c.ok ? "" : styles.bad}>
                      <td>{c.ok ? "✓" : "✗"}</td><td>{c.name}</td><td>{fmt(c.measured, c.unit)}</td><td className={styles.dim}>{fmt(c.expected, c.unit)}</td>
                    </tr>
                  ))}
                  {b.baseline?.changed && <tr className={styles.bad}><td>✗</td><td>baseline</td><td colSpan={2}>changed</td></tr>}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
