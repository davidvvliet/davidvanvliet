import { MissionSpec } from './types';

export const mariner2: MissionSpec = {
  id: 'mariner2', name: 'Mariner 2', file: '/missions/mariner2.json', center: 'Sun',
  view: { distanceAU: 2, elevationDeg: 28 }, secondsPerDay: 0.1,
  note: 'This is the first interplanetary mission ever. At the time we barely knew what the inner planets were like. Imagine the excitement of what would be found.',
};
