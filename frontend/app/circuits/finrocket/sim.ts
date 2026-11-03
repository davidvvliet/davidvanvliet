// A model rocket with four servo fins and the flight computer's control law for them.
// Frame: z up, metres, seconds. The rocket's body axis is its attitude applied to +z;
// fin i sits at 90° × i about that axis, fin 0 on the body's +x. Every number comes from the
// rocket's spec (Rocket below), not from here.
import * as THREE from "three";

export type Rocket = {
  mass_dry: number;          // kg, without the motor
  motor: { mass: number; propellant: number; curve: [number, number][] }; // kg, kg, (s, N)
  diameter: number;          // body, m
  length: number;            // m
  cd: number;                // drag coefficient on the body's frontal area
  cg: number;                // m from the nose tip, loaded
  cp: number;                // m from the nose tip (Barrowman)
  cn_alpha: number;          // whole rocket's normal-force slope, per radian, on the frontal area
  fin: { x: number; r: number; area: number; cl_alpha: number }; // a fin's moving part: m from nose, m from axis to its centre, m², per radian
  servo: { max_deg: number; deg_per_s: number };
  rail: number;              // launch rail length, m
};

export type Gains = { kp: number; kd: number; kroll: number; q_min: number }; // N·m per rad, N·m per rad/s, N·m per rad/s, Pa

const v = () => new THREE.Vector3();
const axisOf = (q: THREE.Quaternion) => v().set(0, 0, 1).applyQuaternion(q);
const radialOf = (q: THREE.Quaternion, i: number) => v().set(Math.cos((i * Math.PI) / 2), Math.sin((i * Math.PI) / 2), 0).applyQuaternion(q);

// The flight computer: from what the IMU reads (attitude, rotation rate), the fin angles it asks for.
// The tilt to correct is the rotation that brings the body axis back to vertical; the torque it wants
// is shared out to the fins (fin i pushes the tail along its own radial line, and all four together
// turn the rocket about its axis), divided by the dynamic pressure so the angle suits the speed.
export function command(r: Rocket, g: Gains, att: THREE.Quaternion, omega: THREE.Vector3, speed: number, rho: number): number[] {
  const b = axisOf(att);
  const tilt = v().crossVectors(b, new THREE.Vector3(0, 0, 1)); // |tilt| = sin(angle off vertical)
  const off = Math.asin(Math.min(1, tilt.length()));
  if (tilt.lengthSq() > 1e-12) tilt.setLength(off);
  const roll = omega.dot(b);
  const side = omega.clone().addScaledVector(b, -roll);
  // The rocket's own stability turns it into the airflow, not upright: the controller adds that
  // stiffness (dynamic pressure × normal-force slope × static margin) to its gain, so it can hold
  // the nose up against the wind and the flight path bends back to vertical.
  const qTrue = 0.5 * rho * speed * speed;
  const stiff = qTrue * r.fin.area * r.cn_alpha * (r.cp - r.cg);
  const want = tilt.multiplyScalar(g.kp + stiff).addScaledVector(side, -g.kd); // N·m, across the axis
  const wantRoll = -g.kroll * roll;
  const q = Math.max(g.q_min, qTrue);
  const perF = q * r.fin.area * r.fin.cl_alpha; // N per radian of deflection
  const arm = Math.abs(r.cg - r.fin.x);
  return [0, 1, 2, 3].map((i) => {
    const f = want.dot(radialOf(att, i)) / (2 * arm) + wantRoll / (4 * r.fin.r);
    const deg = THREE.MathUtils.radToDeg(f / perF);
    return THREE.MathUtils.clamp(deg, -r.servo.max_deg, r.servo.max_deg);
  });
}
