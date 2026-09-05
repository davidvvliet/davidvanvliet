import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const reset: Command = {
  name: "reset",
  category: "explore",
  description: "Reset all settings",
  execute: () => {
    usePageStore.getState().resetSettings();
    try { localStorage.removeItem('explore-view'); } catch { /* storage unavailable */ }
    return ["Settings reset: compact scale, stars off, orbit paths hidden, 10s per day. The saved view is cleared on next load."];
  },
};

register(reset);
