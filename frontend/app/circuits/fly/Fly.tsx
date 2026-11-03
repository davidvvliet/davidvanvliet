"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Grid, Line, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import StudioLights from "../../models/StudioLights";
import { Header } from "../../models/PublishedModels";
import styles from "../../models/models.module.css";
import { start, step, type Gains, type Rocket, type State } from "./sim";

// The sim is z up; three.js is y up. C turns the sim's frame into three's: (x, y, z) -> (x, z, -y),
// the same mapping as the glTF export of Blender's z-up models.
const C = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);
const Ci = C.clone().invert();
const toThree = (q: THREE.Quaternion) => C.clone().multiply(q).multiply(Ci);
const toSim = (q: THREE.Quaternion) => Ci.clone().multiply(q).multiply(C);
const v3 = (p: THREE.Vector3) => new THREE.Vector3(p.x, p.z, -p.y);

const DT = 1 / 240;
type Shared = { s: State; held: THREE.Quaternion | null; launched: boolean; trail: THREE.Vector3[] };

export default function Fly({ rocket, gains, rho, cp }: { rocket: Rocket; gains: Gains; rho: number; cp: number }) {
  const shared = useRef<Shared>({ s: start(), held: null, launched: false, trail: [] });
  const [hud, setHud] = useState<State>(shared.current.s);
  useEffect(() => {
    const id = setInterval(() => setHud(shared.current.s), 100);
    return () => clearInterval(id);
  }, []);
  const reset = () => { shared.current = { s: start(), held: null, launched: false, trail: [] }; };
  const tilt = THREE.MathUtils.radToDeg(Math.acos(Math.min(1, new THREE.Vector3(0, 0, 1).applyQuaternion(hud.att).z)));
  const margin = (cp - rocket.cg) / rocket.diameter;
  return (
    <div className={styles.page}>
      <Header>
        <Link href="/circuits?board=rocket-recorder" className={styles.dim}>← rocket-recorder</Link>
        <span>Fly the rocket</span>
      </Header>
      <div className={styles.detail}>
        <div className={styles.viewCell}>
          <Canvas camera={{ fov: 40, near: 0.05, far: 3000, position: [2.5, 1.2, 2.5] }} dpr={[1, 2]}>
            <Suspense fallback={null}>
              <Flight shared={shared} rocket={rocket} gains={gains} rho={rho} />
              <StudioLights />
            </Suspense>
          </Canvas>
          <Trajectory shared={shared} hud={hud} />
        </div>
        <aside className={styles.sources}>
          <div style={{ height: 260, border: "var(--line)", position: "relative", touchAction: "none" }}>
            <Canvas camera={{ fov: 30, position: [0, 0, 0.32] }} dpr={[1, 2]}>
              <Suspense fallback={null}>
                <Board shared={shared} />
                <StudioLights />
              </Suspense>
            </Canvas>
          </div>
          <div className={styles.dim}>
            Drag the board to tilt the rocket, as a gust would; its IMU feels the tilt and the four servos turn the fins against it.
            On the pad the fins swing fully over: there is no air to push yet.
          </div>
          <div style={{ display: "flex", gap: "1rem" }}>
            <button className={styles.flyButton} onClick={() => { if (shared.current.s.phase === "apogee") reset(); shared.current.launched = true; }}>launch</button>
            <button className={styles.flyButton} onClick={reset}>reset</button>
          </div>
          <table className={styles.parts}>
            <tbody>
              <tr><td>phase</td><td>{hud.phase}</td></tr>
              <tr><td>time</td><td>{hud.phase === "pad" ? "–" : `${hud.t.toFixed(1)} s`}</td></tr>
              <tr><td>altitude</td><td>{hud.pos.z.toFixed(1)} m</td></tr>
              <tr><td>speed</td><td>{hud.vel.length().toFixed(1)} m/s</td></tr>
              <tr><td>tilt</td><td>{tilt.toFixed(1)}°</td></tr>
              {hud.fins.map((f, i) => <tr key={i}><td>fin {i + 1}</td><td>{f >= 0 ? "+" : ""}{f.toFixed(1)}°</td></tr>)}
            </tbody>
          </table>
          <div className={styles.dim}>
            Estes F15 thrust curve (NAR data); BT-70 airframe; AGFRC C04CLS servos at their rated 0.09 s per 60°, fins
            limited to ±{rocket.servo.max_deg}°. Centre of pressure by Barrowman&apos;s method, {margin.toFixed(1)} calibres behind the
            centre of gravity. Masses and centre of gravity are estimates; the controller&apos;s gains are chosen, not tuned on hardware.
          </div>
        </aside>
      </div>
    </div>
  );
}

// The rocket in flight: steps the sim, turns the fins, follows it with the camera, draws its path.
function Flight({ shared, rocket, gains, rho }: { shared: React.RefObject<Shared>; rocket: Rocket; gains: Gains; rho: number }) {
  const gltf = useGLTF("/models/finrocket.glb");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const fins = useMemo(() => [0, 1, 2, 3].map((i) => {
    const node = scene.getObjectByName(`fin${i}_j`);
    const a = node?.userData.joint_axis as number[] | undefined;
    return node && a ? { node, rest: node.quaternion.clone(), axis: new THREE.Vector3(a[0], a[2], -a[1]).normalize() } : null;
  }), [scene]);
  const body = useRef<THREE.Group>(null);
  const camera = useThree((s) => s.camera);
  const [trail, setTrail] = useState<THREE.Vector3[]>([]);
  const acc = useRef(0);
  const q = useMemo(() => new THREE.Quaternion(), []);
  useFrame((_, dt) => {
    const sh = shared.current;
    acc.current = Math.min(acc.current + dt, 0.1);
    while (acc.current >= DT) {
      sh.s = step(sh.s, rocket, gains, DT, rho, sh.held, sh.launched);
      acc.current -= DT;
    }
    const s = sh.s;
    const p = v3(s.pos);
    if (s.phase !== "pad" && s.phase !== "apogee" && (!sh.trail.length || sh.trail[sh.trail.length - 1].distanceTo(p) > 0.5)) {
      sh.trail.push(p.clone());
      setTrail([...sh.trail]);
    } else if (!sh.trail.length && trail.length) setTrail([]);
    if (body.current) { body.current.position.copy(p); body.current.quaternion.copy(toThree(s.att)); }
    fins.forEach((f, i) => f && f.node.quaternion.copy(q.setFromAxisAngle(f.axis, THREE.MathUtils.degToRad(s.fins[i])).multiply(f.rest)));
    // Chase camera: keeps its bearing, stays a few metres off, looks at the rocket's middle.
    const mid = p.clone().add(new THREE.Vector3(0, rocket.length / 2, 0).applyQuaternion(toThree(s.att)));
    const off = camera.position.clone().sub(mid).setY(0).normalize().multiplyScalar(2.6);
    camera.position.lerp(mid.clone().add(off).add(new THREE.Vector3(0, 0.6, 0)), Math.min(1, dt * 4));
    camera.lookAt(mid);
  });
  return (
    <>
      <group ref={body}><primitive object={scene} /></group>
      <Grid args={[400, 400]} cellSize={1} sectionSize={10} cellColor="#222" sectionColor="#333" fadeDistance={120} infiniteGrid />
      {trail.length > 1 && <Line points={trail} color="#00ff00" lineWidth={1.5} />}
    </>
  );
}

// The flight computer: the board stands along the rocket's axis, so it turns as the rocket does.
// Dragging it holds the rocket at the board's attitude (left-right tilts sideways, up-down toward you).
function Board({ shared }: { shared: React.RefObject<Shared> }) {
  const gltf = useGLTF("/circuits/rocket-recorder.glb");
  const scene = useMemo(() => {
    const s = gltf.scene.clone(true);
    const box = new THREE.Box3().setFromObject(s);
    s.position.sub(box.getCenter(new THREE.Vector3()));
    // The board lies in the glTF's x-z plane, long side along x: stand it up along y, face to +z.
    const g = new THREE.Group();
    g.add(s);
    g.quaternion.setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI / 2)
      .multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI / 2));
    return g;
  }, [gltf.scene]);
  const turn = useRef<THREE.Group>(null);
  const gl = useThree((s) => s.gl);
  useEffect(() => {
    const el = gl.domElement;
    let last: { x: number; y: number } | null = null;
    const down = (e: PointerEvent) => {
      last = { x: e.clientX, y: e.clientY };
      el.setPointerCapture(e.pointerId);
      shared.current.held = shared.current.s.att.clone();
    };
    const move = (e: PointerEvent) => {
      if (!last || !shared.current.held) return;
      const dx = e.clientX - last.x, dy = e.clientY - last.y;
      last = { x: e.clientX, y: e.clientY };
      const k = 0.008; // radians per pixel
      const turnBy = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -dx * k)
        .multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), dy * k));
      shared.current.held = toSim(turnBy.multiply(toThree(shared.current.held)));
    };
    const up = () => { last = null; shared.current.held = null; };
    el.addEventListener("pointerdown", down);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerup", up);
    el.addEventListener("pointercancel", up);
    el.style.cursor = "grab";
    return () => {
      el.removeEventListener("pointerdown", down);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerup", up);
      el.removeEventListener("pointercancel", up);
    };
  }, [gl, shared]);
  useFrame(() => {
    // Only its attitude: the rocket's travel and its turn about the vertical stay out of this view.
    if (turn.current) turn.current.quaternion.copy(toThree(shared.current.held ?? shared.current.s.att));
  });
  return <group ref={turn}><primitive object={scene} /></group>;
}

// The path seen from the side: altitude against distance east (x) and north (y) from the pad.
function Trajectory({ shared, hud }: { shared: React.RefObject<Shared>; hud: State }) {
  const pts = shared.current.trail;
  const top = Math.max(50, ...pts.map((p) => p.y));
  const side = Math.max(top / 4, ...pts.map((p) => Math.max(Math.abs(p.x), Math.abs(p.z))));
  const W = 180, H = 200;
  const X = (h: number) => W / 2 + (h / side) * (W / 2 - 8), Y = (z: number) => H - 8 - (z / top) * (H - 16);
  const path = (f: (p: THREE.Vector3) => number) => pts.map((p, i) => `${i ? "L" : "M"}${X(f(p)).toFixed(1)},${Y(p.y).toFixed(1)}`).join("");
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 12, bottom: 12, pointerEvents: "none" }} aria-label="trajectory">
      <line x1={W / 2} y1={8} x2={W / 2} y2={H - 8} stroke="#333" />
      <line x1={8} y1={H - 8} x2={W - 8} y2={H - 8} stroke="#333" />
      <path d={path((p) => p.x)} fill="none" stroke="#00ff00" />
      <path d={path((p) => -p.z)} fill="none" stroke="#f5c451" />
      <text x={8} y={14} fill="#777" fontSize={10}>{Math.round(top)} m</text>
      <text x={W - 8} y={H - 12} fill="#777" fontSize={10} textAnchor="end">±{Math.round(side)} m</text>
      <text x={8} y={28} fill="#00ff00" fontSize={10}>east</text>
      <text x={8} y={40} fill="#f5c451" fontSize={10}>north</text>
      {hud.phase === "apogee" && <text x={W / 2} y={14} fill="#ededed" fontSize={10} textAnchor="middle">apogee {hud.pos.z.toFixed(0)} m</text>}
    </svg>
  );
}
