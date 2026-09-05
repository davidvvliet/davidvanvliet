import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const TRUE_MSG = [
  "This is a true-scale version of the actual solar system.",
  "Every distance and Sun/planet/moon size* is exact and is based on a chosen unit size of the Earth.",
  "__DIM__*Although zooming out enough will change the size ratios due to a minimum on-screen size for each body.",
];
const COMPACT_MSG = ["A more compact version of the solar system."];

const scale: Command = {
  name: "scale",
  description: "True or compact solar system",
  execute: (args) => {
    const store = usePageStore.getState();
    const arg = args[0]?.toLowerCase();
    if (!arg) {
      return ["__DIM__Usage: scale true | compact", `Currently: ${store.scaleMode}`];
    }
    if (arg !== "true" && arg !== "compact") {
      return [`Unknown scale: ${arg}. Use "true" or "compact".`];
    }
    store.setScaleMode(arg);
    return arg === "true" ? TRUE_MSG : COMPACT_MSG;
  },
  complete: (args) => (args.length <= 1 ? ["true", "compact"] : []),
};

register(scale);
