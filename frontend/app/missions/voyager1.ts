import { MissionSpec } from './types';

export const voyager1: MissionSpec = {
  id: 'voyager1', name: 'Voyager 1', file: '/missions/voyager1.json', center: 'Sun',
  view: { distanceAU: 8, elevationDeg: 28 }, secondsPerDay: 0.01,
  // The Pale Blue Dot: 1990-02-14 04:48 GMT (NASA Photojournal PIA00452/PIA23645), 6.05 billion km from Earth on this trail.
  cues: [
    // Photos: NASA Photojournal PIA00014, PIA00010, PIA02238, PIA00335 (dates from their captions; times within the day are not published).
  // Closest approaches: Jupiter 1979-03-05 12:05 UTC, Saturn 1980-11-12 23:45 UTC (both verified against Horizons at 5-minute steps).
    { jd: 2443930.0, lines: ['__IMG__/voyager1-jupiter-grs.jpg', "__DIM__The Great Red Spot, 25 February 1979, from 9.2 million km. Photo: NASA/JPL."] },
    { jd: 2443937.75, lines: ['__IMG__/voyager1-io-plume.jpg', "__DIM__The first active volcano seen beyond Earth, on Io. 5 March 1979. Photo: NASA/JPL."] },
    { jd: 2443938.0035, lines: ['Closest approach to Jupiter, 5 March 1979.'] },
    { jd: 2444556.0, lines: ['__IMG__/voyager1-titan-haze.jpg', "__DIM__Titan's haze, 12 November 1980, from 435,000 km. Photo: NASA/JPL."] },
    { jd: 2444556.4896, lines: ["Closest approach to Saturn, 12 November 1980."] },
    { jd: 2444560.0, lines: ['__IMG__/voyager1-saturn-crescent.jpg', "__DIM__Looking back at Saturn, 16 November 1980, four days after closest approach. A view never possible from Earth. Photo: NASA/JPL."] },
    { jd: 2447936.7, lines: ['__IMG__/voyager1-pale-blue-dot.jpg', "__DIM__Voyager 1 turns its camera back and takes one of the most famous images ever. When I was younger I had it as a massive glass print in my bedroom. Photo: NASA/JPL-Caltech."] },
  ],
};
