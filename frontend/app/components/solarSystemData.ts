// Solar system body tables. Plain data (no three.js) so the terminal can
// import body names without pulling the renderer into its bundle.

export type PlanetSpec = {
  name: string;
  au: number;              // semi-major axis
  radiusEarths: number;    // radius relative to Earth
  periodDays: number;      // orbital period
  rotationDays: number;    // sidereal rotation period
  inclinationDeg: number;  // orbit inclination to the ecliptic
  eccentricity?: number;   // orbital eccentricity (0 = circle)
  perihelionDeg?: number;  // longitude of perihelion (J2000), direction of closest approach
  color: number;
  phaseDeg: number;        // starting mean anomaly
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
  faceOffsetDeg?: number;  // extra spin so the map's sub-planet point faces the planet (180 for maps centred on lon 180)
};

// Moons of the table planets (Earth's Moon is built separately). One row each.
export const MOONS: MoonSpec[] = [
  { name: 'Phobos', planet: 'Mars', orbitPlanetRadii: 2.77, radiusEarths: 0.00174, periodDays: 0.3189, inclinationDeg: 1.08, color: 0x7a746c, phaseDeg: 0 },
  { name: 'Deimos', planet: 'Mars', orbitPlanetRadii: 6.92, radiusEarths: 0.00097, periodDays: 1.263, inclinationDeg: 1.79, color: 0x7a746c, phaseDeg: 200 },
  // Galilean moons. Inclinations are to Jupiter's equator (its axis is tilted only 3 degrees).
  { name: 'Io', planet: 'Jupiter', orbitPlanetRadii: 5.90, radiusEarths: 0.286, periodDays: 1.769, inclinationDeg: 0.05, color: 0xd9c46a, phaseDeg: 0, texture: '/io.jpg' },
  { name: 'Europa', planet: 'Jupiter', orbitPlanetRadii: 9.39, radiusEarths: 0.245, periodDays: 3.551, inclinationDeg: 0.47, color: 0xc8bfae, phaseDeg: 90, texture: '/europa.jpg', faceOffsetDeg: 180 },
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
  // Dysnomia: Eris's moon, and the reason Eris's mass is known.
  { name: 'Dysnomia', planet: 'Eris', orbitPlanetRadii: 32.0, radiusEarths: 0.055, periodDays: 15.79, inclinationDeg: 0.0, color: 0x6e6a66, phaseDeg: 120 },
];

// Planets other than Earth (Earth is built separately: it has the continents,
// the location dots and the Moon). Adding a planet = one row.
export const PLANETS: PlanetSpec[] = [
  { name: 'Mercury', au: 0.387, radiusEarths: 0.383, periodDays: 87.97, rotationDays: 58.65, inclinationDeg: 7.0, eccentricity: 0.2056, perihelionDeg: 77.46, axialTiltDeg: 0.03, color: 0x8a847c, phaseDeg: 120, texture: '/mercury.jpg' },
  // Venus: retrograde spin expressed as a 177 degree axial tilt (same convention as Uranus and Pluto).
  { name: 'Venus', au: 0.723, radiusEarths: 0.949, periodDays: 224.7, rotationDays: 243.0, inclinationDeg: 3.39, eccentricity: 0.0068, perihelionDeg: 131.6, axialTiltDeg: 177.4, color: 0xe8dcc0, phaseDeg: 230, texture: '/venus.jpg' },
  { name: 'Mars', au: 1.524, radiusEarths: 0.532, periodDays: 686.98, rotationDays: 1.026, inclinationDeg: 1.85, eccentricity: 0.0934, perihelionDeg: 336.0, axialTiltDeg: 25.19, color: 0xc1663f, phaseDeg: 40, texture: '/mars.jpg' },
  // Ceres: dwarf planet in the asteroid belt. Rotation 9 hours, small 4 degree axial tilt.
  { name: 'Ceres', au: 2.766, radiusEarths: 0.0737, periodDays: 1682, rotationDays: 0.378, inclinationDeg: 10.59, eccentricity: 0.0785, perihelionDeg: 153.4, color: 0x8f8a84, phaseDeg: 260, axialTiltDeg: 4.0, texture: '/ceres.jpg' },
  { name: 'Jupiter', au: 5.203, radiusEarths: 10.97, periodDays: 4332.6, rotationDays: 0.4135, inclinationDeg: 1.30, eccentricity: 0.0489, perihelionDeg: 14.7, axialTiltDeg: 3.13, color: 0xc9a37a, phaseDeg: 300, texture: '/jupiter.jpg', focusRadii: 7 },
  // Saturn: rings span the C ring's inner edge to the A ring's outer edge, in Saturn radii.
  { name: 'Saturn', au: 9.537, radiusEarths: 9.14, periodDays: 10759, rotationDays: 0.444, inclinationDeg: 2.49, eccentricity: 0.0565, perihelionDeg: 92.6, color: 0xe3d2a6, phaseDeg: 150, focusRadii: 9, axialTiltDeg: 26.7, texture: '/saturn.jpg',
    rings: { innerRadii: 1.24, outerRadii: 2.27, color: 0xd8c9a3, opacity: 0.45, texture: '/saturn-ring.png' } },
  // Uranus: axis tilted 97.8 degrees, so it rolls around its orbit on its side. (Spin is
  // about its own tilted axis; the >90 degree tilt is what makes it retrograde to the ecliptic.)
  { name: 'Uranus', au: 19.19, radiusEarths: 3.98, periodDays: 30687, rotationDays: 0.718, inclinationDeg: 0.77, eccentricity: 0.0457, perihelionDeg: 170.9, color: 0xa9d4d8, phaseDeg: 210, axialTiltDeg: 97.8, texture: '/uranus.jpg',
    // Main ring system spans ring 6 to the epsilon ring; dark and narrow, nothing like Saturn's.
    rings: { innerRadii: 1.64, outerRadii: 2.02, color: 0x8a8f93, opacity: 0.35, texture: '/uranus-ring.png' } },
  { name: 'Neptune', au: 30.07, radiusEarths: 3.86, periodDays: 60190, rotationDays: 0.671, inclinationDeg: 1.77, eccentricity: 0.0113, perihelionDeg: 45.0, color: 0x3f5fbf, phaseDeg: 330, axialTiltDeg: 28.3, texture: '/neptune.jpg' },
  // Pluto: mean distance (its real orbit is eccentric enough to cross Neptune's), steeply
  // inclined, spinning on a 122 degree tilt (so retrograde to the ecliptic). Charon orbits its equator.
  // spinPhaseDeg = Charon's phaseDeg + 180: Pluto's prime meridian (lon 0, the map seam) is defined
  // as the sub-Charon point, so the heart (lon 180, map centre) faces away from Charon. Both turn at
  // the same rate, so this alignment holds: they are mutually locked.
  { name: 'Pluto', au: 39.48, radiusEarths: 0.1865, periodDays: 90560, rotationDays: 6.387, inclinationDeg: 17.16, eccentricity: 0.2488, perihelionDeg: 224.1, color: 0xc9a98a, phaseDeg: 100, axialTiltDeg: 122.5, texture: '/pluto.jpg', spinPhaseDeg: 180 },
  // Two more dwarf planets. Their maps are artist's impressions: no spacecraft has visited either.
  { name: 'Makemake', au: 45.43, radiusEarths: 0.1122, periodDays: 111800, rotationDays: 0.95, inclinationDeg: 28.98, eccentricity: 0.161, perihelionDeg: 14.4, color: 0xb5745f, phaseDeg: 190, texture: '/makemake.jpg' },
  { name: 'Eris', au: 67.86, radiusEarths: 0.1826, periodDays: 204200, rotationDays: 1.08, inclinationDeg: 44.04, eccentricity: 0.436, perihelionDeg: 187.5, axialTiltDeg: 78, color: 0xd9d9d9, phaseDeg: 300, texture: '/eris.jpg' },
];
/** A favourite fact per body, shown under the name when the body is in focus. */
export const BODY_FACTS: Record<string, string> = {
  Io: "Io is the most volcanic body in the solar system. Before the discovery of erupting volcanoes on Io, we weren't aware of any other body in the solar system with active volcanism at all. It shows how quickly perspectives can change from exploration and new information. Thank you Voyager 1 :)",
  Uranus: "Uranus spins on its side, suggesting a massive collision at some point in its past. Uranus has rings, just like Saturn does! Neptune and Jupiter actually have rings as well, likely from small debris coming from their moons, but they're much fainter.",
  Neptune: "We've only visited Neptune once, with Voyager 2 in 1989. It imaged the dark spot storm that you can see here. This storm has since disappeared. Jupiter's red spot has lasted for centuries, suggesting that Neptune's climate changes far more rapidly.",
  Eris: "We have never sent a spacecraft to Eris, so we don't know what its surface looks like. This map is a fictional interpretation. Discovering more of these planet-like objects that didn't dominate their own orbit led to a reworking of the planet definition, causing Pluto to be demoted as well.",
  Makemake: "We have never sent a spacecraft to Makemake, so we don't know what its surface looks like. This map is a fictional interpretation. We do know that it appears red/brown, from frozen methane on its surface.",
  Saturn: "My favorite thing about Saturn is the hexagonal storm at its north pole. About four Earths could fit inside it. It's an amazing display of fluid dynamics at a colossal scale.",
  Mercury: "I would love to disassemble this planet and use the material for a Dyson sphere. Even if it were entirely gone from the solar system, it would not destabilize any of the other planets' orbits.",
  Venus: "Venus is very similar to Earth. It is in the habitable zone and is roughly the same size. However, even with these similarities, their paths have clearly diverged significantly. These facts make Venus an important point of interest for understanding how planets behave and for studying what habitable zone exoplanets might be like.",
};

// Shared across the Uranian moons.
const URANIAN_MOON_FACT =
  "Usually moons follow a Greek naming convention, while Roman names are reserved for planets. However, the Uranian system is named after characters from Shakespeare's plays. This is a remnant of its initial discovery by the British, who had named the planet George's Star.";
for (const name of ['Miranda', 'Ariel', 'Umbriel', 'Titania', 'Oberon']) {
  BODY_FACTS[name] = URANIAN_MOON_FACT;
}

/** Every focusable body name, for the terminal's `fly` command. */
export const BODY_NAMES: string[] = ['Sun', 'Mercury', 'Venus', 'Earth', 'Moon', ...PLANETS.filter((p) => !['Mercury', 'Venus'].includes(p.name)).map((p) => p.name), ...MOONS.map((m) => m.name)];

// --- Stars ---
// The ten brightest stars in the night sky (plus Polaris, as a check that the
// sky is aligned: it should sit over Earth's north pole). J2000 coordinates.
// Only direction is used; at solar-system scale their parallax is nil.
export type StarSpec = {
  name: string;
  raDeg: number;           // right ascension, degrees
  decDeg: number;          // declination, degrees
  magnitude: number;       // apparent visual magnitude
  spectral: 'O' | 'B' | 'A' | 'F' | 'G' | 'K' | 'M';
  lightYears: number;      // distance, for the hover label
  fact?: string;           // shown under the name on hover
};

export const STARS: StarSpec[] = [
  { name: 'Sirius', raDeg: 101.287, decDeg: -16.716, magnitude: -1.46, spectral: 'A', lightYears: 8.6, fact: 'The brightest star in our night sky.' },
  { name: 'Canopus', raDeg: 95.988, decDeg: -52.696, magnitude: -0.74, spectral: 'F', lightYears: 310, fact: "My favorite thing about Canopus is that it's commonly used in star tracking by spacecraft. It's used for the roll component of a spacecraft's orientation, where the Sun is used for pitch and yaw. Canopus' brightness (2nd brightest in our night sky) and position make it ideal." },
  { name: 'Alpha Centauri', raDeg: 219.902, decDeg: -60.834, magnitude: -0.27, spectral: 'G', lightYears: 4.4, fact: 'The closest star system to the Sun.' },
  { name: 'Arcturus', raDeg: 213.915, decDeg: 19.182, magnitude: -0.05, spectral: 'K', lightYears: 37 },
  { name: 'Vega', raDeg: 279.235, decDeg: 38.784, magnitude: 0.03, spectral: 'A', lightYears: 25 },
  { name: 'Capella', raDeg: 79.172, decDeg: 45.998, magnitude: 0.08, spectral: 'G', lightYears: 43 },
  { name: 'Rigel', raDeg: 78.634, decDeg: -8.202, magnitude: 0.13, spectral: 'B', lightYears: 860, fact: 'One of my favorite stars.' },
  { name: 'Procyon', raDeg: 114.826, decDeg: 5.225, magnitude: 0.34, spectral: 'F', lightYears: 11 },
  { name: 'Achernar', raDeg: 24.429, decDeg: -57.237, magnitude: 0.46, spectral: 'B', lightYears: 140 },
  { name: 'Betelgeuse', raDeg: 88.793, decDeg: 7.407, magnitude: 0.50, spectral: 'M', lightYears: 550, fact: 'Betelgeuse is unstable and will likely go supernova within 100,000 years. The explosion will be visible from Earth for months and will shine as bright as a full moon. Earth is far enough away to be safe from this event.' },
  { name: 'Polaris', raDeg: 37.954, decDeg: 89.264, magnitude: 1.98, spectral: 'F', lightYears: 430 },
  // The rest of Orion (Betelgeuse and Rigel are above): shoulders, belt, knee, head.
  { name: 'Bellatrix', raDeg: 81.283, decDeg: 6.350, magnitude: 1.64, spectral: 'B', lightYears: 250 },
  { name: 'Mintaka', raDeg: 83.002, decDeg: -0.299, magnitude: 2.23, spectral: 'O', lightYears: 1200 },
  { name: 'Alnilam', raDeg: 84.053, decDeg: -1.202, magnitude: 1.69, spectral: 'B', lightYears: 2000 },
  { name: 'Alnitak', raDeg: 85.190, decDeg: -1.943, magnitude: 1.77, spectral: 'O', lightYears: 1260 },
  { name: 'Saiph', raDeg: 86.939, decDeg: -9.670, magnitude: 2.09, spectral: 'B', lightYears: 650 },
  { name: 'Meissa', raDeg: 83.784, decDeg: 9.934, magnitude: 3.39, spectral: 'O', lightYears: 1100 },
  // The Southern Cross (Crux).
  { name: 'Acrux', raDeg: 186.650, decDeg: -63.099, magnitude: 0.76, spectral: 'B', lightYears: 320 },
  { name: 'Mimosa', raDeg: 191.930, decDeg: -59.689, magnitude: 1.25, spectral: 'B', lightYears: 280 },
  { name: 'Gacrux', raDeg: 187.791, decDeg: -57.113, magnitude: 1.64, spectral: 'M', lightYears: 89 },
  { name: 'Imai', raDeg: 183.786, decDeg: -58.749, magnitude: 2.79, spectral: 'B', lightYears: 345 },
  { name: 'Ginan', raDeg: 185.340, decDeg: -60.401, magnitude: 3.59, spectral: 'K', lightYears: 230 },
  // Canis Major (Sirius is above).
  { name: 'Adhara', raDeg: 104.656, decDeg: -28.972, magnitude: 1.50, spectral: 'B', lightYears: 430 },
  { name: 'Wezen', raDeg: 107.098, decDeg: -26.393, magnitude: 1.83, spectral: 'F', lightYears: 1600 },
  { name: 'Mirzam', raDeg: 95.675, decDeg: -17.956, magnitude: 1.98, spectral: 'B', lightYears: 490 },
  { name: 'Aludra', raDeg: 111.024, decDeg: -29.303, magnitude: 2.45, spectral: 'B', lightYears: 2000 },
  { name: 'Furud', raDeg: 95.078, decDeg: -30.063, magnitude: 3.02, spectral: 'B', lightYears: 360 },
  // Ursa Major: the Big Dipper.
  { name: 'Dubhe', raDeg: 165.932, decDeg: 61.751, magnitude: 1.79, spectral: 'K', lightYears: 123 },
  { name: 'Merak', raDeg: 165.460, decDeg: 56.383, magnitude: 2.37, spectral: 'A', lightYears: 80 },
  { name: 'Phecda', raDeg: 178.458, decDeg: 53.695, magnitude: 2.44, spectral: 'A', lightYears: 83 },
  { name: 'Megrez', raDeg: 183.857, decDeg: 57.033, magnitude: 3.31, spectral: 'A', lightYears: 81 },
  { name: 'Alioth', raDeg: 193.507, decDeg: 55.960, magnitude: 1.77, spectral: 'A', lightYears: 83 },
  { name: 'Mizar', raDeg: 200.981, decDeg: 54.925, magnitude: 2.04, spectral: 'A', lightYears: 83 },
  { name: 'Alkaid', raDeg: 206.885, decDeg: 49.313, magnitude: 1.86, spectral: 'B', lightYears: 104 },
  // Ursa Minor: the Little Dipper (Polaris is above). Faint apart from Kochab.
  { name: 'Kochab', raDeg: 222.676, decDeg: 74.156, magnitude: 2.08, spectral: 'K', lightYears: 130 },
  { name: 'Pherkad', raDeg: 230.182, decDeg: 71.834, magnitude: 3.05, spectral: 'A', lightYears: 490 },
  { name: 'Yildun', raDeg: 263.054, decDeg: 86.586, magnitude: 4.36, spectral: 'A', lightYears: 172 },
  { name: 'Epsilon Ursae Minoris', raDeg: 251.493, decDeg: 82.037, magnitude: 4.23, spectral: 'G', lightYears: 300 },
  { name: 'Zeta Ursae Minoris', raDeg: 236.015, decDeg: 77.794, magnitude: 4.32, spectral: 'A', lightYears: 380 },
  { name: 'Eta Ursae Minoris', raDeg: 244.376, decDeg: 75.755, magnitude: 4.95, spectral: 'F', lightYears: 97 },
  // Auriga (Capella is above). Elnath is formally Taurus's but completes Auriga's pentagon.
  { name: 'Menkalinan', raDeg: 89.882, decDeg: 44.948, magnitude: 1.90, spectral: 'A', lightYears: 81 },
  { name: 'Mahasim', raDeg: 89.930, decDeg: 37.213, magnitude: 2.65, spectral: 'A', lightYears: 166 },
  { name: 'Hassaleh', raDeg: 74.248, decDeg: 33.166, magnitude: 2.69, spectral: 'K', lightYears: 490 },
  { name: 'Almaaz', raDeg: 75.492, decDeg: 43.823, magnitude: 3.00, spectral: 'F', lightYears: 2000 },
  { name: 'Haedus', raDeg: 76.629, decDeg: 41.234, magnitude: 3.18, spectral: 'B', lightYears: 243 },
  { name: 'Saclateni', raDeg: 75.620, decDeg: 41.076, magnitude: 3.75, spectral: 'K', lightYears: 790 },
  { name: 'Elnath', raDeg: 81.573, decDeg: 28.608, magnitude: 1.65, spectral: 'B', lightYears: 134 },
  // Cassiopeia: the W.
  { name: 'Schedar', raDeg: 10.127, decDeg: 56.537, magnitude: 2.24, spectral: 'K', lightYears: 228 },
  { name: 'Caph', raDeg: 2.295, decDeg: 59.150, magnitude: 2.28, spectral: 'F', lightYears: 54 },
  { name: 'Navi', raDeg: 14.177, decDeg: 60.717, magnitude: 2.15, spectral: 'B', lightYears: 550 },
  { name: 'Ruchbah', raDeg: 21.454, decDeg: 60.235, magnitude: 2.68, spectral: 'A', lightYears: 99 },
  { name: 'Segin', raDeg: 28.599, decDeg: 63.670, magnitude: 3.37, spectral: 'B', lightYears: 440 },
  // Cygnus: the Northern Cross. Deneb is the tail, Albireo the head (a famous gold-and-blue double).
  { name: 'Deneb', raDeg: 310.358, decDeg: 45.280, magnitude: 1.25, spectral: 'A', lightYears: 2600, fact: "Deneb is also used for star tracking at times. It is bright and sits nearly opposite the default reference, Canopus. For example, Voyager 2 was commanded to acquire the star in 1977 so that it could flip over." },
  { name: 'Sadr', raDeg: 305.557, decDeg: 40.257, magnitude: 2.23, spectral: 'F', lightYears: 1800 },
  { name: 'Aljanah', raDeg: 311.553, decDeg: 33.970, magnitude: 2.48, spectral: 'K', lightYears: 72 },
  { name: 'Fawaris', raDeg: 296.244, decDeg: 45.131, magnitude: 2.87, spectral: 'B', lightYears: 165 },
  { name: 'Albireo', raDeg: 292.680, decDeg: 27.960, magnitude: 3.18, spectral: 'K', lightYears: 430 },
  { name: 'Zeta Cygni', raDeg: 318.234, decDeg: 30.227, magnitude: 3.20, spectral: 'G', lightYears: 143 },
  { name: 'Iota Cygni', raDeg: 292.427, decDeg: 51.730, magnitude: 3.77, spectral: 'A', lightYears: 121 },
  { name: 'Kappa Cygni', raDeg: 289.276, decDeg: 53.369, magnitude: 3.80, spectral: 'G', lightYears: 124 },
  // Lyra (Vega is above): a small parallelogram hanging off Vega. Epsilon Lyrae is the "Double Double".
  { name: 'Sheliak', raDeg: 282.520, decDeg: 33.363, magnitude: 3.52, spectral: 'B', lightYears: 960 },
  { name: 'Sulafat', raDeg: 284.736, decDeg: 32.690, magnitude: 3.25, spectral: 'B', lightYears: 620 },
  { name: 'Delta Lyrae', raDeg: 283.626, decDeg: 36.899, magnitude: 4.22, spectral: 'M', lightYears: 740 },
  { name: 'Zeta Lyrae', raDeg: 281.193, decDeg: 37.605, magnitude: 4.34, spectral: 'A', lightYears: 156 },
  { name: 'Epsilon Lyrae', raDeg: 281.085, decDeg: 39.670, magnitude: 4.67, spectral: 'A', lightYears: 160 },
  // Bootes (Arcturus is above): the kite.
  { name: 'Izar', raDeg: 221.247, decDeg: 27.074, magnitude: 2.37, spectral: 'K', lightYears: 202 },
  { name: 'Muphrid', raDeg: 208.671, decDeg: 18.398, magnitude: 2.68, spectral: 'G', lightYears: 37 },
  { name: 'Seginus', raDeg: 218.019, decDeg: 38.308, magnitude: 3.03, spectral: 'A', lightYears: 87 },
  { name: 'Nekkar', raDeg: 225.487, decDeg: 40.391, magnitude: 3.49, spectral: 'G', lightYears: 225 },
  { name: 'Delta Bootis', raDeg: 228.876, decDeg: 33.315, magnitude: 3.47, spectral: 'G', lightYears: 122 },
  { name: 'Rho Bootis', raDeg: 217.957, decDeg: 30.371, magnitude: 3.58, spectral: 'K', lightYears: 160 },
  { name: 'Xuange', raDeg: 214.096, decDeg: 46.088, magnitude: 4.18, spectral: 'A', lightYears: 99 },
  // Triangulum: a small, faint triangle below Andromeda.
  { name: 'Beta Trianguli', raDeg: 32.386, decDeg: 34.987, magnitude: 3.00, spectral: 'A', lightYears: 127 },
  { name: 'Mothallah', raDeg: 28.270, decDeg: 29.579, magnitude: 3.41, spectral: 'F', lightYears: 63 },
  { name: 'Gamma Trianguli', raDeg: 34.329, decDeg: 33.847, magnitude: 4.01, spectral: 'A', lightYears: 112 },
  // Leo: the Sickle (Regulus up through Rasalas) and the hindquarters (Denebola, Zosma, Chertan).
  { name: 'Regulus', raDeg: 152.093, decDeg: 11.967, magnitude: 1.36, spectral: 'B', lightYears: 79 },
  { name: 'Denebola', raDeg: 177.265, decDeg: 14.572, magnitude: 2.14, spectral: 'A', lightYears: 36 },
  { name: 'Algieba', raDeg: 154.993, decDeg: 19.842, magnitude: 2.01, spectral: 'K', lightYears: 130 },
  { name: 'Zosma', raDeg: 168.527, decDeg: 20.524, magnitude: 2.56, spectral: 'A', lightYears: 58 },
  { name: 'Chertan', raDeg: 168.560, decDeg: 15.430, magnitude: 3.32, spectral: 'A', lightYears: 165 },
  { name: 'Adhafera', raDeg: 154.173, decDeg: 23.417, magnitude: 3.44, spectral: 'F', lightYears: 274 },
  { name: 'Rasalas', raDeg: 148.191, decDeg: 26.007, magnitude: 3.88, spectral: 'K', lightYears: 124 },
  { name: 'Algenubi', raDeg: 146.463, decDeg: 23.774, magnitude: 2.98, spectral: 'G', lightYears: 247 },
  // Virgo: Spica and the Y-shaped bowl.
  { name: 'Spica', raDeg: 201.298, decDeg: -11.161, magnitude: 0.97, spectral: 'B', lightYears: 250 },
  { name: 'Porrima', raDeg: 190.415, decDeg: -1.449, magnitude: 2.74, spectral: 'F', lightYears: 38 },
  { name: 'Vindemiatrix', raDeg: 195.544, decDeg: 10.959, magnitude: 2.83, spectral: 'G', lightYears: 110 },
  { name: 'Heze', raDeg: 203.673, decDeg: -0.596, magnitude: 3.38, spectral: 'A', lightYears: 74 },
  { name: 'Auva', raDeg: 193.901, decDeg: 3.397, magnitude: 3.38, spectral: 'M', lightYears: 198 },
  { name: 'Zavijava', raDeg: 177.674, decDeg: 1.765, magnitude: 3.60, spectral: 'F', lightYears: 36 },
  { name: 'Zaniah', raDeg: 184.977, decDeg: -0.667, magnitude: 3.89, spectral: 'A', lightYears: 265 },
  { name: 'Syrma', raDeg: 214.004, decDeg: -6.000, magnitude: 4.08, spectral: 'F', lightYears: 70 },
  // Centaurus (Alpha Centauri is above). Hadar is the other Pointer to the Southern Cross.
  { name: 'Hadar', raDeg: 210.956, decDeg: -60.373, magnitude: 0.61, spectral: 'B', lightYears: 390 },
  { name: 'Menkent', raDeg: 211.671, decDeg: -36.370, magnitude: 2.06, spectral: 'K', lightYears: 59 },
  { name: 'Muhlifain', raDeg: 190.379, decDeg: -48.960, magnitude: 2.17, spectral: 'A', lightYears: 130 },
  { name: 'Epsilon Centauri', raDeg: 204.972, decDeg: -53.466, magnitude: 2.30, spectral: 'B', lightYears: 430 },
  { name: 'Eta Centauri', raDeg: 218.877, decDeg: -42.158, magnitude: 2.31, spectral: 'B', lightYears: 310 },
  { name: 'Zeta Centauri', raDeg: 208.885, decDeg: -47.288, magnitude: 2.55, spectral: 'B', lightYears: 380 },
  { name: 'Delta Centauri', raDeg: 182.090, decDeg: -50.722, magnitude: 2.58, spectral: 'B', lightYears: 400 },
  { name: 'Iota Centauri', raDeg: 200.149, decDeg: -36.712, magnitude: 2.75, spectral: 'A', lightYears: 59 },
  // Scorpius: Antares at the heart, the curved tail ending at Shaula and Lesath (the Stinger).
  { name: 'Antares', raDeg: 247.352, decDeg: -26.432, magnitude: 1.06, spectral: 'M', lightYears: 550 },
  { name: 'Shaula', raDeg: 263.402, decDeg: -37.104, magnitude: 1.62, spectral: 'B', lightYears: 570 },
  { name: 'Sargas', raDeg: 264.330, decDeg: -42.998, magnitude: 1.86, spectral: 'F', lightYears: 300 },
  { name: 'Dschubba', raDeg: 240.083, decDeg: -22.622, magnitude: 2.29, spectral: 'B', lightYears: 490 },
  { name: 'Larawag', raDeg: 252.541, decDeg: -34.293, magnitude: 2.29, spectral: 'K', lightYears: 64 },
  { name: 'Girtab', raDeg: 265.622, decDeg: -39.030, magnitude: 2.39, spectral: 'B', lightYears: 480 },
  { name: 'Acrab', raDeg: 241.359, decDeg: -19.806, magnitude: 2.56, spectral: 'B', lightYears: 400 },
  { name: 'Lesath', raDeg: 262.691, decDeg: -37.296, magnitude: 2.70, spectral: 'B', lightYears: 580 },
  { name: 'Paikauhale', raDeg: 248.971, decDeg: -28.216, magnitude: 2.82, spectral: 'B', lightYears: 470 },
  { name: 'Fang', raDeg: 239.713, decDeg: -26.114, magnitude: 2.89, spectral: 'B', lightYears: 460 },
  { name: 'Alniyat', raDeg: 245.297, decDeg: -25.593, magnitude: 2.89, spectral: 'B', lightYears: 570 },
  { name: 'Iota Scorpii', raDeg: 266.896, decDeg: -40.127, magnitude: 3.03, spectral: 'F', lightYears: 1900 },
  { name: 'Mu Scorpii', raDeg: 252.968, decDeg: -38.047, magnitude: 3.04, spectral: 'B', lightYears: 500 },
  { name: 'Eta Scorpii', raDeg: 258.038, decDeg: -43.239, magnitude: 3.33, spectral: 'F', lightYears: 73 },
  { name: 'Zeta Scorpii', raDeg: 253.646, decDeg: -42.361, magnitude: 3.62, spectral: 'K', lightYears: 130 },
  // Sagittarius: the Teapot, pointing at the galactic centre.
  { name: 'Kaus Australis', raDeg: 276.043, decDeg: -34.385, magnitude: 1.85, spectral: 'B', lightYears: 143 },
  { name: 'Nunki', raDeg: 283.816, decDeg: -26.297, magnitude: 2.05, spectral: 'B', lightYears: 228 },
  { name: 'Ascella', raDeg: 285.653, decDeg: -29.880, magnitude: 2.60, spectral: 'A', lightYears: 88 },
  { name: 'Kaus Media', raDeg: 275.248, decDeg: -29.828, magnitude: 2.70, spectral: 'K', lightYears: 350 },
  { name: 'Kaus Borealis', raDeg: 276.993, decDeg: -25.422, magnitude: 2.82, spectral: 'K', lightYears: 78 },
  { name: 'Albaldah', raDeg: 287.441, decDeg: -21.024, magnitude: 2.89, spectral: 'F', lightYears: 510 },
  { name: 'Alnasl', raDeg: 271.452, decDeg: -30.424, magnitude: 2.98, spectral: 'K', lightYears: 97 },
  { name: 'Phi Sagittarii', raDeg: 281.414, decDeg: -26.991, magnitude: 3.17, spectral: 'B', lightYears: 240 },
  { name: 'Tau Sagittarii', raDeg: 286.735, decDeg: -27.670, magnitude: 3.32, spectral: 'K', lightYears: 120 },
  // Taurus: Aldebaran and the Hyades (the V), plus the Pleiades cluster. Elnath is above.
  { name: 'Aldebaran', raDeg: 68.980, decDeg: 16.509, magnitude: 0.85, spectral: 'K', lightYears: 65 },
  { name: 'Tianguan', raDeg: 84.411, decDeg: 21.143, magnitude: 3.01, spectral: 'B', lightYears: 440 },
  { name: 'Chamukuy', raDeg: 67.166, decDeg: 15.871, magnitude: 3.40, spectral: 'A', lightYears: 150 },
  { name: 'Lambda Tauri', raDeg: 60.170, decDeg: 12.490, magnitude: 3.47, spectral: 'B', lightYears: 480 },
  { name: 'Ain', raDeg: 67.154, decDeg: 19.181, magnitude: 3.53, spectral: 'K', lightYears: 147 },
  { name: 'Prima Hyadum', raDeg: 64.948, decDeg: 15.628, magnitude: 3.65, spectral: 'K', lightYears: 154 },
  { name: 'Secunda Hyadum', raDeg: 65.734, decDeg: 17.543, magnitude: 3.77, spectral: 'K', lightYears: 156 },
  { name: 'Alcyone', raDeg: 56.871, decDeg: 24.105, magnitude: 2.87, spectral: 'B', lightYears: 440 },
  { name: 'Atlas', raDeg: 57.291, decDeg: 24.053, magnitude: 3.62, spectral: 'B', lightYears: 440 },
  { name: 'Electra', raDeg: 56.219, decDeg: 24.113, magnitude: 3.70, spectral: 'B', lightYears: 440 },
  { name: 'Maia', raDeg: 56.457, decDeg: 24.368, magnitude: 3.87, spectral: 'B', lightYears: 440 },
  { name: 'Merope', raDeg: 56.582, decDeg: 23.948, magnitude: 4.18, spectral: 'B', lightYears: 440 },
  { name: 'Taygeta', raDeg: 56.302, decDeg: 24.467, magnitude: 4.30, spectral: 'B', lightYears: 440 },
  // Gemini: the twins, Castor and Pollux at the heads.
  { name: 'Pollux', raDeg: 116.329, decDeg: 28.026, magnitude: 1.14, spectral: 'K', lightYears: 34 },
  { name: 'Castor', raDeg: 113.650, decDeg: 31.888, magnitude: 1.58, spectral: 'A', lightYears: 51 },
  { name: 'Alhena', raDeg: 99.428, decDeg: 16.399, magnitude: 1.93, spectral: 'A', lightYears: 109 },
  { name: 'Tejat', raDeg: 95.740, decDeg: 22.514, magnitude: 2.87, spectral: 'M', lightYears: 230 },
  { name: 'Mebsuta', raDeg: 100.983, decDeg: 25.131, magnitude: 3.06, spectral: 'G', lightYears: 840 },
  { name: 'Propus', raDeg: 93.720, decDeg: 22.507, magnitude: 3.28, spectral: 'M', lightYears: 380 },
  { name: 'Alzirr', raDeg: 101.322, decDeg: 12.896, magnitude: 3.35, spectral: 'F', lightYears: 59 },
  { name: 'Wasat', raDeg: 110.031, decDeg: 21.982, magnitude: 3.53, spectral: 'F', lightYears: 60 },
  { name: 'Kappa Geminorum', raDeg: 116.112, decDeg: 24.398, magnitude: 3.57, spectral: 'G', lightYears: 141 },
  { name: 'Mekbuda', raDeg: 106.027, decDeg: 20.570, magnitude: 3.93, spectral: 'F', lightYears: 1200 },
  // Aquila: Altair completes the Summer Triangle with Vega and Deneb.
  { name: 'Altair', raDeg: 297.696, decDeg: 8.868, magnitude: 0.77, spectral: 'A', lightYears: 17, fact: 'I love the name of this star. It means something like the flying eagle in Arabic. Many stars have Arabic-origin names because Arab astronomers preserved and expanded upon ancient star catalogs.' },
  { name: 'Tarazed', raDeg: 296.565, decDeg: 10.613, magnitude: 2.72, spectral: 'K', lightYears: 395 },
  { name: 'Okab', raDeg: 286.353, decDeg: 13.864, magnitude: 2.99, spectral: 'A', lightYears: 83 },
  { name: 'Theta Aquilae', raDeg: 302.826, decDeg: -0.821, magnitude: 3.24, spectral: 'B', lightYears: 290 },
  { name: 'Delta Aquilae', raDeg: 291.375, decDeg: 3.115, magnitude: 3.36, spectral: 'F', lightYears: 50 },
  { name: 'Lambda Aquilae', raDeg: 286.562, decDeg: -4.883, magnitude: 3.43, spectral: 'B', lightYears: 125 },
  { name: 'Alshain', raDeg: 298.828, decDeg: 6.407, magnitude: 3.71, spectral: 'G', lightYears: 45 },
  { name: 'Eta Aquilae', raDeg: 298.118, decDeg: 1.006, magnitude: 3.87, spectral: 'F', lightYears: 1400 },
  // Piscis Austrinus and Grus: the bright, lonely stars of the southern autumn sky.
  { name: 'Fomalhaut', raDeg: 344.413, decDeg: -29.622, magnitude: 1.16, spectral: 'A', lightYears: 25 },
  { name: 'Alnair', raDeg: 332.058, decDeg: -46.961, magnitude: 1.74, spectral: 'B', lightYears: 101 },
  { name: 'Tiaki', raDeg: 340.667, decDeg: -46.885, magnitude: 2.11, spectral: 'M', lightYears: 170 },
  { name: 'Aldhanab', raDeg: 328.482, decDeg: -37.365, magnitude: 3.01, spectral: 'B', lightYears: 210 },
  { name: 'Epsilon Gruis', raDeg: 342.139, decDeg: -51.317, magnitude: 3.49, spectral: 'A', lightYears: 130 },
  { name: 'Delta Gruis', raDeg: 337.318, decDeg: -43.496, magnitude: 3.97, spectral: 'G', lightYears: 300 },
  // Carina, Vela, Puppis: the old ship Argo (Canopus is above). Includes the False Cross.
  { name: 'Miaplacidus', raDeg: 138.300, decDeg: -69.717, magnitude: 1.68, spectral: 'A', lightYears: 113 },
  { name: 'Avior', raDeg: 125.628, decDeg: -59.509, magnitude: 1.86, spectral: 'K', lightYears: 610 },
  { name: 'Aspidiske', raDeg: 139.273, decDeg: -59.275, magnitude: 2.21, spectral: 'A', lightYears: 690 },
  { name: 'Theta Carinae', raDeg: 160.739, decDeg: -64.394, magnitude: 2.76, spectral: 'B', lightYears: 460 },
  { name: 'Upsilon Carinae', raDeg: 146.775, decDeg: -65.072, magnitude: 2.97, spectral: 'A', lightYears: 1600 },
  { name: 'Regor', raDeg: 122.383, decDeg: -47.337, magnitude: 1.78, spectral: 'O', lightYears: 1100 },
  { name: 'Alsephina', raDeg: 131.176, decDeg: -54.709, magnitude: 1.96, spectral: 'A', lightYears: 80 },
  { name: 'Suhail', raDeg: 136.999, decDeg: -43.433, magnitude: 2.21, spectral: 'K', lightYears: 545 },
  { name: 'Markeb', raDeg: 140.528, decDeg: -55.011, magnitude: 2.48, spectral: 'B', lightYears: 570 },
  { name: 'Mu Velorum', raDeg: 161.692, decDeg: -49.420, magnitude: 2.69, spectral: 'G', lightYears: 117 },
  { name: 'Naos', raDeg: 120.896, decDeg: -40.003, magnitude: 2.25, spectral: 'O', lightYears: 1080 },
  { name: 'Pi Puppis', raDeg: 109.286, decDeg: -37.098, magnitude: 2.71, spectral: 'K', lightYears: 810 },
  { name: 'Tureis', raDeg: 121.886, decDeg: -24.304, magnitude: 2.81, spectral: 'F', lightYears: 64 },
  { name: 'Tau Puppis', raDeg: 102.484, decDeg: -50.615, magnitude: 2.94, spectral: 'K', lightYears: 182 },
  // Perseus: Mirfak and the Demon Star, Algol.
  { name: 'Mirfak', raDeg: 51.081, decDeg: 49.861, magnitude: 1.79, spectral: 'F', lightYears: 510 },
  { name: 'Algol', raDeg: 47.042, decDeg: 40.956, magnitude: 2.12, spectral: 'B', lightYears: 90 },
  { name: 'Zeta Persei', raDeg: 58.533, decDeg: 31.884, magnitude: 2.85, spectral: 'B', lightYears: 750 },
  { name: 'Epsilon Persei', raDeg: 59.463, decDeg: 40.010, magnitude: 2.89, spectral: 'B', lightYears: 640 },
  { name: 'Gamma Persei', raDeg: 46.199, decDeg: 53.506, magnitude: 2.93, spectral: 'G', lightYears: 240 },
  { name: 'Delta Persei', raDeg: 55.731, decDeg: 47.788, magnitude: 3.01, spectral: 'B', lightYears: 520 },
  { name: 'Miram', raDeg: 42.674, decDeg: 55.896, magnitude: 3.76, spectral: 'K', lightYears: 1000 },
  { name: 'Misam', raDeg: 47.374, decDeg: 44.858, magnitude: 3.80, spectral: 'K', lightYears: 112 },
  // Andromeda: the chain from Alpheratz out to Almach. M31 lies just above Mirach.
  { name: 'Alpheratz', raDeg: 2.097, decDeg: 29.091, magnitude: 2.06, spectral: 'B', lightYears: 97 },
  { name: 'Mirach', raDeg: 17.433, decDeg: 35.621, magnitude: 2.05, spectral: 'M', lightYears: 197 },
  { name: 'Almach', raDeg: 30.975, decDeg: 42.330, magnitude: 2.26, spectral: 'K', lightYears: 350 },
  { name: 'Delta Andromedae', raDeg: 9.832, decDeg: 30.861, magnitude: 3.28, spectral: 'K', lightYears: 105 },
  { name: 'Nembus', raDeg: 24.498, decDeg: 48.628, magnitude: 3.57, spectral: 'K', lightYears: 169 },
  { name: 'Mu Andromedae', raDeg: 14.188, decDeg: 38.499, magnitude: 3.87, spectral: 'A', lightYears: 130 },
  // Pegasus: the Great Square (with Alpheratz) and the neck out to Enif.
  { name: 'Scheat', raDeg: 345.944, decDeg: 28.083, magnitude: 2.42, spectral: 'M', lightYears: 196 },
  { name: 'Markab', raDeg: 346.190, decDeg: 15.205, magnitude: 2.49, spectral: 'B', lightYears: 133 },
  { name: 'Algenib', raDeg: 3.309, decDeg: 15.184, magnitude: 2.83, spectral: 'B', lightYears: 390 },
  { name: 'Enif', raDeg: 326.047, decDeg: 9.875, magnitude: 2.39, spectral: 'K', lightYears: 690 },
  { name: 'Matar', raDeg: 340.750, decDeg: 30.221, magnitude: 2.94, spectral: 'G', lightYears: 215 },
  { name: 'Homam', raDeg: 340.365, decDeg: 10.831, magnitude: 3.40, spectral: 'B', lightYears: 209 },
  { name: 'Sadalbari', raDeg: 342.501, decDeg: 24.602, magnitude: 3.51, spectral: 'G', lightYears: 106 },
  { name: 'Biham', raDeg: 332.550, decDeg: 6.198, magnitude: 3.53, spectral: 'A', lightYears: 92 },
  // Pavo, deep south.
  { name: 'Peacock', raDeg: 306.412, decDeg: -56.735, magnitude: 1.94, spectral: 'B', lightYears: 179 },
  { name: 'Beta Pavonis', raDeg: 311.240, decDeg: -66.203, magnitude: 3.42, spectral: 'A', lightYears: 135 },
  { name: 'Delta Pavonis', raDeg: 302.182, decDeg: -66.182, magnitude: 3.56, spectral: 'G', lightYears: 20 },
  // Eridanus: the river, winding from Cursa beside Rigel all the way down to Achernar (above).
  { name: 'Cursa', raDeg: 76.962, decDeg: -5.086, magnitude: 2.79, spectral: 'A', lightYears: 89 },
  { name: 'Acamar', raDeg: 44.565, decDeg: -40.305, magnitude: 2.88, spectral: 'A', lightYears: 165 },
  { name: 'Zaurak', raDeg: 59.507, decDeg: -13.509, magnitude: 2.95, spectral: 'M', lightYears: 203 },
  { name: 'Rana', raDeg: 55.812, decDeg: -9.765, magnitude: 3.54, spectral: 'K', lightYears: 29 },
  { name: 'Phi Eridani', raDeg: 34.127, decDeg: -51.512, magnitude: 3.56, spectral: 'B', lightYears: 155 },
  { name: 'Upsilon4 Eridani', raDeg: 64.473, decDeg: -33.798, magnitude: 3.56, spectral: 'B', lightYears: 178 },
  { name: 'Chi Eridani', raDeg: 28.990, decDeg: -51.609, magnitude: 3.69, spectral: 'G', lightYears: 57 },
  { name: 'Tau4 Eridani', raDeg: 49.879, decDeg: -21.758, magnitude: 3.69, spectral: 'M', lightYears: 300 },
  { name: 'Ran', raDeg: 53.233, decDeg: -9.458, magnitude: 3.73, spectral: 'K', lightYears: 10.5 },
  { name: 'Theemin', raDeg: 68.888, decDeg: -30.562, magnitude: 3.82, spectral: 'G', lightYears: 209 },
  { name: 'Sceptrum', raDeg: 69.545, decDeg: -14.304, magnitude: 3.87, spectral: 'K', lightYears: 110 },
  { name: 'Azha', raDeg: 44.107, decDeg: -8.898, magnitude: 3.89, spectral: 'K', lightYears: 137 },
  { name: 'Nu Eridani', raDeg: 69.080, decDeg: -3.353, magnitude: 3.93, spectral: 'B', lightYears: 590 },
  { name: 'Beid', raDeg: 62.966, decDeg: -6.838, magnitude: 4.04, spectral: 'F', lightYears: 122 },
  { name: 'Iota Eridani', raDeg: 40.167, decDeg: -39.856, magnitude: 4.11, spectral: 'K', lightYears: 145 },
  { name: 'Kappa Eridani', raDeg: 36.746, decDeg: -47.704, magnitude: 4.24, spectral: 'B', lightYears: 530 },
  { name: 'Lambda Eridani', raDeg: 77.287, decDeg: -8.754, magnitude: 4.27, spectral: 'B', lightYears: 1000 },
  { name: 'Keid', raDeg: 63.818, decDeg: -7.653, magnitude: 4.43, spectral: 'K', lightYears: 16.3 },
];

/** Apollo landing sites, for the hidden `apollo` command. Selenographic lat/lon (east positive). */
export const APOLLO_SITES = [
  { mission: 'Apollo 11', year: 1969, site: 'Tranquility Base', lat: 0.674, lon: 23.473 },
  { mission: 'Apollo 12', year: 1969, site: 'Ocean of Storms', lat: -3.012, lon: -23.421 },
  { mission: 'Apollo 14', year: 1971, site: 'Fra Mauro', lat: -3.646, lon: -17.471 },
  { mission: 'Apollo 15', year: 1971, site: 'Hadley Rille', lat: 26.132, lon: 3.634 },
  { mission: 'Apollo 16', year: 1972, site: 'Descartes Highlands', lat: -8.973, lon: 15.501 },
  { mission: 'Apollo 17', year: 1972, site: 'Taurus-Littrow', lat: 20.191, lon: 30.772 },
];

/** Every star name, for the terminal's `fly` command (which turns toward stars). */
export const STAR_NAMES: string[] = STARS.map((s) => s.name);

// Approximate blackbody colors by spectral class.
export const SPECTRAL_COLORS: Record<StarSpec['spectral'], number> = {
  O: 0x9bb0ff, B: 0xaabfff, A: 0xcad7ff, F: 0xf8f7ff, G: 0xfff4ea, K: 0xffd2a1, M: 0xffcc6f,
};

