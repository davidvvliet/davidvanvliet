/** A mission the terminal can `launch`: a trajectory file plus how to present it. */
export type MissionSpec = {
  id: string; name: string; file: string; center: 'Sun' | 'Earth';
  /** Camera on launch: Earth stays the focus; ease out to this distance (AU) at this elevation above the ecliptic. */
  view?: { distanceAU: number; elevationDeg: number };
  /** Clock rate set on launch, real seconds per Earth day. */
  secondsPerDay?: number;
  /** Date readout while launched: month and year (default) or the full day. */
  dateFormat?: 'month' | 'day';
  /** Where the path comes from, shown on launch when it is not a plain Horizons ephemeris. */
  note?: string;
  /** Timed cues: each set of lines is pushed to the terminal once, the first time the clock reaches its date while tracking. */
  cues?: { jd: number; lines: string[] }[];
  /** Events: between fromJD and toJD the clock runs at `speed` times true speed (or the set rate if absent), and the
   *  camera flies to `view` if given. The shortest event containing the date wins, so events can nest. */
  events?: MissionEvent[];
};

export type MissionEvent = {
  fromJD: number; toJD: number; speed?: number;
  view?: {
    target: string;        // a body name, or 'craft' for the mission marker
    distanceKm: number;    // camera distance from the target's centre
    elevationDeg?: number; // tilt above the ecliptic (or above the site's horizon plane when a site is given)
    siteLat?: number; siteLon?: number; // look down on this spot (bodies with a fixed map: the Moon)
    stay?: boolean;        // keep this view when the event ends instead of flying back to the mission view
  };
};
