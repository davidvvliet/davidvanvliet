import { MissionSpec } from './types';

export const voyager2: MissionSpec = {
  id: 'voyager2', name: 'Voyager 2', file: '/missions/voyager2.json', center: 'Sun',
  view: { distanceAU: 8, elevationDeg: 28 }, secondsPerDay: 0.02,
  // Closest approaches, verified against Horizons at 5-minute steps.
  cues: [
    { jd: 2444064.4375, lines: ['Closest approach to Jupiter, 9 July 1979.'] },
    { jd: 2444842.6424, lines: ['Closest approach to Saturn, 26 August 1981.'] },
    { jd: 2446455.25, lines: ['Closest approach to Uranus, 24 January 1986.'] },
    { jd: 2447763.6632, lines: ['Closest approach to Neptune, 25 August 1989.'] },
  ],
};
