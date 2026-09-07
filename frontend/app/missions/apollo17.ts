import { MissionSpec } from './types';

// Lunar orbit from the metric-camera state vectors (Apollo Image Archive, ASU); the translunar
// legs are integrated between the injection and entry conditions in mission report JSC-07904.
export const apollo17: MissionSpec = {
  id: 'apollo17', name: 'Apollo 17', file: '/missions/apollo17.json', center: 'Earth',
  view: { distanceAU: 0.006, elevationDeg: 28 }, secondsPerDay: 10, dateFormat: 'day',
  cues: [
    { jd: 0, lines: ['__IMG__/apollo17-crew.jpg', '__DIM__The Apollo 17 crew: Gene Cernan, Harrison Schmitt and Ron Evans. Photo: NASA.'] },
    // AS17-134-20384: Cernan's portrait of Schmitt with the flag and Earth, 118:25:54 GET (ALSJ), 1972-12-12 03:58:54 UTC.
    { jd: 2441663.6659, lines: ['__IMG__/apollo17-flag.jpg', "__DIM__Gene Cernan takes my phone's homescreen photo here. Photo: NASA."] },
  ],
  // Lunar orbit (insertion to transearth injection, mission report JSC-07904) close on the Moon at the set rate.
  events: [
    { fromJD: 2441662.32457, toJD: 2441668.48274, view: { target: 'Moon', distanceKm: 7000, elevationDeg: 25 } },
  ],
};
