import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PageState {
  /** Current route, mirrored from the URL by the site shell ("/" is explore). */
  view: string;
  setView: (path: string) => void;
  /** Route a terminal command asked for; the site shell navigates. `seq` increments so repeats fire. */
  navRequest: { path: string; seq: number } | null;
  openPath: (path: string) => void;
  /** How many photos public/photos holds (set by the site shell; for the `photos` command). */
  photoCount: number;
  setPhotoCount: (count: number) => void;
  /** Body the solar system should fly to. `seq` increments so repeat requests fire. */
  focusRequest: { name: string; seq: number } | null;
  requestFocus: (name: string) => void;
  /** Simulated Julian date, published by the scene a few times a second. */
  simJD: number;
  setSimJD: (jd: number) => void;
  /** Trace a mission's trajectory (id from MISSIONS), or null to clear. */
  trackRequest: { id: string | null; seq: number } | null;
  requestTrack: (id: string | null) => void;
  /** The clock rate in force before the first `launch`, restored by `launch off`. Null when no mission is running. */
  clockRateBeforeMission: number | null;
  setClockRateBeforeMission: (rate: number | null) => void;
  /** Request to jump the clock to a Julian date. */
  dateRequest: { jd: number; seq: number } | null;
  requestDate: (jd: number) => void;
  apolloVisible: boolean; // Apollo landing-site dots on the Moon (hidden `apollo` command)
  setApolloVisible: (visible: boolean) => void;
  starsVisible: boolean;
  setStarsVisible: (visible: boolean) => void;
  orbitsHighlighted: boolean; // orbit rings drawn bright white instead of faint gray
  setOrbitsHighlighted: (on: boolean) => void;
  scaleMode: "true" | "compact"; // true: exact ratios; compact: distances squeezed toward parents
  setScaleMode: (mode: "true" | "compact") => void;
  secondsPerDay: number; // real seconds per simulated Earth day; every motion scales with it
  setSecondsPerDay: (seconds: number) => void;
  /** Steps ahead in the puzzle sequence for this browser only (hidden `puzzle` command). Survives `reset`. */
  puzzleOffset: number;
  nextPuzzle: () => void;
  /** Restore every persisted setting to its default. */
  resetSettings: () => void;
  /** Lines pushed to the terminal from elsewhere (e.g. the scene). `seq` increments per push. */
  terminalPush: { lines: string[]; seq: number } | null;
  pushTerminalLines: (lines: string[]) => void;
  /** True while a mission transcript is playing in real time: the terminal hides its prompt. */
  transcriptPlaying: boolean;
  setTranscriptPlaying: (on: boolean) => void;
}

/** Defaults for the settings that persist to local storage. */
export const DEFAULT_SETTINGS = {
  starsVisible: true,
  orbitsHighlighted: true,
  scaleMode: "compact" as const,
  secondsPerDay: 10,
};

export const usePageStore = create<PageState>()(
  persist(
    (set) => ({
  view: "/",
  setView: (path) => set({ view: path }),
  navRequest: null,
  photoCount: 0,
  setPhotoCount: (count) => set({ photoCount: count }),
  openPath: (path) => set((state) => ({ navRequest: { path, seq: (state.navRequest?.seq ?? 0) + 1 } })),
  focusRequest: null,
  requestFocus: (name) =>
    set((state) => ({ focusRequest: { name, seq: (state.focusRequest?.seq ?? 0) + 1 } })),
  ...DEFAULT_SETTINGS,
  setStarsVisible: (visible) => set({ starsVisible: visible }),
  setOrbitsHighlighted: (on) => set({ orbitsHighlighted: on }),
  setScaleMode: (mode) => set({ scaleMode: mode }),
  setSecondsPerDay: (seconds) => set({ secondsPerDay: seconds }),
  puzzleOffset: 0,
  nextPuzzle: () => set((state) => ({ puzzleOffset: state.puzzleOffset + 1 })),
  resetSettings: () => set({ ...DEFAULT_SETTINGS }),
  simJD: 0,
  setSimJD: (jd) => set({ simJD: jd }),
  clockRateBeforeMission: null,
  setClockRateBeforeMission: (rate) => set({ clockRateBeforeMission: rate }),
  trackRequest: null,
  requestTrack: (id) => set((state) => ({ trackRequest: { id, seq: (state.trackRequest?.seq ?? 0) + 1 } })),
  dateRequest: null,
  requestDate: (jd) => set((state) => ({ dateRequest: { jd, seq: (state.dateRequest?.seq ?? 0) + 1 } })),
  apolloVisible: false,
  setApolloVisible: (visible) => set({ apolloVisible: visible }),
  transcriptPlaying: false,
  setTranscriptPlaying: (on) => set({ transcriptPlaying: on }),
  terminalPush: null,
  pushTerminalLines: (lines) =>
    set((state) => ({ terminalPush: { lines, seq: (state.terminalPush?.seq ?? 0) + 1 } })),
    }),
    {
      name: "explore-settings",
      // Only preferences persist. The view lives in the URL; focus requests and the clock rate are per-visit.
      partialize: (s) => ({
        starsVisible: s.starsVisible,
        orbitsHighlighted: s.orbitsHighlighted,
        scaleMode: s.scaleMode,
        puzzleOffset: s.puzzleOffset,
      }),
    }
  )
);
