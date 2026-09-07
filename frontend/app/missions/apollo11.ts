import { MissionSpec } from './types';

// No tracking data exists: legs integrated and shot between the states in mission report MSC-00171,
// the lunar orbit propagated between the tabulated CSM states.
export const apollo11: MissionSpec = {
  id: 'apollo11', name: 'Apollo 11', file: '/missions/apollo11.json', center: 'Earth',
  view: { distanceAU: 0.006, elevationDeg: 28 }, secondsPerDay: 10, dateFormat: 'day',
  // The descent: the flight director's loop from 102:37:03 GET (aligned on four transcript anchors,
  // "Contact light" at 8:36, where the clip now ends), with the landing calls verbatim from the Lunar Surface
  // Journal. The clip is locked to the clock (see events below).
  cues: [
    { jd: 0, lines: ['__IMG__/apollo11-crew.jpg', '__DIM__The Apollo 11 crew: Neil Armstrong, Michael Collins and Buzz Aldrin. Photo: NASA.'] },
    { jd: 2440423.33962, lines: ['Eagle begins its landing.', '__VIDEO__/apollo11-landing.webm@jd:2440423.33962', '__DIM__Powered descent to the Sea of Tranquility, at 10x speed. I cried the first time I watched this. Video: NASA.'] },
    { jd: 2440423.34579, lines: ['__TIMED__Duke [CAPCOM]: We copy you down, Eagle.__TIMED__102:45:57'] },
    { jd: 2440423.34581, lines: ['__TIMED__Armstrong: Houston, Tranquility Base here. The Eagle has landed.__TIMED__102:45:58'] },
    { jd: 2440423.3459, lines: ["__TIMED__Duke [CAPCOM]: Roger, Twan...Tranquility. We copy you on the ground. You got a bunch of guys about to turn blue. We're breathing again. Thanks a lot.__TIMED__102:46:06"] },
    { jd: 2440423.34602, lines: ['__TIMED__Aldrin: Thank you.__TIMED__102:46:16'] },
    { jd: 2440423.34604, lines: ["__TIMED__Duke [CAPCOM]: You're looking good here.__TIMED__102:46:18", '\u00a0'] },
    // The first step: the last 16 s of NASA's restored TV comparison, muted, at 2x with the line as text;
    // "That's one small step" is spoken at 109:24:23 (Lunar Surface Journal), 0.8 s into the clip.
    { jd: 2440423.62248, lines: ['Six and a half hours later.', '__VIDEO__/apollo11-step.webm@jd:2440423.62248', '__DIM__Armstrong makes history. Video: NASA.'] },
    { jd: 2440423.62249, lines: ["__TIMED__Armstrong: That's one small step for (a) man; one giant leap for mankind.__TIMED__109:24:23", '\u00a0'] },
  ],
  // Lunar orbit (insertion to transearth injection) close on the Moon at the set rate; inside it, the descent at 10x
  // over Tranquility Base until Contact Light (where the clip ends), the landing calls at 2x, and the first step at 2x.
  events: [
    { fromJD: 2440422.2235, toJD: 2440424.70535, view: { target: 'Moon', distanceKm: 7000, elevationDeg: 25 } },
    { fromJD: 2440423.33962, toJD: 2440423.3456, speed: 10, view: { target: 'Moon', distanceKm: 6000, elevationDeg: 20, siteLat: 0.674, siteLon: 23.473 } },
    { fromJD: 2440423.3456, toJD: 2440423.34604, speed: 2, view: { target: 'Moon', distanceKm: 6000, elevationDeg: 20, siteLat: 0.674, siteLon: 23.473 } },
    { fromJD: 2440423.62248, toJD: 2440423.62266, speed: 2, view: { target: 'Moon', distanceKm: 3000, elevationDeg: 20, siteLat: 0.674, siteLon: 23.473 } },
  ],
};
