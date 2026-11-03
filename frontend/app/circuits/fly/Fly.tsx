"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Grid, Html, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import StudioLights from "../../models/StudioLights";
import { Header } from "../../models/PublishedModels";
import styles from "../../models/models.module.css";
import { command, type Gains, type Rocket } from "./sim";

// The controller is z up; three.js is y up. C turns its frame into three's: (x, y, z) -> (x, z, -y),
// the same mapping as the glTF export of Blender's z-up models.
const C = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);
const Ci = C.clone().invert();
const toThree = (q: THREE.Quaternion) => C.clone().multiply(q).multiply(Ci);
const toSim = (q: THREE.Quaternion) => Ci.clone().multiply(q).multiply(C);

// The board on the bench, wired to the rocket's servos. The rocket stands still: the board's IMU
// reads the board's own attitude and turn rate, and the servos turn the fins as the flight
// computer would command them for a rocket in that attitude.
type Bench = { att: THREE.Quaternion; prev: THREE.Quaternion; omega: THREE.Vector3; fins: number[] };

export default function Fly({ rocket, gains, rho }: { rocket: Rocket; gains: Gains; rho: number }) {
  const bench = useRef<Bench>({ att: new THREE.Quaternion(), prev: new THREE.Quaternion(), omega: new THREE.Vector3(), fins: [0, 0, 0, 0] });
  const [hud, setHud] = useState({ tilt: 0, spin: 0, fins: [0, 0, 0, 0] });
  useEffect(() => {
    const id = setInterval(() => {
      const b = bench.current;
      const axis = new THREE.Vector3(0, 0, 1).applyQuaternion(b.att);
      setHud({
        tilt: THREE.MathUtils.radToDeg(Math.acos(Math.min(1, axis.z))),
        spin: THREE.MathUtils.radToDeg(b.omega.dot(axis)),
        fins: [...b.fins],
      });
    }, 100);
    return () => clearInterval(id);
  }, []);
  return (
    <div className={styles.page}>
      <Header>
        <Link href="/circuits?board=rocket-recorder" className={styles.dim}>← rocket-recorder</Link>
        <span>Fins on the bench</span>
      </Header>
      <div className={styles.detail}>
        <div className={styles.viewCell}>
          <Canvas camera={{ fov: 35, near: 0.01, far: 50, position: [0.45, 0.4, 0.65] }} dpr={[1, 2]}>
            <Suspense fallback={null}>
              <Stand bench={bench} rocket={rocket} gains={gains} rho={rho} />
              <StudioLights />
            </Suspense>
            <OrbitControls target={[0, 0.12, 0]} enablePan={false} minDistance={0.25} maxDistance={3} />
          </Canvas>
        </div>
        <aside className={styles.sources}>
          <div style={{ height: 260, border: "var(--line)", position: "relative", touchAction: "none" }}>
            <Canvas camera={{ fov: 30, position: [0, 0, 0.32] }} dpr={[1, 2]}>
              <Suspense fallback={null}>
                <Board bench={bench} />
                <StudioLights />
              </Suspense>
            </Canvas>
          </div>
          <div className={styles.dim}>
            Drag the board to tilt it, shift-drag left-right to spin it about its long side, double-click to stand it
            straight. It is wired to the rocket&apos;s four servos: its IMU feels the tilt and the fins turn as they would
            to bring the rocket back upright. The rocket itself stays on the stand.
          </div>
          <table className={styles.parts}>
            <tbody>
              <tr><td>tilt</td><td>{hud.tilt.toFixed(1)}°</td></tr>
              <tr><td>spin</td><td>{hud.spin.toFixed(0)}°/s</td></tr>
              {hud.fins.map((f, i) => <tr key={i}><td>fin {i + 1}</td><td>{f >= 0 ? "+" : ""}{f.toFixed(1)}°</td></tr>)}
            </tbody>
          </table>
          <div className={styles.dim}>
            On the bench there is no airflow, so the controller uses the gain it would at 15 m/s: about{" "}
            {finPerTilt(rocket, gains).toFixed(1)}° of fin per degree of tilt, and turning the board makes the fins
            kick further while it moves, to damp the turn. A spin needs little fin: the rocket turns easily about its
            axis. AGFRC C04CLS servos at their rated 0.09 s per 60°, fins limited to ±{rocket.servo.max_deg}°.
            The controller&apos;s gains are chosen, not tuned on hardware.
          </div>
        </aside>
      </div>
    </div>
  );
}

// Fin degrees per degree of steady tilt at the controller's floor dynamic pressure.
function finPerTilt(r: Rocket, g: Gains): number {
  return g.kp / (2 * Math.abs(r.cg - r.fin.x)) / (g.q_min * r.fin.area * r.fin.cl_alpha);
}

// The rocket on its stand: reads the board, runs the controller, turns the fins at servo speed.
function Stand({ bench, rocket, gains, rho }: { bench: React.RefObject<Bench>; rocket: Rocket; gains: Gains; rho: number }) {
  const gltf = useGLTF("/models/finrocket.glb");
  const scene = useMemo(() => { const s = gltf.scene.clone(true); s.updateMatrixWorld(true); return s; }, [gltf.scene]);
  const fins = useMemo(() => [0, 1, 2, 3].map((i) => {
    const node = scene.getObjectByName(`fin${i}_j`);
    const a = node?.userData.joint_axis as number[] | undefined;
    if (!node || !a) return null;
    // Label each fin just beyond its tip, at the fin's middle height.
    const box = new THREE.Box3().setFromObject(node);
    const c = box.getCenter(new THREE.Vector3());
    const out = new THREE.Vector3(c.x, 0, c.z).normalize();
    const label = new THREE.Vector3(c.x, c.y, c.z).addScaledVector(out, Math.max(box.max.x - box.min.x, box.max.z - box.min.z) / 2 + 0.02);
    return { node, rest: node.quaternion.clone(), axis: new THREE.Vector3(a[0], a[2], -a[1]).normalize(), label };
  }), [scene]);
  const q = useMemo(() => new THREE.Quaternion(), []);
  useFrame((_, dt) => {
    const b = bench.current;
    const h = Math.min(dt, 0.1);
    // The gyro: the board's turn rate since the last frame, smoothed over about 50 ms.
    const d = b.att.clone().multiply(b.prev.clone().invert());
    if (d.w < 0) d.set(-d.x, -d.y, -d.z, -d.w);
    const ang = 2 * Math.acos(Math.min(1, d.w));
    const raw = new THREE.Vector3(d.x, d.y, d.z);
    if (raw.lengthSq() > 1e-12 && h > 0) raw.setLength(ang / h); else raw.set(0, 0, 0);
    b.omega.lerp(raw, Math.min(1, h / 0.05));
    b.prev.copy(b.att);
    const cmd = command(rocket, gains, b.att, b.omega, 0, rho);
    const most = rocket.servo.deg_per_s * h;
    b.fins = b.fins.map((x, i) => x + THREE.MathUtils.clamp(cmd[i] - x, -most, most));
    fins.forEach((f, i) => f && f.node.quaternion.copy(q.setFromAxisAngle(f.axis, THREE.MathUtils.degToRad(b.fins[i])).multiply(f.rest)));
  });
  return (
    <>
      <primitive object={scene} />
      {fins.map((f, i) => f && (
        <Html key={i} position={f.label} center style={{ color: "#ededed", font: "11px var(--font-mono, monospace)", pointerEvents: "none" }}>
          {i + 1}
        </Html>
      ))}
      <Grid args={[4, 4]} cellSize={0.05} sectionSize={0.25} cellColor="#222" sectionColor="#333" fadeDistance={3} infiniteGrid />
    </>
  );
}

// The flight computer, held in the hand: it stands along the rocket's axis direction, so its
// attitude is the one the controller reads. Left-right tilts it sideways, up-down toward you,
// shift left-right spins it about its long side; double-click stands it straight.
function Board({ bench }: { bench: React.RefObject<Bench> }) {
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
    };
    const move = (e: PointerEvent) => {
      if (!last) return;
      const dx = e.clientX - last.x, dy = e.clientY - last.y;
      last = { x: e.clientX, y: e.clientY };
      const k = 0.008; // radians per pixel
      const att = toThree(bench.current.att);
      let next: THREE.Quaternion;
      if (e.shiftKey) {
        // About the board's own long side (its y in three's frame).
        next = att.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), dx * k));
      } else {
        next = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -dx * k)
          .multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), dy * k))
          .multiply(att);
      }
      bench.current.att.copy(toSim(next.normalize()));
    };
    const up = () => { last = null; };
    // Stood straight at once, not turned: the gyro reads no turn.
    const straight = () => { bench.current.att.identity(); bench.current.prev.identity(); bench.current.omega.set(0, 0, 0); };
    el.addEventListener("pointerdown", down);
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerup", up);
    el.addEventListener("pointercancel", up);
    el.addEventListener("dblclick", straight);
    el.style.cursor = "grab";
    return () => {
      el.removeEventListener("pointerdown", down);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerup", up);
      el.removeEventListener("pointercancel", up);
      el.removeEventListener("dblclick", straight);
    };
  }, [gl, bench]);
  useFrame(() => {
    if (turn.current) turn.current.quaternion.copy(toThree(bench.current.att));
  });
  return <group ref={turn}><primitive object={scene} /></group>;
}
