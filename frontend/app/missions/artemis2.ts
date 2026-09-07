import { MissionSpec } from './types';

// Earth-centred: the path is drawn in Earth's moving frame. 0.006 AU is ~2.3 Earth-Moon distances.
export const artemis2: MissionSpec = {
  id: 'artemis2', name: 'Artemis II', file: '/missions/artemis2.json', center: 'Earth',
  view: { distanceAU: 0.006, elevationDeg: 28 }, secondsPerDay: 10, dateFormat: 'day',
  // NASA image art002e012278 ("Sill Life"), taken 2026-04-06 22:10:17 UTC per its EXIF, 49 minutes before closest approach.
  cues: [{ jd: 2461137.4238, lines: ['__IMG__/artemis2-moon.jpg', '__DIM__Artemis II takes my laptop homescreen photo here. Photo: NASA.'] }],
};
