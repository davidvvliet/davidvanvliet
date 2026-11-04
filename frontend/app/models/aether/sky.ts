import * as THREE from "three";
import { moonPositionJ2000Km } from "../../components/lunar";
import { moonFixedFromIcrf } from "../../components/moonOrientation";

export { moonFixedFromIcrf };

// The real sky around the Moon on a date: the Moon's orientation (IAU model), and the Sun and the
// Earth as seen from it. Directions are in the Moon's body-fixed frame (x toward longitude 0,
// z toward the north pole), the frame the LOLA elevation maps use.

const J2000 = 2451545.0;
const d2r = Math.PI / 180;

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
