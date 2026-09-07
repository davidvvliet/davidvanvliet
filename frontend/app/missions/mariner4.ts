import { MissionSpec } from './types';

// No ephemeris exists: integrated from the injection state in JPL TR 32-740, the midcourse burn shot onto the report's encounter table.
export const mariner4: MissionSpec = {
  id: 'mariner4', name: 'Mariner 4', file: '/missions/mariner4.json', center: 'Sun',
  view: { distanceAU: 2, elevationDeg: 28 }, secondsPerDay: 0.1,
  note: 'Reconstructed from the injection state and encounter conditions in JPL Technical Report 32-740; no tracking data exists.',
};
