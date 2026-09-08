import { MissionSpec } from './types';

export const perseverance: MissionSpec = {
  id: 'perseverance', name: 'Perseverance', file: '/missions/perseverance.json', center: 'Sun',
  view: { distanceAU: 2, elevationDeg: 28 }, secondsPerDay: 0.1,
  // Touchdown 2021-02-18 20:50 UTC (the trail's last sample on the surface); the clip is 0:13-3:11 of NASA's landing video.
  cues: [{ jd: 2459264.3673, lines: ['Arrival at Mars.', '__VIDEO__/perseverance-landing.webm', '__DIM__Perseverance descending to Jezero Crater, 18 February 2021, at 3x speed. Video: NASA/JPL-Caltech.'] }],
  // At touchdown, as the video starts: close on Mars over Jezero (the green dot) and stay. The clock is frozen there anyway.
  events: [{ fromJD: 2459264.3673, toJD: 2459264.3773, view: { target: 'Mars', distanceKm: 12000, elevationDeg: 10, siteLat: 18.4447, siteLon: 77.4508, stay: true } }],
};
