import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

// Lichess puzzle filters.
const OPTIONS: Record<string, string> = {
  random: "",
  mate: "?angle=mate",
  easier: "?difficulty=easier",
  harder: "?difficulty=harder",
};

const puzzle: Command = {
  name: "puzzle",
  description: "New chess puzzle (random, mate, easier, harder)",
  execute: (args) => {
    const key = (args[0] ?? "random").toLowerCase();
    if (!(key in OPTIONS)) {
      return [`Unknown option: ${args[0]}. Use ${Object.keys(OPTIONS).join(", ")}.`];
    }
    usePageStore.getState().requestPuzzle(OPTIONS[key]);
    return [key === "random" ? "Loading a puzzle..." : `Loading a ${key} puzzle...`];
  },
  complete: (args) => (args.length <= 1 ? Object.keys(OPTIONS) : []),
};

register(puzzle);
