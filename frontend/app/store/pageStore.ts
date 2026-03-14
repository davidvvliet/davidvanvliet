import { create } from "zustand";

interface PageState {
  leftPanel: string;
  setLeftPanel: (view: string) => void;
  blogPost: string;
  setBlogPost: (slug: string) => void;
}

export const usePageStore = create<PageState>((set) => ({
  leftPanel: "",
  setLeftPanel: (view) => set({ leftPanel: view }),
  blogPost: "",
  setBlogPost: (slug) => set({ blogPost: slug }),
}));
