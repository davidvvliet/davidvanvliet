"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Grid, Html, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import StudioLights from "../../models/StudioLights";
import styles from "../../models/models.module.css";
import { command, type Gains, type Rocket } from "./sim";

// A board that drives the fin rocket (its recipe's "drives": "finrocket"): the board is on the bench,
// wired to the rocket's four servos. The rocket stays on its stand; the board's IMU reads the board's
// own attitude and turn rate, and the fins turn as the flight computer would command them.

export type FinRocketData = { rocket: Rocket; gains: Gains; rho: number };

// The board's turn in the viewer (three.js frame, from where it lay when loaded), changed by dragging.
// `snap` counts the times it was set straight at once, which the gyro must not read as a turn.
export type Held = { q: THREE.Quaternion; snap: number };

// The board lies with its long side along x; in the rocket that side runs along the rocket's axis
// (y up in three.js). M turns y onto x, so the board as loaded counts as the rocket standing upright
// and a turn about the board's long side is a roll. The controller is z up: (x, y, z) -> (x, z, -y).
const M = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -Math.PI / 2);
const Mi = M.clone().invert();
const C = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);
const Ci = C.clone().invert();
const attitude = (h: Held) => Ci.clone().multiply(Mi).multiply(h.q).multiply(M).multiply(C);

type Bench = { prev: THREE.Quaternion; snap: number; omega: THREE.Vector3; fins: number[] };

export function FinRocketView({ data, held }: { data: FinRocketData; held: React.RefObject<Held> }) {
  return (
    <Canvas camera={{ fov: 35, near: 0.01, far: 50, position: [0.45, 0.4, 0.65] }} dpr={[1, 2]}>
      <color attach="background" args={["#090909"]} />
      <Suspense fallback={null}>
        <Stand data={data} held={held} />
        <StudioLights />
      </Suspense>
      <OrbitControls target={[0, 0.12, 0]} enablePan={false} minDistance={0.25} maxDistance={3} />
    </Canvas>
  );
}

// The readout beside the block list: the board's tilt and spin, and each fin's angle.
export function FinRocketReadout({ data, held }: { data: FinRocketData; held: React.RefObject<Held> }) {
  const [hud, setHud] = useState({ tilt: 0, spin: 0, fins: [0, 0, 0, 0] });
  useEffect(() => {
    const id = setInterval(() => {
      const b = benches.get(held.current);
      const att = attitude(held.current);
      const axis = new THREE.Vector3(0, 0, 1).applyQuaternion(att);
      setHud({
        tilt: THREE.MathUtils.radToDeg(Math.acos(Math.min(1, axis.z))),
        spin: b ? THREE.MathUtils.radToDeg(b.omega.dot(axis)) : 0,
        fins: b ? [...b.fins] : [0, 0, 0, 0],
      });
    }, 100);
    return () => clearInterval(id);
  }, [held]);
  const { rocket: r, gains: g } = data;
  const perTilt = g.kp / (2 * Math.abs(r.cg - r.fin.x)) / (g.q_min * r.fin.area * r.fin.cl_alpha);
  return (
    <>
      <div className={styles.dim}>
        Wired to a model rocket&apos;s four fin servos. Drag the board to tilt it, shift-drag left-right to spin it about
        its long side, double-click to set it straight: its IMU feels the turn and the fins answer as they would to bring
        the rocket back upright. The rocket stays on its stand.
      </div>
      <table className={styles.parts}>
        <tbody>
          <tr><td>tilt</td><td>{hud.tilt.toFixed(1)}°</td></tr>
          <tr><td>spin</td><td>{hud.spin.toFixed(0)}°/s</td></tr>
          {hud.fins.map((f, i) => <tr key={i}><td>fin {i + 1}</td><td>{f >= 0 ? "+" : ""}{f.toFixed(1)}°</td></tr>)}
        </tbody>
      </table>
      <div className={styles.dim}>
        On the bench there is no airflow, so the controller uses its gain for 15 m/s: about {perTilt.toFixed(1)}° of fin
        per degree of tilt, more while the board turns, to damp the turn. A spin needs little fin: the rocket turns
        easily about its axis. AGFRC C04CLS servos at their rated 0.09 s per 60°, fins limited to ±{r.servo.max_deg}°.
        The gains are chosen, not tuned on hardware.
      </div>
    </>
  );
}

// The servos' state, per board, shared by the rocket view (which updates it) and the readout.
const benches = new WeakMap<Held, Bench>();

function Stand({ data, held }: { data: FinRocketData; held: React.RefObject<Held> }) {
  const { rocket, gains, rho } = data;
  const gltf = useGLTF("/models/finrocket.glb");
  const scene = useMemo(() => { const s = gltf.scene.clone(true); s.updateMatrixWorld(true); return s; }, [gltf.scene]);
  const fins = useMemo(() => [0, 1, 2, 3].map((i) => {
    const node = scene.getObjectByName(`fin${i}_j`);
    const a = node?.userData.joint_axis as number[] | undefined;
    if (!node || !a) return null;
    // Each fin's number, just beyond its tip at its middle height.
    const box = new THREE.Box3().setFromObject(node);
    const c = box.getCenter(new THREE.Vector3());
    const out = new THREE.Vector3(c.x, 0, c.z).normalize();
    const label = c.clone().addScaledVector(out, Math.max(box.max.x - box.min.x, box.max.z - box.min.z) / 2 + 0.02);
    return { node, rest: node.quaternion.clone(), axis: new THREE.Vector3(a[0], a[2], -a[1]).normalize(), label };
  }), [scene]);
  const q = useMemo(() => new THREE.Quaternion(), []);
  useFrame((_, dt) => {
    const h = held.current;
    let b = benches.get(h);
    if (!b) { b = { prev: attitude(h), snap: h.snap, omega: new THREE.Vector3(), fins: [0, 0, 0, 0] }; benches.set(h, b); }
    const step = Math.min(dt, 0.1);
    const att = attitude(h);
    if (b.snap !== h.snap) { b.snap = h.snap; b.prev.copy(att); b.omega.set(0, 0, 0); }
    // The gyro: the board's turn rate since the last frame, smoothed over about 50 ms.
    const d = att.clone().multiply(b.prev.clone().invert());
    if (d.w < 0) d.set(-d.x, -d.y, -d.z, -d.w);
    const raw = new THREE.Vector3(d.x, d.y, d.z);
    if (raw.lengthSq() > 1e-12 && step > 0) raw.setLength((2 * Math.acos(Math.min(1, d.w))) / step); else raw.set(0, 0, 0);
    b.omega.lerp(raw, Math.min(1, step / 0.05));
    b.prev.copy(att);
    const cmd = command(rocket, gains, att, b.omega, 0, rho);
    const most = rocket.servo.deg_per_s * step;
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
