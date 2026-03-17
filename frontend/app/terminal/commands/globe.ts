import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const globe: Command = {
  name: "globe",
  aliases: ["g"],
  description: "Open globe",
  execute: () => {
    usePageStore.getState().setLeftPanel("");
    return [];
  },
};

register(globe);
