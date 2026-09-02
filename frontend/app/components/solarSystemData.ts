// Solar system body tables. Plain data (no three.js) so the terminal can
// import body names without pulling the renderer into its bundle.

export type PlanetSpec = {
  name: string;
  au: number;              // semi-major axis
  radiusEarths: number;    // radius relative to Earth
  periodDays: number;      // orbital period
  rotationDays: number;    // sidereal rotation period
  inclinationDeg: number;  // orbit inclination to the ecliptic
  color: number;
  phaseDeg: number;        // starting position on the orbit
  solid?: boolean;         // solid sphere instead of wireframe (e.g. cloud-covered)
  texture?: string;        // equirectangular map under /public; implies solid
  focusRadii?: number;     // click fly-in distance in body radii (default: MIN_DISTANCE_RADII * 1.5)
  axialTiltDeg?: number;   // tilt of the spin axis (rings, if any, lie in the equatorial plane)
  spinPhaseDeg?: number;   // initial rotation about the spin axis (map centre, lon 180, starts on +x at 0)
  rings?: { innerRadii: number; outerRadii: number; color: number; opacity: number; texture?: string }; // in planet radii; texture = radial strip (inner edge at left) with alpha
};

export type MoonSpec = {
  name: string;
  planet: string;          // name of the planet it orbits (from PLANETS)
  orbitPlanetRadii: number;// orbit radius in radii of its planet (true ratio)
  radiusEarths: number;    // radius relative to Earth (true ratio; tiny ones render as dots)
  periodDays: number;
  inclinationDeg: number;
  color: number;
  phaseDeg: number;
  texture?: string;        // equirectangular map under /public; implies solid
  solid?: boolean;         // solid sphere instead of wireframe (e.g. haze-covered)
};

// Moons of the table planets (Earth's Moon is built separately). One row each.
export const MOONS: MoonSpec[] = [
  { name: 'Phobos', planet: 'Mars', orbitPlanetRadii: 2.77, radiusEarths: 0.00174, periodDays: 0.3189, inclinationDeg: 1.08, color: 0x7a746c, phaseDeg: 0 },
  { name: 'Deimos', planet: 'Mars', orbitPlanetRadii: 6.92, radiusEarths: 0.00097, periodDays: 1.263, inclinationDeg: 1.79, color: 0x7a746c, phaseDeg: 200 },
  // Galilean moons. Inclinations are to Jupiter's equator (its axis is tilted only 3 degrees).
  { name: 'Io', planet: 'Jupiter', orbitPlanetRadii: 5.90, radiusEarths: 0.286, periodDays: 1.769, inclinationDeg: 0.05, color: 0xd9c46a, phaseDeg: 0, texture: '/io.jpg' },
  { name: 'Europa', planet: 'Jupiter', orbitPlanetRadii: 9.39, radiusEarths: 0.245, periodDays: 3.551, inclinationDeg: 0.47, color: 0xc8bfae, phaseDeg: 90, texture: '/europa.jpg' },
  { name: 'Ganymede', planet: 'Jupiter', orbitPlanetRadii: 14.97, radiusEarths: 0.413, periodDays: 7.155, inclinationDeg: 0.20, color: 0x9a9184, phaseDeg: 180, texture: '/ganymede.jpg' },
  { name: 'Callisto', planet: 'Jupiter', orbitPlanetRadii: 26.33, radiusEarths: 0.378, periodDays: 16.69, inclinationDeg: 0.19, color: 0x6e665c, phaseDeg: 270, texture: '/callisto.jpg' },
  // Titan: solid, its orange haze hides the surface.
  { name: 'Titan', planet: 'Saturn', orbitPlanetRadii: 20.98, radiusEarths: 0.404, periodDays: 15.945, inclinationDeg: 0.35, color: 0xd9a15c, phaseDeg: 60, texture: '/titan.jpg' },
  // Enceladus: tiny, and the most reflective body in the solar system.
  { name: 'Enceladus', planet: 'Saturn', orbitPlanetRadii: 4.09, radiusEarths: 0.0396, periodDays: 1.370, inclinationDeg: 0.01, color: 0xf2f2f2, phaseDeg: 200, texture: '/enceladus.jpg' },
  { name: 'Mimas', planet: 'Saturn', orbitPlanetRadii: 3.19, radiusEarths: 0.0311, periodDays: 0.942, inclinationDeg: 1.57, color: 0xd0cdc8, phaseDeg: 300 },
  { name: 'Tethys', planet: 'Saturn', orbitPlanetRadii: 5.06, radiusEarths: 0.0834, periodDays: 1.888, inclinationDeg: 1.12, color: 0xd6d3ce, phaseDeg: 250 },
  { name: 'Dione', planet: 'Saturn', orbitPlanetRadii: 6.48, radiusEarths: 0.0881, periodDays: 2.737, inclinationDeg: 0.02, color: 0xc4c0ba, phaseDeg: 80 },
  { name: 'Rhea', planet: 'Saturn', orbitPlanetRadii: 9.05, radiusEarths: 0.120, periodDays: 4.518, inclinationDeg: 0.35, color: 0xc9c5bf, phaseDeg: 130 },
  // Iapetus: far out and inclined ~8 degrees to Saturn's equator, the only large moon off the ring plane.
  { name: 'Iapetus', planet: 'Saturn', orbitPlanetRadii: 61.15, radiusEarths: 0.115, periodDays: 79.32, inclinationDeg: 8.13, color: 0xa89f92, phaseDeg: 20 },
  // Uranus: the five round moons. They orbit its equator, so nearly perpendicular to its orbit.
  { name: 'Miranda', planet: 'Uranus', orbitPlanetRadii: 5.10, radiusEarths: 0.0370, periodDays: 1.413, inclinationDeg: 4.23, color: 0xb8b5b0, phaseDeg: 0 },
  { name: 'Ariel', planet: 'Uranus', orbitPlanetRadii: 7.53, radiusEarths: 0.0909, periodDays: 2.520, inclinationDeg: 0.26, color: 0xc9c6c1, phaseDeg: 70 },
  { name: 'Umbriel', planet: 'Uranus', orbitPlanetRadii: 10.50, radiusEarths: 0.0918, periodDays: 4.144, inclinationDeg: 0.13, color: 0x6f6d6a, phaseDeg: 140 },
  { name: 'Titania', planet: 'Uranus', orbitPlanetRadii: 17.19, radiusEarths: 0.1237, periodDays: 8.706, inclinationDeg: 0.34, color: 0xa8a29a, phaseDeg: 210 },
  { name: 'Oberon', planet: 'Uranus', orbitPlanetRadii: 23.01, radiusEarths: 0.1195, periodDays: 13.46, inclinationDeg: 0.06, color: 0x9d9791, phaseDeg: 280 },
  // Triton: retrograde (negative period), the only large moon that orbits backwards. Its real
  // inclination is 157 degrees; retrograde direction plus a 23 degree tilt is the same orbit.
  { name: 'Triton', planet: 'Neptune', orbitPlanetRadii: 14.41, radiusEarths: 0.2124, periodDays: -5.877, inclinationDeg: 23.1, color: 0xc7b8b0, phaseDeg: 45 },
  // Charon: half Pluto's size and mutually locked with it (its orbit equals Pluto's day).
  { name: 'Charon', planet: 'Pluto', orbitPlanetRadii: 16.5, radiusEarths: 0.0951, periodDays: 6.387, inclinationDeg: 0.0, color: 0x9a8f88, phaseDeg: 0, texture: '/charon.jpg' },
];

// Planets other than Earth (Earth is built separately: it has the continents,
// the location dots and the Moon). Adding a planet = one row.
export const PLANETS: PlanetSpec[] = [
  { name: 'Mercury', au: 0.387, radiusEarths: 0.383, periodDays: 87.97, rotationDays: 58.65, inclinationDeg: 7.0, color: 0x8a847c, phaseDeg: 120, texture: '/mercury.jpg' },
  // Venus rotates retrograde (negative period). Solid: it's a featureless cloud deck.
  { name: 'Venus', au: 0.723, radiusEarths: 0.949, periodDays: 224.7, rotationDays: -243.0, inclinationDeg: 3.39, color: 0xe8dcc0, phaseDeg: 230, texture: '/venus.jpg' },
  { name: 'Mars', au: 1.524, radiusEarths: 0.532, periodDays: 686.98, rotationDays: 1.026, inclinationDeg: 1.85, color: 0xc1663f, phaseDeg: 40, texture: '/mars.jpg' },
  // Ceres: dwarf planet in the asteroid belt. Rotation 9 hours, small 4 degree axial tilt.
  { name: 'Ceres', au: 2.766, radiusEarths: 0.0737, periodDays: 1682, rotationDays: 0.378, inclinationDeg: 10.59, color: 0x8f8a84, phaseDeg: 260, axialTiltDeg: 4.0, texture: '/ceres.jpg' },
  { name: 'Jupiter', au: 5.203, radiusEarths: 10.97, periodDays: 4332.6, rotationDays: 0.4135, inclinationDeg: 1.30, color: 0xc9a37a, phaseDeg: 300, texture: '/jupiter.jpg', focusRadii: 7 },
  // Saturn: rings span the C ring's inner edge to the A ring's outer edge, in Saturn radii.
  { name: 'Saturn', au: 9.537, radiusEarths: 9.14, periodDays: 10759, rotationDays: 0.444, inclinationDeg: 2.49, color: 0xe3d2a6, phaseDeg: 150, focusRadii: 9, axialTiltDeg: 26.7, texture: '/saturn.jpg',
    rings: { innerRadii: 1.24, outerRadii: 2.27, color: 0xd8c9a3, opacity: 0.45, texture: '/saturn-ring.png' } },
  // Uranus: axis tilted 97.8 degrees, so it rolls around its orbit on its side. (Spin is
  // about its own tilted axis; the >90 degree tilt is what makes it retrograde to the ecliptic.)
  { name: 'Uranus', au: 19.19, radiusEarths: 3.98, periodDays: 30687, rotationDays: 0.718, inclinationDeg: 0.77, color: 0xa9d4d8, phaseDeg: 210, axialTiltDeg: 97.8, texture: '/uranus.jpg',
    // Main ring system spans ring 6 to the epsilon ring; dark and narrow, nothing like Saturn's.
    rings: { innerRadii: 1.64, outerRadii: 2.02, color: 0x8a8f93, opacity: 0.35, texture: '/uranus-ring.png' } },
  { name: 'Neptune', au: 30.07, radiusEarths: 3.86, periodDays: 60190, rotationDays: 0.671, inclinationDeg: 1.77, color: 0x3f5fbf, phaseDeg: 330, axialTiltDeg: 28.3, texture: '/neptune.jpg' },
  // Pluto: mean distance (its real orbit is eccentric enough to cross Neptune's), steeply
  // inclined, spinning on a 122 degree tilt (so retrograde to the ecliptic). Charon orbits its equator.
  // spinPhaseDeg = Charon's phaseDeg + 180: Pluto's prime meridian (lon 0, the map seam) is defined
  // as the sub-Charon point, so the heart (lon 180, map centre) faces away from Charon. Both turn at
  // the same rate, so this alignment holds: they are mutually locked.
  { name: 'Pluto', au: 39.48, radiusEarths: 0.1865, periodDays: 90560, rotationDays: 6.387, inclinationDeg: 17.16, color: 0xc9a98a, phaseDeg: 100, axialTiltDeg: 122.5, texture: '/pluto.jpg', spinPhaseDeg: 180 },
];
/** A favourite fact per body, shown under the name when the body is in focus. */
export const BODY_FACTS: Record<string, string> = {
  Io: "Io is the most volcanic body in the solar system. Before the discovery of erupting volcanoes on Io, we weren't aware of any other body in the solar system with active volcanism at all. It shows how quickly perspectives can change from exploration and new information.",
  Uranus: "Uranus spins on its side, suggesting a massive collision at some point in its past. Uranus has rings, just like Saturn does!",
};

// Shared across the Uranian moons.
const URANIAN_MOON_FACT =
  "Usually moons follow a Greek naming convention, while Roman names are reserved for planets. However, the Uranian system is named after characters from Shakespeare's plays. This is a remnant of its initial discovery by the British, who had named the planet George's Star.";
for (const name of ['Miranda', 'Ariel', 'Umbriel', 'Titania', 'Oberon']) {
  BODY_FACTS[name] = URANIAN_MOON_FACT;
}

/** Every focusable body name, for the terminal's `fly` command. */
export const BODY_NAMES: string[] = ['Sun', 'Mercury', 'Venus', 'Earth', 'Moon', ...PLANETS.filter((p) => !['Mercury', 'Venus'].includes(p.name)).map((p) => p.name), ...MOONS.map((m) => m.name)];
