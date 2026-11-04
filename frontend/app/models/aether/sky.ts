import * as THREE from "three";
import { moonPositionJ2000Km } from "../../components/lunar";

// The real sky around the Moon on a date: the Moon's orientation (IAU model), and the Sun and the
// Earth as seen from it. Directions are in the Moon's body-fixed frame (x toward longitude 0,
// z toward the north pole), the frame the LOLA elevation maps use.

const J2000 = 2451545.0;
const d2r = Math.PI / 180;

// IAU 2009 Moon orientation, as kept in NAIF pck00011.tpc (BODY301_* and BODY3_NUT_PREC_ANGLES).
// Angles E1..E13: degrees and degrees per Julian century.
const E_ANGLES: [number, number][] = [
  [125.045, -1935.5364525], [250.089, -3871.072905], [260.008, 475263.3328725], [176.625, 487269.629985],
  [357.529, 35999.0509575], [311.589, 964468.49931], [134.963, 477198.869325], [276.617, 12006.300765],
  [34.226, 63863.5132425], [15.134, -5806.6093575], [119.743, 131.84064], [239.961, 6003.1503825],
  [25.053, 473327.79642],
];
const RA_T = [-3.8787, -0.1204, 0.07, -0.0172, 0, 0.0072, 0, 0, 0, -0.0052, 0, 0, 0.0043];
const DEC_T = [1.5419, 0.0239, -0.0278, 0.0068, 0, -0.0029, 0.0009, 0, 0, 0.0008, 0, 0, -0.0009];
const PM_T = [3.561, 0.1208, -0.0642, 0.0158, 0.0252, -0.0066, -0.0047, -0.0046, 0.0028, 0.0052, 0.004, 0.0019, -0.0044];

/** Rotation from ICRF (J2000 equatorial) to the Moon's body-fixed frame at a Julian date. */
export function moonFixedFromIcrf(jd: number): THREE.Matrix4 {
  const d = jd - J2000, T = d / 36525;
  let ra = 269.9949 + 0.0031 * T, dec = 66.5392 + 0.013 * T, w = 38.3213 + 13.17635815 * d - 1.4e-12 * d * d;
  E_ANGLES.forEach(([a, b], i) => {
    const E = (a + b * T) * d2r;
    ra += RA_T[i] * Math.sin(E); dec += DEC_T[i] * Math.cos(E); w += PM_T[i] * Math.sin(E);
  });
  // R = Rz(W) Rx(90 - dec) Rz(90 + ra)
  const m = new THREE.Matrix4().makeRotationZ(-(90 + ra) * d2r);   // three.js rotations are active: rotating the frame is the inverse
  m.premultiply(new THREE.Matrix4().makeRotationX(-(90 - dec) * d2r));
  m.premultiply(new THREE.Matrix4().makeRotationZ(-w * d2r));
  return m;
}

// Ecliptic J2000 -> ICRF: a rotation about x by the J2000 obliquity, 84381.448 arcsec (as in SolarSystem.tsx).
const EPS = (84381.448 / 3600) * d2r;
const eclToIcrf = (v: THREE.Vector3) => v.set(v.x, Math.cos(EPS) * v.y - Math.sin(EPS) * v.z, Math.sin(EPS) * v.y + Math.cos(EPS) * v.z);

// The Earth's orbit from the mean elements the solar-system page uses (SolarSystem.tsx: mean longitude
// 100.464 deg at J2000, longitude of perihelion 102.9 deg, e 0.0167, 365.25 days, 1 AU).
const AU_KM = 149597870;
function sunGeocentricKm(jd: number, out: THREE.Vector3) {
  const e = 0.0167, peri = 102.9 * d2r;
  const M = (100.464 + (360 / 365.25) * (jd - J2000)) * d2r - peri;
  let E = M;
  for (let i = 0; i < 8; i++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
  const nu = 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2));
  const r = AU_KM * (1 - e * Math.cos(E)), lon = nu + peri;
  return out.set(-r * Math.cos(lon), -r * Math.sin(lon), 0);   // the Sun is opposite the Earth's heliocentric position
}

export type Sky = { sun: THREE.Vector3; earth: THREE.Vector3 };

/** The Sun and the Earth from the Moon's centre, in km, in the Moon's body-fixed frame of date `frameJd`. */
export function skyAt(jd: number, frameJd = jd): Sky {
  const m = moonPositionJ2000Km(jd);
  const moon = new THREE.Vector3(m.x, m.y, m.z);
  const sun = sunGeocentricKm(jd, new THREE.Vector3()).sub(moon);
  const earth = moon.clone().negate();
  const R = moonFixedFromIcrf(frameJd);
  return { sun: eclToIcrf(sun).applyMatrix4(R), earth: eclToIcrf(earth).applyMatrix4(R) };
}

/** A J2000 RA/Dec direction in the Moon's body-fixed frame of a date. */
export function raDecToFixed(raDeg: number, decDeg: number, R: THREE.Matrix4): THREE.Vector3 {
  const ra = raDeg * d2r, dec = decDeg * d2r;
  return new THREE.Vector3(Math.cos(dec) * Math.cos(ra), Math.cos(dec) * Math.sin(ra), Math.sin(dec)).applyMatrix4(R);
}
