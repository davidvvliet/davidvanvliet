import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const reset: Command = {
  name: "reset",
  category: "explore",
  description: "Reset all settings",
  execute: (args) => {
    if (args[0]?.toLowerCase() === "all") {
      // Back to a first visit: drop everything the site stores, then reload so the
      // scene, camera, clock, mission, terminal and puzzle all start fresh. The keys
      // are removed in the same task as the reload, after this line has been saved,
      // so nothing can write them back in between.
      setTimeout(() => {
        try {
          for (const key of ["explore-settings", "explore-view", "terminal-history"]) localStorage.removeItem(key);
        } catch { /* storage unavailable */ }
        location.reload();
      }, 300);
      return ["Resetting everything..."];
    }
    usePageStore.getState().resetSettings();
    try { localStorage.removeItem('explore-view'); } catch { /* storage unavailable */ }
    return ["Settings reset: compact scale, stars on, orbit paths shown, 10s per day. The saved view is cleared on next load."];
  },
};

register(reset);
