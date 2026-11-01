import { Command } from "../types";
import { run } from "../run";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const footprint: Command = {
  name: "footprint",
  category: "explore",
  description: "Show how far our farthest craft have gone",
  execute: (args) => {
    const store = usePageStore.getState();
    if (args[0]?.toLowerCase() === "off") {
      store.setFootprintShown(false);
      return ["Footprint cleared."];
    }
    store.openPath("/");
    store.endMission(); // one picture at a time
    if (store.scaleMode !== "true") store.setScaleMode("true"); // the paths are only true at true scale
    store.setFootprintShown(true);
    return [
      "__GRAY__The five craft leaving the solar system, each path from launch to where it is now:",
      "__COL__Voyager 1, 2__COL__blue",
      "__COL__Pioneer 10, 11__COL__yellow",
      "__COL__New Horizons__COL__red",
      `__DIM__${run("footprint off", "off")}`,
    ];
  },
  complete: (args) => (args.length <= 1 ? ["off"] : []),
};

register(footprint);
