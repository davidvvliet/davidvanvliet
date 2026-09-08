import { MissionSpec } from './types';

export const voyager2: MissionSpec = {
  id: 'voyager2', name: 'Voyager 2', file: '/missions/voyager2.json', center: 'Sun',
  view: { distanceAU: 8, elevationDeg: 28 }, secondsPerDay: 0.02,
  // Photos: NASA Photojournal PIA00459, NSSDC P-23953, PIA00347, PIA00143, PIA00058 (dates from their captions).
  // Closest approaches, verified against Horizons at 5-minute steps.
  cues: [
    { jd: 2444064.25, lines: ['__IMG__/voyager2-europa.jpg', "__DIM__Europa, 9 July 1979, from 246,000 km. Photo: NASA/JPL."] },
    { jd: 2444064.4375, lines: ['Closest approach to Jupiter, 9 July 1979.'] },
    { jd: 2444834.0, lines: ['__IMG__/voyager2-saturn-rings.jpg', "__DIM__Saturn's rings in false colour, 17 August 1981, from 8.9 million km. Photo: NASA/JPL."] },
    { jd: 2444842.0, lines: ['__IMG__/voyager2-enceladus.jpg', "__DIM__Enceladus, 25 August 1981, from 119,000 km. Photo: NASA/JPL."] },
    { jd: 2444842.6424, lines: ['Closest approach to Saturn, 26 August 1981.'] },
    { jd: 2446455.25, lines: ['Closest approach to Uranus, 24 January 1986.'] },
    { jd: 2446456.0, lines: ['__IMG__/voyager2-uranus-crescent.jpg', "__DIM__Leaving Uranus, 25 January 1986, from 1 million km. Photo: NASA/JPL."] },
    { jd: 2447763.5799, lines: ['__IMG__/voyager2-neptune-clouds.jpg', "__DIM__Neptune's cloud streaks casting shadows, two hours before closest approach on 25 August 1989. Photo: NASA/JPL."] },
    { jd: 2447763.6632, lines: ['Closest approach to Neptune, 25 August 1989.'] },
  ],
};
