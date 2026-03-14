import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const globe: Command = {
  name: "globe",
  description: "Show the globe",
  execute: () => {
    usePageStore.getState().setLeftPanel("");
    return [];
  },
};

register(globe);
