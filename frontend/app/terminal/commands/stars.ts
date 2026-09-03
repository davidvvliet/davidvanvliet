import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const stars: Command = {
  name: "stars",
  description: "Light the sky",
  execute: (args) => {
    const store = usePageStore.getState();
    const arg = args[0]?.toLowerCase();
    const next = arg === "on" ? true : arg === "off" ? false : !store.starsVisible;
    store.setStarsVisible(next);
    return [next ? "Stars on." : "Stars off."];
  },
  complete: (args) => (args.length <= 1 ? ["on", "off"] : []),
};

register(stars);
