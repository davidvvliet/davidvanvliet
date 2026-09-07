import { MissionSpec } from './types';

export const perseverance: MissionSpec = {
  id: 'perseverance', name: 'Perseverance', file: '/missions/perseverance.json', center: 'Sun',
  view: { distanceAU: 2, elevationDeg: 28 }, secondsPerDay: 0.1,
  // Touchdown 2021-02-18 20:50 UTC (the trail's last sample on the surface); the clip is 0:13-3:11 of NASA's landing video.
  cues: [{ jd: 2459264.3681, lines: ['Arrival at Mars.', '__VIDEO__/perseverance-landing.webm', '__DIM__Perseverance descending to Jezero Crater, 18 February 2021, at 3x speed. Video: NASA/JPL-Caltech.'] }],
};
