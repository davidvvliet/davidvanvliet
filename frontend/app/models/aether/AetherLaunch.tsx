"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, useTexture } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import styles from "./aether.module.css";

// The numbers are the spec's (scripts/blender/specs/aether.json): a flat shot off a 17.2 km track at
// 14 g reaches 2.176 km/s; half an orbit later, 7331 km over the north pole, the 20 N engine burns
// 59.5 m/s to lift the low point from the surface to 673 km; then the wings unfold.
const G0 = 9.80665;
const GM = 4.9e12;                       // m^3/s^2 (NSSDCA)
const R = 1737.4e3;                      // m
const R_A = R + 7331e3;                  // aposelene radius
const R_P = R + 673e3;                   // target periselene radius
const ACC = 14 * G0;
const V = Math.sqrt((2 * GM * R_A) / (R * (R + R_A)));  // the flat shot's speed
const TRACK = (V * V) / (2 * ACC);
const T_SHOT = V / ACC;                  // 15.8 s, shown in real time
const SEP = 4;                           // after the track's end
const COAST = 12;                        // 4.9 h, shown in 12 s
const BURN = 8;                          // 893 s, shown in 8 s
const REVEAL = 4;
const ACT = 13;
const DV = 59.5;
const BURN_S = 893;
const COAST_H = 4.9;

const P_SHOT = 0, P_COAST = T_SHOT + SEP, P_BURN = P_COAST + COAST, P_REVEAL = P_BURN + BURN;
const P_ACT = P_REVEAL + REVEAL, TOTAL = P_ACT + ACT;

// Sled parts leave the craft at the track's end; the model's own short rails are replaced by the long track.
const SLED = ["sep_ring_lower", "pusher", "sled_base", "shoe0", "shoe1", "shoe2", "shoe3", "armature"];
const MODEL_TRACK = ["rail0", "rail1", "stator"];

type Hinge = { node: THREE.Object3D; axis: THREE.Vector3; rest: THREE.Quaternion; restDeg: number };
type Ui = { phase: string; caption: string; readout: string };

const ease = (u: number) => { const c = Math.min(1, Math.max(0, u)); return c * c * (3 - 2 * c); };
const shot = { a: (R + R_A) / 2, e: (R_A - R) / (R_A + R) };
const target = { a: (R_P + R_A) / 2, e: (R_A - R_P) / (R_A + R_P) };
// Periselene over the south pole (-y), moving +x there, so the high point is over the north pole.
const orbitPoint = (o: { a: number; e: number }, nu: number) => {
  const r = (o.a * (1 - o.e * o.e)) / (1 + o.e * Math.cos(nu));
  return new THREE.Vector3(r * Math.sin(nu), -r * Math.cos(nu), 0);
};
const trueAnomaly = (M: number, e: number) => {
  let E = M + e * Math.sin(M);
  for (let i = 0; i < 12; i++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
  return 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2));
};
const km = (m: number) => Math.round(m / 1000).toLocaleString("en-US");

function orbitLine(o: { a: number; e: number }, from: number, to: number, color: string, opacity: number) {
  const pts = Array.from({ length: 241 }, (_, i) => orbitPoint(o, from + ((to - from) * i) / 240));
  const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
  line.frustumCulled = false;
  return line;
}

function Scene({ start, onDone, ui }: { start: number | null; onDone: () => void; ui: (u: Ui) => void }) {
  const gltf = useGLTF("/models/aether.glb");
  const moonMap = useTexture("/moon.jpg");
  const { camera } = useThree();
  const controls = useRef<OrbitControlsImpl>(null);

  // The craft, with the sled split off into its own group and the joints found.
  const { craft, sled, hinges } = useMemo(() => {
    const craft = gltf.scene.clone(true);
    craft.updateMatrixWorld(true);
    const sled = new THREE.Group();
    for (const n of SLED) { const o = craft.getObjectByName(n); if (o) sled.attach(o); }
    for (const n of MODEL_TRACK) { const o = craft.getObjectByName(n); if (o) o.visible = false; }
    const byName = new Map<string, Hinge>();
    craft.traverse((o) => {
      const u = o.userData;
      if (!Array.isArray(u.joint_axis)) return;
      byName.set(o.name, { node: o, axis: new THREE.Vector3(u.joint_axis[0], u.joint_axis[2], -u.joint_axis[1]).normalize(),
        rest: o.quaternion.clone(), restDeg: typeof u.angle_deg === "number" ? u.angle_deg : 0 });
    });
    // Unfolding order: the yoke, the first panel, then the others outward.
    const order = (s: string) => [`yoke_${s}_j`, ...[0, 1, 2, 3, 4].map((n) => `panel_${s}${n}_j`)];
    const left = order("l"), right = order("r");
    const hinges = left.map((n, i) => [byName.get(n), byName.get(right[i])].filter((h): h is Hinge => !!h));
    return { craft, sled, hinges };
  }, [gltf]);

  const ground = useMemo(() => {
    const map = moonMap.clone();
    map.wrapS = map.wrapT = THREE.RepeatWrapping;
    map.repeat.set(160, 40);
    map.colorSpace = THREE.SRGBColorSpace;
    map.needsUpdate = true;
    return map;
  }, [moonMap]);
  useEffect(() => { moonMap.colorSpace = THREE.SRGBColorSpace; moonMap.needsUpdate = true; }, [moonMap]);

  const lines = useMemo(() => ({
    shotPath: orbitLine(shot, 0, Math.PI, "#ffffff", 0.5),
    target: orbitLine(target, 0, 2 * Math.PI, "#ffb347", 0.9),
  }), []);
  const stars = useMemo(() => {
    const n = 4000, p = new Float32Array(n * 3), v = new THREE.Vector3();
    let s = 7;
    const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    for (let i = 0; i < n; i++) { v.set(rnd() * 2 - 1, rnd() * 2 - 1, rnd() * 2 - 1).normalize().multiplyScalar(2e8); p.set([v.x, v.y, v.z], i * 3); }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(p, 3));
    const pts = new THREE.Points(g, new THREE.PointsMaterial({ color: "#ffffff", size: 1.2, sizeAttenuation: false }));
    pts.frustumCulled = false;
    return pts;
  }, []);
  const posts = useMemo(() => {
    const n = Math.ceil(TRACK / 500) + 1;
    const mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(0.3, 2, 0.3), new THREE.MeshStandardMaterial({ color: "#bbbbbb" }), n * 2);
    const m = new THREE.Matrix4();
    for (let i = 0; i < n; i++) for (const z of [-3, 3]) { m.makeTranslation(i * 500, 0.35, z); mesh.setMatrixAt(i * 2 + (z > 0 ? 1 : 0), m); }
    mesh.frustumCulled = false;
    return mesh;
  }, []);

  const launchSet = useRef<THREE.Group>(null);
  const moon = useRef<THREE.Mesh>(null);
  const orbit = useRef<THREE.Group>(null);
  const marker = useRef<THREE.Mesh>(null);
  const plume = useRef<THREE.Mesh>(null);
  const craftRef = useRef<THREE.Group>(null);
  const sledRef = useRef<THREE.Group>(null);
  const last = useRef("");
  const done = useRef(false);
  const q = useMemo(() => new THREE.Quaternion(), []);
  const tmp = useMemo(() => new THREE.Vector3(), []);
  const shift = useMemo(() => new THREE.Vector3(), []);
  const shotKey = useRef("");     // the planned shot now showing
  const touched = useRef(false);  // the viewer has turned or zoomed since that shot began
  const sun = useRef<THREE.DirectionalLight>(null);

  useEffect(() => {
    const ctl = controls.current;
    camera.position.set(6, 2.5, 7);
    if (!ctl) return;
    ctl.minDistance = 2; ctl.maxDistance = 60;
    ctl.target.set(0.6, 0, 0); ctl.update();
    const grab = () => { touched.current = true; };
    ctl.addEventListener("start", grab);
    return () => ctl.removeEventListener("start", grab);
  }, [camera]);
  useEffect(() => { done.current = false; shotKey.current = ""; }, [start]);

  useFrame(() => {
    const running = start !== null;
    const t = running ? Math.min(TOTAL, performance.now() / 1000 - start) : 0;
    const c = craftRef.current, sl = sledRef.current;
    if (!c || !sl || !launchSet.current || !moon.current || !orbit.current || !marker.current || !plume.current) return;
    const local = t < P_COAST, orbitView = (t >= P_COAST && t < P_BURN) || (t >= P_REVEAL && t < P_ACT);
    launchSet.current.visible = local;
    sl.visible = local;
    moon.current.visible = !local;
    orbit.current.visible = orbitView;
    c.visible = !orbitView;
    plume.current.visible = t >= P_BURN && t < P_REVEAL;
    sun.current?.position.set(5e7, local || orbitView ? 1.5e7 : -2.5e7, 3e7);

    // Wings: folded until activation, then unfolded hinge by hinge.
    const a = t - P_ACT;
    const spans = [[1.5, 3.5], [3.5, 5.5], [5.5, 6.7], [6.7, 7.9], [7.9, 9.1], [9.1, 10.3]];
    hinges.forEach((pair, i) => {
      const u = ease((a - spans[i][0]) / (spans[i][1] - spans[i][0]));
      for (const h of pair) h.node.quaternion.copy(q.setFromAxisAngle(h.axis, THREE.MathUtils.degToRad(-h.restDeg * u)).multiply(h.rest));
    });

    let u: Ui;
    // Each shot opens on its planned view. Once the viewer turns or zooms, only the point the
    // camera circles follows the craft (the camera moves with it), so their angle and zoom stay.
    const ctl = controls.current;
    const cam = (key: string, pos: THREE.Vector3, look: THREE.Vector3, min: number, max: number) => {
      if (!running || t >= TOTAL || !ctl) return;
      if (key !== shotKey.current) {
        shotKey.current = key; touched.current = false;
        ctl.minDistance = min; ctl.maxDistance = max;
      }
      if (touched.current) camera.position.add(shift.copy(look).sub(ctl.target));
      else camera.position.copy(pos);
      ctl.target.copy(look); ctl.update();
    };
    if (local) {
      c.rotation.set(0, 0, 0);
      let x: number, y = 0, xs: number;
      if (t < T_SHOT) {
        x = 0.5 * ACC * t * t; xs = x;
        u = { phase: "Launch", caption: "On the mass driver at the south pole: 14 g along a 17.2 km track.",
          readout: `speed  ${((ACC * t) / 1000).toFixed(3)} km/s\naccel  14 g\ntrack  ${(x / 1000).toFixed(1)} / ${(TRACK / 1000).toFixed(1)} km` };
      } else {
        const tau = t - T_SHOT, dx = V * tau;
        x = TRACK + dx; y = (dx * dx) / (2 * R);           // the ground curves away below it
        const tb = Math.min(tau, V / (30 * G0));
        xs = TRACK + V * tb - 0.5 * 30 * G0 * tb * tb;
        u = { phase: "Separation", caption: "Off the end of the track at 2.18 km/s. The sled brakes; the craft flies on, and the ground curves away beneath it.",
          readout: `speed  ${(V / 1000).toFixed(3)} km/s\nheight ${y.toFixed(0)} m` };
      }
      c.position.set(x, y, 0); sl.position.set(xs, 0, 0);
      const back = t < T_SHOT ? 1 : 1 + (t - T_SHOT) * 1.5;
      cam("track", tmp.set(x - 9 * back, 2.2 * back, 6.5 * back), new THREE.Vector3(x + 2, y, 0), 2, 500);
    } else if (orbitView) {
      const coast = t < P_BURN;
      const f = coast ? (t - P_COAST) / COAST : 1;
      const nu = trueAnomaly(Math.PI * f, shot.e);
      const p = f >= 1 ? new THREE.Vector3(0, R_A, 0) : orbitPoint(shot, nu);
      marker.current.position.copy(p);
      (lines.target.material as THREE.LineBasicMaterial).opacity = coast ? 0.25 : 0.95;
      (lines.shotPath.material as THREE.LineBasicMaterial).opacity = coast ? 0.6 : 0.2;
      const r = p.length(), v = Math.sqrt(GM * (2 / r - 1 / shot.a));
      u = coast
        ? { phase: "Coast", caption: "Coasting half an orbit, 4.9 hours, up to 7,331 km over the north pole.",
            readout: `T+     ${(COAST_H * f).toFixed(1)} h\nheight ${km(r - R)} km\nspeed  ${(v / 1000).toFixed(2)} km/s` }
        : { phase: "In orbit", caption: "The low point is lifted from the surface to 673 km: the relay's orbit.",
            readout: "orbit  673 × 7,331 km\nperiod 10.8 h" };
      cam(coast ? "coast" : "in orbit", tmp.set(0, 3.0e6, 2.8e7), new THREE.Vector3(0, 3.0e6, 0), 2.5e6, 1e8);
    } else {
      // At the high point: dish (+y) toward the Moon below, engine firing along the motion (-x).
      c.position.set(0, R_A, 0); c.rotation.set(0, 0, Math.PI);
      const burn = t < P_REVEAL;
      if (burn) {
        const f = (t - P_BURN) / BURN;
        const m = plume.current.material as THREE.MeshBasicMaterial;
        m.opacity = 0.25 + 0.1 * Math.sin(t * 40);
        u = { phase: "Orbit insertion", caption: "At the high point the 20 N engine burns 59.5 m/s, lifting the orbit's low point from the surface to 673 km.",
          readout: `Δv     ${(DV * f).toFixed(1)} / ${DV} m/s\nburn   ${Math.round(BURN_S * f)} / ${BURN_S} s` };
        // From above, looking down past the craft at the Moon 7,331 km below.
        const ang = 0.5 + 0.1 * (t - P_BURN);
        cam("burn", tmp.set(4 * Math.cos(ang), R_A + 10, 4 * Math.sin(ang)), new THREE.Vector3(0, R_A - 2, 0), 2, 2e7);
      } else {
        const step = a < 1.5 ? "The hold-downs release." : a < 10.3 ? "The wings unfold: the yoke, then the panels, one by one."
          : "Wings out, 663 W. The S-band dish looks down at the Moon; the X-band panel turns to the Earth.";
        u = { phase: "Activation", caption: step, readout: "orbit  673 × 7,331 km\nwings  2 × 5 panels" };
        // From below, toward the cells and the dish.
        cam("activation", tmp.set(7, R_A - 6, 9), new THREE.Vector3(0, R_A, 0), 2, 2e7);
      }
    }
    const key = u.phase + u.caption + u.readout;
    if (key !== last.current) { last.current = key; ui(running ? u : { phase: "", caption: "", readout: "" }); }

    if (ctl && running && t >= TOTAL && !done.current) {
      done.current = true;
      c.getWorldPosition(tmp); camera.position.add(shift.copy(tmp).sub(ctl.target)); ctl.target.copy(tmp);
      onDone();
    }
  });

  return (
    <>
      <ambientLight intensity={0.15} />
      <directionalLight ref={sun} position={[5e7, 1.5e7, 3e7]} intensity={2.6} />
      <primitive object={stars} />
      <group ref={launchSet}>
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[12000, -0.66, 0]}>
          <planeGeometry args={[40000, 10000]} />
          <meshStandardMaterial map={ground} roughness={1} />
        </mesh>
        {[-0.45, 0.45].map((z) => (
          <mesh key={z} position={[TRACK / 2 - 50, -0.593, z]}>
            <boxGeometry args={[TRACK + 100, 0.12, 0.08]} />
            <meshStandardMaterial color="#3a3a3a" metalness={0.6} roughness={0.4} />
          </mesh>
        ))}
        <mesh position={[TRACK / 2 - 50, -0.533, 0]}>
          <boxGeometry args={[TRACK + 100, 0.04, 0.3]} />
          <meshStandardMaterial color="#2a2a2a" metalness={0.5} roughness={0.5} />
        </mesh>
        <primitive object={posts} />
      </group>
      <mesh ref={moon}>
        <sphereGeometry args={[R, 128, 64]} />
        <meshStandardMaterial map={moonMap} roughness={1} />
      </mesh>
      <group ref={orbit}>
        <primitive object={lines.shotPath} />
        <primitive object={lines.target} />
        <mesh ref={marker}>
          <sphereGeometry args={[90e3, 16, 8]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
      </group>
      <group ref={craftRef}>
        <primitive object={craft} />
        <mesh ref={plume} position={[0.055 - 0.45, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <coneGeometry args={[0.14, 0.9, 24, 1, true]} />
          <meshBasicMaterial color="#cfe3ff" transparent opacity={0.3} depthWrite={false} blending={THREE.AdditiveBlending} side={THREE.DoubleSide} />
        </mesh>
      </group>
      <group ref={sledRef}><primitive object={sled} /></group>
      <OrbitControls ref={controls} makeDefault enablePan={false} />
    </>
  );
}

export default function AetherLaunch() {
  const [start, setStart] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [ui, setUi] = useState<Ui>({ phase: "", caption: "", readout: "" });
  return (
    <div className={styles.page}>
      <Canvas className={styles.canvas} gl={{ logarithmicDepthBuffer: true, antialias: true }}
        camera={{ fov: 40, near: 0.05, far: 5e8, position: [6, 2.5, 7] }}>
        <Suspense fallback={null}>
          <Scene start={start} ui={setUi} onDone={() => setRunning(false)} />
        </Suspense>
      </Canvas>
      <div className={styles.title}>Altair Aether</div>
      {ui.phase && (
        <div className={styles.phase}>
          <div className={styles.phaseName}>{ui.phase}</div>
          <div className={styles.caption}>{ui.caption}</div>
          <div className={styles.readout}>{ui.readout}</div>
        </div>
      )}
      <button className={styles.launch} disabled={running}
        onClick={() => { setStart(performance.now() / 1000); setRunning(true); }}>
        Launch
      </button>
    </div>
  );
}
