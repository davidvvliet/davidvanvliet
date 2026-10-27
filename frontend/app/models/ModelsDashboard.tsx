"use client";

import { Component, ReactNode, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { Environment, Lightformer, OrbitControls, useGLTF } from "@react-three/drei";
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
  sources: { title?: string; url?: string }[]; referenceModel: { url?: string; note?: string } | null;
  refs: string[]; build: Build | null;
};
// out/<probe>/ref/explode.json, written by `run.py explode` (the reference split into our parts).
type Breakdown = {
  build_started: number | null;
  families: Record<string, { ref: { pieces: number; size: number[] } | null; centre_offset?: number[]; ours: { size: number[] } }>;
};
type Current = { probe: string; step: string; state: string; message: string | null; session: string; at: number };
type Status = { updated: number | null; current: Current | null; probes: Probe[] };

const STEPS = ["spec", "model", "checks", "render", "export", "done"];
const SELECTED_KEY = "models-dashboard-probe";
const file = (rel: string, v?: number) => `/api/models/file/${rel}${v ? `?v=${v}` : ""}`;

function ago(t: number, now: number) {
  const s = Math.max(0, Math.round(now / 1000 - t));
  return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)}m ago` : `${Math.round(s / 3600)}h ago`;
}

// Part family, as explode.py groups them: rtg_1 and rtg_1_fins -> rtg, feed_leg_3 -> feed_leg.
const family = (name: string) => name.replace(/_fins$/, "").replace(/_\d+$/, "");

type Part = { node: THREE.Object3D; rest: THREE.Vector3; family: string; meshes: THREE.Mesh[] };

// Every top-level node of the export is one part. Each family is pushed away from the bus
// centre: a fixed step plus a share of its distance, capped so the 13 m booms stay in view.
function useParts(scene: THREE.Object3D) {
  return useMemo(() => {
    const parts: Part[] = scene.children.map((node) => {
      const meshes: THREE.Mesh[] = [];
      node.traverse((o) => {
        const m = o as THREE.Mesh;
        if (!m.isMesh) return;
        // Parts share materials ("black" etc.): give each mesh its own so a highlight stays on one part.
        m.material = Array.isArray(m.material) ? m.material.map((x) => x.clone()) : m.material.clone();
        meshes.push(m);
      });
      return { node, rest: node.position.clone(), family: family(node.name), meshes };
    });
    const boxes = new Map<string, THREE.Box3>();
    for (const p of parts) {
      const box = boxes.get(p.family) ?? new THREE.Box3();
      boxes.set(p.family, box.union(new THREE.Box3().setFromObject(p.node)));
    }
    const busBox = boxes.get("bus") ?? new THREE.Box3().setFromObject(scene);
    const bus = busBox.getCenter(new THREE.Vector3());
    const step = busBox.getSize(new THREE.Vector3()).length() * 1.0;
    const offsets = new Map<string, THREE.Vector3>();
    for (const [fam, box] of boxes) {
      const d = box.getCenter(new THREE.Vector3()).sub(bus);
      const len = d.length();
      if (fam === "bus" || len < 1e-6) { offsets.set(fam, new THREE.Vector3()); continue; }
      offsets.set(fam, d.normalize().multiplyScalar(step + Math.min(len, step * 2) * 0.8));
    }
    return { parts, offsets, boxes };
  }, [scene]);
}

const HIGHLIGHT = new THREE.Color("#1d4f66");
const FADED = 0.12; // opacity of the other parts while one is focused
const smooth = (t: number) => t * t * (3 - 2 * t);

type Controls = { target: THREE.Vector3; update: () => void };

// Frames the model once it loads: camera on a fixed three-quarter line, far enough
// that its bounding sphere fits the view, orbiting its centre. Explodes on `exploded`.
// A clicked part (`focus`) gets the camera: it flies in keeping the current viewing
// direction, orbits that part, follows it through explode/assemble, and flies back home
// when the focus clears.
function Model({ url, exploded, focus, setFocus, onLabel }: {
  url: string; exploded: boolean; focus: string | null; setFocus: (f: string | null) => void;
  onLabel: (label: { name: string; size: THREE.Vector3 } | null) => void;
}) {
  const { scene } = useGLTF(url);
  const { parts, offsets, boxes } = useParts(scene);
  const [hover, setHover] = useState<string | null>(null);
  const t = useRef(0);
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const controls = useThree((s) => s.controls) as unknown as Controls | null;
  const home = useRef<{ pos: THREE.Vector3; target: THREE.Vector3; near: number } | null>(null);
  const flight = useRef({ flying: false, dir: new THREE.Vector3(), last: new THREE.Vector3() });

  useEffect(() => {
    const sphere = new THREE.Box3().setFromObject(scene).getBoundingSphere(new THREE.Sphere());
    const fov = THREE.MathUtils.degToRad(camera.fov) * Math.min(1, camera.aspect);
    const dist = (sphere.radius * 1.15) / Math.sin(fov / 2);
    camera.position.copy(sphere.center).addScaledVector(new THREE.Vector3(0.6, 0.45, 0.66).normalize(), dist);
    camera.near = dist / 100;
    camera.far = dist * 10;
    camera.updateProjectionMatrix();
    home.current = { pos: camera.position.clone(), target: sphere.center.clone(), near: camera.near };
    if (controls) { controls.target.copy(sphere.center); controls.update(); }
    else camera.lookAt(sphere.center);
  }, [scene, camera, controls]);

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
        const fade = !!focus && p.family !== focus;
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
    for (const p of parts) p.node.position.copy(p.rest).addScaledVector(offsets.get(p.family)!, k);
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
      const mat = m.material as THREE.MeshStandardMaterial;
      if (!mat.emissive) continue;
      if (!mat.userData.rest) mat.userData.rest = mat.emissive.clone();
      mat.emissive.copy(p.family === hover ? HIGHLIGHT : mat.userData.rest);
    }
  }, [hover, parts]);
  const top = (o: THREE.Object3D) => { while (o.parent && o.parent !== scene) o = o.parent; return o; };
  const onMove = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    const fam = family(top(e.object).name);
    setHover(focus && fam !== focus ? null : fam); // faded parts don't react
  };
  const onClick = (e: ThreeEvent<MouseEvent>) => {
    if (e.delta > 4) return; // the end of an orbit drag, not a click
    e.stopPropagation();
    const fam = family(top(e.object).name);
    if (focus && fam !== focus) return; // clicks through faded parts: ignore
    setFocus(fam === focus ? null : fam);
  };
  // The label is drawn by the Viewer in a fixed panel, so it never covers the part.
  const label = hover ?? focus;
  useEffect(() => {
    const box = label ? boxes.get(label) : undefined;
    onLabel(label && box ? { name: label, size: box.getSize(new THREE.Vector3()) } : null);
  }, [label, boxes, onLabel]);
  return <primitive object={scene} onPointerMove={onMove} onPointerOut={() => setHover(null)} onClick={onClick} />;
}

// Blender's axes from the glTF's (exported y-up): x, -z, y; sizes just swap y and z.
const blenderSize = (v: THREE.Vector3) => [v.x, v.z, v.y];
const m2 = (v: number) => (v >= 1 ? `${v.toFixed(2)} m` : `${Math.round(v * 100)} cm`);

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

function Viewer({ url, breakdown, stale }: { url: string; breakdown: Breakdown | null; stale: boolean }) {
  const [exploded, setExploded] = useState(false);
  const [focus, setFocus] = useState<string | null>(null);
  const [label, setLabel] = useState<{ name: string; size: THREE.Vector3 } | null>(null);
  const down = useRef<{ x: number; y: number } | null>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setFocus(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <ViewerBoundary resetKey={url}>
      <button className={`${styles.explode} ${exploded ? styles.active : ""}`} onClick={() => setExploded((x) => !x)}>
        {exploded ? "Assemble" : "Explode"}
      </button>
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
        <ambientLight intensity={0.25} />
        <directionalLight position={[5, 7, 6]} intensity={3} />
        <directionalLight position={[-6, -1, -3]} intensity={0.6} />
        {/* Local studio reflections so foil and metal read as metal (no HDR download). */}
        <Environment resolution={64}>
          <Lightformer form="rect" intensity={2} position={[0, 5, 0]} scale={[10, 10, 1]} rotation-x={Math.PI / 2} />
          <Lightformer form="rect" intensity={0.8} position={[-5, 1, 3]} scale={[6, 4, 1]} rotation-y={Math.PI / 3} />
          <Lightformer form="rect" intensity={0.4} position={[5, -1, -3]} scale={[6, 4, 1]} rotation-y={-Math.PI / 1.5} />
        </Environment>
        <Suspense fallback={null}>
          <Model key={url} url={url} exploded={exploded} focus={focus} setFocus={setFocus} onLabel={setLabel} />
        </Suspense>
        <OrbitControls makeDefault />
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

export default function ModelsDashboard() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
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
  const currentAt = status?.current?.at;
  const seenAt = useRef<number | null | undefined>(undefined);
  useEffect(() => {
    if (currentAt === undefined) return;
    if (seenAt.current === undefined) { seenAt.current = currentAt; return; }
    if (currentAt !== seenAt.current && currentProbe) setSelected(currentProbe);
    seenAt.current = currentAt;
  }, [currentProbe, currentAt]);

  const choose = (name: string) => {
    setSelected(name);
    setView("build");
    try { localStorage.setItem(SELECTED_KEY, name); } catch { /* storage unavailable */ }
  };

  const probe = status?.probes.find((p) => p.name === selected) ?? status?.probes[0];
  const cur = status?.current?.probe === probe?.name ? status?.current : null;
  const b = probe?.build;
  const hasRef = !!probe?.refs.includes("reference-sheet.png");
  // Until a probe has its own build, its reference sheet is all there is to show.
  const views = [b?.sheet && "build", hasRef && "reference", b?.closeups?.length && "close-ups"]
    .filter(Boolean) as ("build" | "reference" | "close-ups")[];
  const shown = views.includes(view) ? view : views[0];
  const sheetUrl = !probe ? null
    : shown === "reference" ? file(`refs/${probe.name}/reference-sheet.png`)
    : shown === "close-ups" ? file(`out/${probe.name}/closeups.png`, b?.started)
    : b?.sheet ? file(`out/${probe.name}/sheet.png`, b.started) : null;
  const glbUrl = probe && b?.glb ? file(`out/${probe.name}/${probe.name}.glb`, b.started) : null;

  // The reference breakdown, if `run.py explode` has been run for this probe; re-read every
  // few seconds since it is written outside the build.
  const [breakdown, setBreakdown] = useState<Breakdown | null>(null);
  const probeName = probe?.name;
  useEffect(() => {
    if (!probeName) return;
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch(file(`out/${probeName}/ref/explode.json`), { cache: "no-store" });
        const next = res.ok ? await res.json() : null;
        if (alive) setBreakdown(next);
      } catch { if (alive) setBreakdown(null); }
    };
    load();
    const id = setInterval(load, 5000);
    return () => { alive = false; clearInterval(id); setBreakdown(null); };
  }, [probeName]);
  const stale = !!breakdown && !!b && breakdown.build_started !== b.started;
  const state = !status ? (error ? "offline" : "") : cur?.state === "running" ? "building"
    : b?.error ? "error" : b ? (b.ok ? "pass" : "fail") : "not built";
  const dot = cur?.state === "running" ? styles.running : b?.ok ? styles.ok : b ? styles.bad : "";

  const live = status?.current?.probe === probe?.name ? status?.current ?? null : null; // telemetry follows the tab
  const running = live?.state === "running";
  const anyRunning = status?.current?.state === "running";
  const passed = b?.checks?.filter((c) => c.ok).length ?? 0;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <nav className={styles.tabs}>
          {status?.probes.map((p) => (
            <button key={p.name} onClick={() => choose(p.name)} className={p.name === probe?.name ? styles.active : ""}>
              <span className={`${styles.dot} ${live?.probe === p.name && running ? styles.running : !p.build ? "" : p.build.ok ? styles.ok : styles.bad}`} />
              {p.name}
            </button>
          ))}
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
          {anyRunning && status?.current?.probe !== probe?.name && (
            <span className={styles.dim}>building {status?.current?.probe}</span>
          )}
          {error && <span className={styles.bad}>offline</span>}
        </div>
      </header>
      <div className={styles.grid}>
        <div className={styles.viewCell}>
          {glbUrl ? <Viewer url={glbUrl} breakdown={breakdown} stale={stale} /> : <div className={styles.empty}>{probe ? "no export" : ""}</div>}
        </div>
        <div className={styles.side}>
          <div className={styles.sheetCell}>
            {sheetUrl ? <img className={styles.sheet} src={sheetUrl} alt="" /> : <div className={styles.empty}>no sheet</div>}
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
