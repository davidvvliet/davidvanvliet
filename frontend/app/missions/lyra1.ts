import { MissionSpec } from './types';

// A proposal, not a flight: scenario A of Hibberd, Hein & Eubanks (2020), Earth to Jupiter to a solar Oberth manoeuvre at
// six solar radii, reconstructed by shooting between Horizons positions on the paper's dates (see scripts/lyra).
export const lyra1: MissionSpec = {
  id: 'lyra1', name: 'Project Lyra 1', file: '/missions/lyra1.json', center: 'Sun',
  view: { distanceAU: 8, elevationDeg: 28 }, secondsPerDay: 0.02,
  note: "This is a proposed mission that will likely never fly. It is supposed to launch in 2033 in order to chase 'Oumuamua, the interstellar comet that passed through the solar system in 2017. By using a sequence of amazing gravity assists, it would gain a much faster speed than 'Oumuamua, and would catch up with it in 2052.",
};
