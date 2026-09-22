import { MissionSpec } from './types';

// A proposal, not a flight: scenario B of Hibberd, Hein & Eubanks (2020), Earth, a deep space manoeuvre at 3.2 AU, an Earth
// flyby, Jupiter, then a solar Oberth manoeuvre at six solar radii (see scripts/lyra).
export const lyra1b: MissionSpec = {
  id: 'lyra1b', name: 'Project Lyra 1b', file: '/missions/lyra1b.json', center: 'Sun',
  view: { distanceAU: 8, elevationDeg: 28 }, secondsPerDay: 0.02,
  note: "This is a proposed mission that will likely never fly. The same 2020 study's cheaper option: launch in 2030, a burn out at 3.2 AU and a return past Earth to pick up speed for Jupiter, then the same dive to six solar radii, catching up with 'Oumuamua in 2052. Source: Hibberd, Hein and Eubanks (2020), Project Lyra: catching 1I/'Oumuamua, mission opportunities after 2024, Acta Astronautica 170, scenario B. https://arxiv.org/abs/1902.04935",
};
