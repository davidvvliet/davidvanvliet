import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const reset: Command = {
  name: "reset",
  category: "explore",
  description: "Reset all settings",
  execute: () => {
    usePageStore.getState().resetSettings();
    return ["Settings reset: compact scale, stars off, orbit paths hidden, 10s per day."];
  },
};

register(reset);
