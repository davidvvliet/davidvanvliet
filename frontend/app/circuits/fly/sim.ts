// A model rocket with four servo fins, flown by the flight computer's control loop.
// Physics frame: z up, metres, seconds. The rocket's body axis is its attitude applied to +z;
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

export type State = {
  t: number;
  pos: THREE.Vector3; vel: THREE.Vector3;
  att: THREE.Quaternion; omega: THREE.Vector3; // world frame
  fins: number[];            // deflection, degrees, as the servos have reached
  phase: "pad" | "boost" | "coast" | "apogee"; // the flight ends at apogee, where the parachute would come out
};

const G = 9.80665;

export function start(): State {
  return { t: 0, pos: new THREE.Vector3(), vel: new THREE.Vector3(), att: new THREE.Quaternion(), omega: new THREE.Vector3(), fins: [0, 0, 0, 0], phase: "pad" };
}

export function thrust(r: Rocket, t: number): number {
  const c = r.motor.curve;
  if (t <= 0 || t >= c[c.length - 1][0]) return 0;
  let i = 0;
  while (c[i + 1][0] < t) i++;
  const [t0, f0] = c[i], [t1, f1] = c[i + 1];
  return f0 + ((f1 - f0) * (t - t0)) / (t1 - t0);
}

// Propellant burnt by t, as a share of the total impulse delivered so far.
function burnt(r: Rocket, t: number): number {
  const c = r.motor.curve;
  let total = 0, done = 0;
  for (let i = 0; i + 1 < c.length; i++) {
    const [t0, f0] = c[i], [t1, f1] = c[i + 1];
    const imp = ((f0 + f1) / 2) * (t1 - t0);
    total += imp;
    if (t >= t1) done += imp;
    else if (t > t0) { const f = f0 + ((f1 - f0) * (t - t0)) / (t1 - t0); done += ((f0 + f) / 2) * (t - t0); }
  }
  return total ? done / total : 0;
}

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

// One step. `held`: the attitude the user's hand holds the rocket at (dragging the board), or null.
export function step(s: State, r: Rocket, g: Gains, dt: number, rho: number, held: THREE.Quaternion | null, launched: boolean): State {
  const n = { ...s, pos: s.pos.clone(), vel: s.vel.clone(), att: s.att.clone(), omega: s.omega.clone(), fins: [...s.fins] };
  // Servos move toward the command at their rated speed.
  const cmd = command(r, g, n.att, n.omega, n.vel.length(), rho);
  n.fins = n.fins.map((d, i) => d + THREE.MathUtils.clamp(cmd[i] - d, -r.servo.deg_per_s * dt, r.servo.deg_per_s * dt));
  if (n.phase === "apogee") return n;
  if (n.phase === "pad") {
    if (held) { n.omega.set(0, 0, 0); n.att.copy(held); }
    if (!launched) return n;
    n.phase = "boost";
    n.t = 0;
  }
  n.t += dt;
  const T = thrust(r, n.t);
  if (n.phase === "boost" && n.t > r.motor.curve[r.motor.curve.length - 1][0]) n.phase = "coast";
  const mass = r.mass_dry + r.motor.mass - r.motor.propellant * burnt(r, n.t);
  const b = axisOf(n.att);
  const area = (Math.PI * r.diameter * r.diameter) / 4;
  const speed = n.vel.length();
  const q = 0.5 * rho * speed * speed;

  const force = v().set(0, 0, -G * mass).addScaledVector(b, T);
  const torque = v();
  if (speed > 1e-3) {
    const vhat = n.vel.clone().divideScalar(speed);
    force.addScaledVector(vhat, -q * r.cd * area);
    // Normal force from the angle of attack, at the centre of pressure: turns the nose into the wind.
    const across = vhat.clone().addScaledVector(b, -vhat.dot(b)); // the airflow's sideways part, sin(alpha)
    const nf = across.multiplyScalar(-q * r.cn_alpha * area);
    force.add(nf);
    torque.add(b.clone().multiplyScalar(r.cg - r.cp).cross(nf));
    // Each fin's moving part: lift across the fin, at the fin.
    n.fins.forEach((deg, i) => {
      const rad = radialOf(n.att, i);
      const t = v().crossVectors(b, rad);
      const f = t.multiplyScalar(q * r.fin.area * r.fin.cl_alpha * THREE.MathUtils.degToRad(deg));
      force.add(f);
      torque.add(b.clone().multiplyScalar(r.cg - r.fin.x).addScaledVector(rad, r.fin.r).cross(f));
    });
  }
  // On the rail the rocket only slides along it.
  const onRail = n.pos.length() < r.rail && !held;
  const acc = force.divideScalar(mass);
  if (onRail) { const along = Math.max(0, acc.dot(b)); acc.copy(b).multiplyScalar(along); }
  n.vel.addScaledVector(acc, dt);
  n.pos.addScaledVector(n.vel, dt);

  if (held) {
    // The hand turns it: the rotation rate follows the hand, so it carries on spinning when let go.
    const d = held.clone().multiply(n.att.clone().invert());
    const ang = 2 * Math.acos(Math.min(1, Math.abs(d.w)));
    const ax = v().set(d.x, d.y, d.z);
    if (ax.lengthSq() > 1e-12) n.omega.copy(ax.normalize().multiplyScalar((Math.sign(d.w || 1) * ang) / dt)); else n.omega.set(0, 0, 0);
    n.att.copy(held);
  } else if (!onRail) {
    // Rigid body: inertia of a thin rod across, of a tube about the axis (from mass, length, radius).
    const iAcross = (mass * r.length * r.length) / 12;
    const iAxis = (mass * r.diameter * r.diameter) / 8;
    const roll = b.clone().multiplyScalar(torque.dot(b));
    const alpha = roll.divideScalar(iAxis).add(torque.clone().addScaledVector(b, -torque.dot(b)).divideScalar(iAcross));
    n.omega.addScaledVector(alpha, dt);
    const w = n.omega.length();
    if (w > 1e-9) n.att.premultiply(new THREE.Quaternion().setFromAxisAngle(n.omega.clone().divideScalar(w), w * dt)).normalize();
  } else n.omega.set(0, 0, 0);

  if (n.phase === "coast" && n.vel.z <= 0) n.phase = "apogee";
  return n;
}
