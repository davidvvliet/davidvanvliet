// The flight sim's rocket, from specs/finrocket.json: sizes, masses, motor curve, and the
// centre of pressure and normal-force slopes by Barrowman's method as the OpenRocket technical
// documentation gives it (or_techdoc: eqs 3.19, 3.28, 3.29, 3.40, 3.53, 3.55; fin CP at 25% MAC).
import type { Gains, Rocket } from "./sim";

type Value = { value: number };
export type Spec = {
  dimensions: Record<string, Value>;
  facts: Record<string, Value>;
  flight: Record<string, Value>;
};

export function rocketFrom(spec: Spec, eng: string): { rocket: Rocket; gains: Gains; rho: number; cp: number } {
  const d = (k: string) => (spec.dimensions[k] ?? spec.facts[k]).value;
  const f = (k: string) => spec.flight[k].value;
  const ro = d("body_od") / 2, ln = d("nose_length"), lb = d("body_length");
  const length = ln + lb;
  const aref = Math.PI * ro * ro;

  // Nose (tangent ogive): CNα = 2 (3.19, from zero to the full area); CP = l − V / A(l) (3.28).
  const rho = (ro * ro + ln * ln) / (2 * ro);
  let vol = 0;
  const n = 400;
  for (let k = 0; k < n; k++) {
    const x = ((k + 0.5) / n) * ln; // from the base toward the tip
    const r = Math.sqrt(rho * rho - x * x) + ro - rho;
    vol += Math.PI * r * r * (ln / n);
  }
  const noseCn = 2, noseX = ln - vol / aref;

  // Fins: one fin's slope (3.40) at low Mach (β = 1), four fins N/2 = 2 times it (3.53), body
  // interference KT(B) (3.55); CP at a quarter of the mean aerodynamic chord.
  const cr = d("fin_root_chord"), ct = d("fin_tip_chord"), s = d("fin_span"), sw = d("fin_sweep");
  const afin = ((cr + ct) / 2) * s;
  const midSweep = Math.atan((sw + ct / 2 - cr / 2) / s);
  const one = (2 * Math.PI * (s * s) / aref) / (1 + Math.sqrt(1 + ((s * s) / (afin * Math.cos(midSweep))) ** 2));
  const kt = 1 + ro / (s + ro);
  let mac = 0, xle = 0, ymac = 0;
  for (let k = 0; k < n; k++) {
    const y = ((k + 0.5) / n) * s, c = cr + ((ct - cr) * y) / s;
    mac += c * c; xle += ((sw * y) / s) * c; ymac += y * c;
  }
  const w = s / n / afin;
  mac *= w; xle *= w; ymac *= w;
  const finLeFromNose = length - (d("fin_root_te_height") + cr);
  const finX = finLeFromNose + xle + 0.25 * mac;
  const finsCn = kt * 2 * one;

  const cnAlpha = noseCn + finsCn;
  const cp = (noseX * noseCn + finX * finsCn) / cnAlpha; // moment sum (3.29)

  const curve = eng.split("\n").map((l) => l.trim()).filter((l) => /^[\d.]+\s+[\d.]+$/.test(l))
    .map((l) => l.split(/\s+/).map(Number) as [number, number]);
  curve.unshift([0, 0]);

  const rocket: Rocket = {
    mass_dry: f("dry_mass"),
    motor: { mass: f("motor_mass"), propellant: f("propellant_mass"), curve },
    diameter: 2 * ro, length, cd: f("cd"), cg: f("cg_from_nose"), cp, cn_alpha: cnAlpha,
    fin: { x: finX, r: ro + 0.001 + ymac, area: aref, cl_alpha: kt * one },
    servo: { max_deg: f("fin_max_deg"), deg_per_s: f("servo_deg_per_s") },
    rail: f("rail_length"),
  };
  // Control gains (design): a critically damped turn back to vertical in about a third of a
  // second, for the rocket's inertia across (a rod: m L² / 12) and about its axis (a tube: m D² / 8).
  const m = rocket.mass_dry + rocket.motor.mass;
  const iAcross = (m * length * length) / 12, iAxis = (m * rocket.diameter ** 2) / 8, wn = 8, zeta = 0.8;
  const gains: Gains = { kp: iAcross * wn * wn, kd: 2 * zeta * wn * iAcross, kroll: 2 * zeta * wn * iAxis, q_min: 0.5 * f("rho") * 15 * 15 };
  return { rocket, gains, rho: f("rho"), cp };
}
