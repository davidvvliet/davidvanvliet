import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const puzzle: Command = {
  name: "puzzle",
  description: "Reset today's chess puzzle",
  execute: () => {
    usePageStore.getState().requestPuzzle("");
    return ["Resetting today's puzzle..."];
  },
};

register(puzzle);
