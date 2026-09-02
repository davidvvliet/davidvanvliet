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
  { name: 'Enceladus', planet: 'Saturn', orbitPlanetRadii: 4.09, radiusEarths: 0.0396, periodDays: 1.370, inclinationDeg: 0.01, color: 0xf2f2f2, phaseDeg: 200 },
];

// Planets other than Earth (Earth is built separately: it has the continents,
// the location dots and the Moon). Adding a planet = one row.
export const PLANETS: PlanetSpec[] = [
  { name: 'Mercury', au: 0.387, radiusEarths: 0.383, periodDays: 87.97, rotationDays: 58.65, inclinationDeg: 7.0, color: 0x8a847c, phaseDeg: 120, texture: '/mercury.jpg' },
  // Venus rotates retrograde (negative period). Solid: it's a featureless cloud deck.
  { name: 'Venus', au: 0.723, radiusEarths: 0.949, periodDays: 224.7, rotationDays: -243.0, inclinationDeg: 3.39, color: 0xe8dcc0, phaseDeg: 230, texture: '/venus.jpg' },
  { name: 'Mars', au: 1.524, radiusEarths: 0.532, periodDays: 686.98, rotationDays: 1.026, inclinationDeg: 1.85, color: 0xc1663f, phaseDeg: 40, texture: '/mars.jpg' },
  { name: 'Jupiter', au: 5.203, radiusEarths: 10.97, periodDays: 4332.6, rotationDays: 0.4135, inclinationDeg: 1.30, color: 0xc9a37a, phaseDeg: 300, texture: '/jupiter.jpg', focusRadii: 7 },
  // Saturn: rings span the C ring's inner edge to the A ring's outer edge, in Saturn radii.
  { name: 'Saturn', au: 9.537, radiusEarths: 9.14, periodDays: 10759, rotationDays: 0.444, inclinationDeg: 2.49, color: 0xe3d2a6, phaseDeg: 150, focusRadii: 9, axialTiltDeg: 26.7, texture: '/saturn.jpg',
    rings: { innerRadii: 1.24, outerRadii: 2.27, color: 0xd8c9a3, opacity: 0.45, texture: '/saturn-ring.png' } },
];
/** A favourite fact per body, shown under the name when the body is in focus. */
export const BODY_FACTS: Record<string, string> = {
  Io: "Io is the most volcanic body in the solar system. Before the discovery of erupting volcanoes on Io, we weren't aware of any other body in the solar system with active volcanism at all. It shows how quickly perspectives can change from exploration and new information.",
};

/** Every focusable body name, for the terminal's `fly` command. */
export const BODY_NAMES: string[] = ['Sun', 'Mercury', 'Venus', 'Earth', 'Moon', ...PLANETS.filter((p) => !['Mercury', 'Venus'].includes(p.name)).map((p) => p.name), ...MOONS.map((m) => m.name)];
