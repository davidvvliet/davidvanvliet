import { MissionSpec } from './types';

export const voyager1: MissionSpec = {
  id: 'voyager1', name: 'Voyager 1', file: '/missions/voyager1.json', center: 'Sun',
  view: { distanceAU: 8, elevationDeg: 28 }, secondsPerDay: 0.01,
  // The Pale Blue Dot: 1990-02-14 04:48 GMT (NASA Photojournal PIA00452/PIA23645), 6.05 billion km from Earth on this trail.
  cues: [
    // Closest approaches: Jupiter 1979-03-05 12:05 UTC, Saturn 1980-11-12 23:45 UTC (both verified against Horizons at 5-minute steps).
    { jd: 2443938.0035, lines: ['Closest approach to Jupiter, 5 March 1979.'] },
    { jd: 2444556.4896, lines: ["Closest approach to Saturn, 12 November 1980."] },
    { jd: 2447936.7, lines: ['__IMG__/voyager1-pale-blue-dot.jpg', "__DIM__Voyager 1 turns its camera back and takes one of the most famous images ever. When I was younger I had it as a massive glass print in my bedroom. Photo: NASA/JPL-Caltech."] },
  ],
};
