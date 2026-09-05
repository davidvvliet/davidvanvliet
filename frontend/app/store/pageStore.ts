import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PageState {
  leftPanel: string;
  setLeftPanel: (view: string) => void;
  blogPost: string;
  setBlogPost: (slug: string) => void;
  /** Body the solar system should fly to. `seq` increments so repeat requests fire. */
  focusRequest: { name: string; seq: number } | null;
  requestFocus: (name: string) => void;
  starsVisible: boolean;
  setStarsVisible: (visible: boolean) => void;
  orbitsHighlighted: boolean; // orbit rings drawn bright white instead of faint gray
  setOrbitsHighlighted: (on: boolean) => void;
  scaleMode: "true" | "compact"; // true: exact ratios; compact: distances squeezed toward parents
  setScaleMode: (mode: "true" | "compact") => void;
  secondsPerDay: number; // real seconds per simulated Earth day; every motion scales with it
  setSecondsPerDay: (seconds: number) => void;
  /** Restore every persisted setting to its default. */
  resetSettings: () => void;
  /** Lines pushed to the terminal from elsewhere (e.g. the scene). `seq` increments per push. */
  terminalPush: { lines: string[]; seq: number } | null;
  pushTerminalLines: (lines: string[]) => void;
  /** Chess: load a new puzzle (query is the Lichess filter string, e.g. "?angle=mate"). */
  puzzleRequest: { query: string; seq: number } | null;
  requestPuzzle: (query: string) => void;
}

/** Defaults for the settings that persist to local storage. */
export const DEFAULT_SETTINGS = {
  starsVisible: false,
  orbitsHighlighted: false,
  scaleMode: "compact" as const,
  secondsPerDay: 10,
};

export const usePageStore = create<PageState>()(
  persist(
    (set) => ({
  leftPanel: "",
  setLeftPanel: (view) => set({ leftPanel: view }),
  blogPost: "",
  setBlogPost: (slug) => set({ blogPost: slug }),
  focusRequest: null,
  requestFocus: (name) =>
    set((state) => ({ focusRequest: { name, seq: (state.focusRequest?.seq ?? 0) + 1 } })),
  ...DEFAULT_SETTINGS,
  setStarsVisible: (visible) => set({ starsVisible: visible }),
  setOrbitsHighlighted: (on) => set({ orbitsHighlighted: on }),
  setScaleMode: (mode) => set({ scaleMode: mode }),
  setSecondsPerDay: (seconds) => set({ secondsPerDay: seconds }),
  resetSettings: () => set({ ...DEFAULT_SETTINGS }),
  terminalPush: null,
  pushTerminalLines: (lines) =>
    set((state) => ({ terminalPush: { lines, seq: (state.terminalPush?.seq ?? 0) + 1 } })),
  puzzleRequest: null,
  requestPuzzle: (query) =>
    set((state) => ({ puzzleRequest: { query, seq: (state.puzzleRequest?.seq ?? 0) + 1 } })),
    }),
    {
      name: "explore-settings",
      // Only preferences persist. Panel, blog post and focus requests are per-visit.
      partialize: (s) => ({
        starsVisible: s.starsVisible,
        orbitsHighlighted: s.orbitsHighlighted,
        scaleMode: s.scaleMode,
        secondsPerDay: s.secondsPerDay,
      }),
    }
  )
);
