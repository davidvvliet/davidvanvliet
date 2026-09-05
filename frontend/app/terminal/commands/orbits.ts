import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const orbits: Command = {
  name: "orbits",
  category: "explore",
  description: "Show orbit paths",
  execute: (args) => {
    const store = usePageStore.getState();
    const arg = args[0]?.toLowerCase();
    const next = arg === "on" ? true : arg === "off" ? false : !store.orbitsHighlighted;
    store.setOrbitsHighlighted(next);
    return [next ? "Orbit paths shown." : "Orbit paths hidden."];
  },
  complete: (args) => (args.length <= 1 ? ["on", "off"] : []),
};

register(orbits);
