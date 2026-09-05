import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

// Hidden: skip to the next puzzle in the sequence, for this browser only.
const puzzle: Command = {
  name: "puzzle",
  description: "New chess puzzle",
  hidden: true,
  execute: () => {
    usePageStore.getState().nextPuzzle();
    return ["New puzzle."];
  },
};

register(puzzle);
