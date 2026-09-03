import { create } from "zustand";

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
}

export const usePageStore = create<PageState>((set) => ({
  leftPanel: "",
  setLeftPanel: (view) => set({ leftPanel: view }),
  blogPost: "",
  setBlogPost: (slug) => set({ blogPost: slug }),
  focusRequest: null,
  requestFocus: (name) =>
    set((state) => ({ focusRequest: { name, seq: (state.focusRequest?.seq ?? 0) + 1 } })),
  starsVisible: true,
  setStarsVisible: (visible) => set({ starsVisible: visible }),
}));
