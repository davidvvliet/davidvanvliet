import { MissionSpec } from './types';

// A proposal, not a flight: the 2028 mission (the later design, without a solar Oberth manoeuvre) of Hibberd, Hein, Eubanks & Kennedy (2022), Table 2, with the legs
// solved between Horizons positions on the paper's dates (see scripts/lyra). 'Oumuamua's own path is drawn in full.
export const lyra2: MissionSpec = {
  id: 'lyra2', name: 'Project Lyra 2', file: '/missions/lyra2.json', center: 'Sun',
  view: { distanceAU: 8, elevationDeg: 28 }, secondsPerDay: 0.02,
  note: "A proposal, not a flight: a 2028 launch to 1I/'Oumuamua, the first known interstellar object, with Venus, Earth and Earth flybys, a deep space manoeuvre and a powered Jupiter flyby, arriving in 2054 at 209 AU. Reconstructed from the 2022 Project Lyra paper; 'Oumuamua's path from JPL Horizons.",
};
