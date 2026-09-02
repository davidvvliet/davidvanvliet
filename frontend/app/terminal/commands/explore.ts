import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const explore: Command = {
  name: "explore",
  aliases: ["e"],
  description: "Explore the solar system",
  execute: () => {
    usePageStore.getState().setLeftPanel("");
    return [];
  },
};

register(explore);
