import { MissionSpec } from './types';

// No ephemeris exists: integrated burn to burn between the states tabulated in mission report MSC-02680.
export const apollo13: MissionSpec = {
  id: 'apollo13', name: 'Apollo 13', file: '/missions/apollo13.json', center: 'Earth',
  view: { distanceAU: 0.006, elevationDeg: 28 }, secondsPerDay: 10, dateFormat: 'day',
  // Crew portrait at launch, then the oxygen tank rupture (mission report, 55:54:53 GET) and the
  // air-to-ground calls that followed, verbatim from the Apollo Flight Journal transcript.
  cues: [
    { jd: 0, lines: ['__IMG__/apollo13-crew.jpg', '__DIM__The Apollo 13 crew: Fred Haise, Jim Lovell and Ken Mattingly. Mattingly was replaced by Jack Swigert three days before launch after being exposed to measles. Photo: NASA.'] },
    { jd: 2440690.63047, lines: ['__DIM__**Oxygen tank 2 ruptures**'] },
    { jd: 2440690.63078, lines: ["__TIMED__Swigert: Okay, Houston, we've had a problem here.__TIMED__055:55:19"] },
    { jd: 2440690.63088, lines: ['__TIMED__Lousma [CAPCOM]: This is Houston. Say again, please.__TIMED__055:55:28'] },
    { jd: 2440690.63096, lines: ["__TIMED__Lovell: Ah, Houston, we've had a problem. We've had a Main B Bus Undervolt.__TIMED__055:55:35"] },
    { jd: 2440690.63104, lines: ['__TIMED__Lousma [CAPCOM]: Roger. Main B Undervolt.__TIMED__055:55:42', '\u00a0'] },
  ],
  // The clock runs at twice true speed from Swigert's call to Lousma's acknowledgement, so the calls land with their real gaps, halved.
  events: [{ fromJD: 2440690.63078, toJD: 2440690.63104, speed: 2, view: { target: 'craft', distanceKm: 20000, elevationDeg: 20 } }],
};
