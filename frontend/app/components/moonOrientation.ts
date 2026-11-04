import * as THREE from "three";

// The Moon's orientation on a date (the IAU model), for the solar-system scene and the launch page.

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

/** Rotation from ICRF (J2000 equatorial) to the Moon's body-fixed frame (x lon 0, z north) at a Julian date. */
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

// Ecliptic J2000 -> ICRF: a rotation about x by the J2000 obliquity, 84381.448 arcsec.
const ICRF_FROM_ECLIPTIC = new THREE.Matrix4().makeRotationX((84381.448 / 3600) * d2r);
// Body-fixed or ecliptic axes -> the scene's (and a three.js sphere's own) axes: x stays, z (north) is +y,
// y (lon 90 E, or ecliptic longitude 90) is -z. A sphere's map centre (lon 0) is then at +x.
export const SCENE_FROM_FIXED = new THREE.Matrix4().set(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1);

/** The Moon mesh's orientation in the scene on a date: its map's lon 0 and north pole where they really point. */
export function moonSceneQuaternion(jd: number, out = new THREE.Quaternion()): THREE.Quaternion {
  // scene <- ecliptic <- ICRF <- body-fixed <- sphere
  const m = SCENE_FROM_FIXED.clone()
    .multiply(ICRF_FROM_ECLIPTIC.clone().transpose())
    .multiply(moonFixedFromIcrf(jd).transpose())
    .multiply(SCENE_FROM_FIXED.clone().transpose());
  return out.setFromRotationMatrix(m);
}
