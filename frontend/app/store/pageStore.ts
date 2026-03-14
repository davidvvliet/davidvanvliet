import { create } from "zustand";

interface PageState {
  leftPanel: string;
  setLeftPanel: (view: string) => void;
}

export const usePageStore = create<PageState>((set) => ({
  leftPanel: "",
  setLeftPanel: (view) => set({ leftPanel: view }),
}));
