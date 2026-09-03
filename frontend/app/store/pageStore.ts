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
}

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
  starsVisible: false,
  setStarsVisible: (visible) => set({ starsVisible: visible }),
  orbitsHighlighted: false,
  setOrbitsHighlighted: (on) => set({ orbitsHighlighted: on }),
  scaleMode: "compact",
  setScaleMode: (mode) => set({ scaleMode: mode }),
  secondsPerDay: 10,
  setSecondsPerDay: (seconds) => set({ secondsPerDay: seconds }),
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
