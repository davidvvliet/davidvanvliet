import { MissionSpec } from './types';
export type { MissionSpec };
export type { MissionEvent } from './types';
import { voyager1 } from './voyager1';
import { voyager2 } from './voyager2';
import { newhorizons } from './newhorizons';
import { pioneer10 } from './pioneer10';
import { pioneer11 } from './pioneer11';
import { dawn } from './dawn';
import { ulysses } from './ulysses';
import { cassini } from './cassini';
import { parker } from './parker';
import { mariner2 } from './mariner2';
import { perseverance } from './perseverance';
import { mariner4 } from './mariner4';
import { artemis2 } from './artemis2';
import { apollo11 } from './apollo11';
import { apollo13 } from './apollo13';
import { apollo17 } from './apollo17';

/** Every mission the terminal can `launch`, one file each. */
export const MISSIONS: MissionSpec[] = [
  voyager1,
  voyager2,
  newhorizons,
  pioneer10,
  pioneer11,
  dawn,
  ulysses,
  cassini,
  parker,
  mariner2,
  perseverance,
  mariner4,
  artemis2,
  apollo11,
  apollo13,
  apollo17,
];
