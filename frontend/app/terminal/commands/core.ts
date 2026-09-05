import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

// Hidden: turn the view toward the galactic centre (Sagittarius A*).
const core: Command = {
  name: "core",
  description: "Galactic core",
  hidden: true,
  execute: () => {
    const store = usePageStore.getState();
    store.setLeftPanel("");
    store.setStarsVisible(true); // Sagittarius should frame it
    store.requestFocus("Galactic core");
    return ["This is the direction of the galactic core"];
  },
};

register(core);
