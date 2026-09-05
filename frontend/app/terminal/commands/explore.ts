import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const explore: Command = {
  name: "explore",
  category: "explore",
  aliases: ["e"],
  description: "Explore the solar system",
  execute: () => {
    const credits = [
      "",
      "__DIM__Credits:",
      "__DIM__Björn Jónsson, planetary maps: https://bjj.mmedia.is/data/planetary_maps.html",
      "__DIM__Solar System Scope, planet and ring textures: https://www.solarsystemscope.com/textures/",
      "__DIM__NASA, JPL and USGS, mission and surface imagery",
      "__DIM__JPL Horizons, spacecraft and planet ephemerides: https://ssd.jpl.nasa.gov/horizons/",
    ];
    const store = usePageStore.getState();
    if (store.leftPanel === "") {
      return ["You're already on the explore page. Try to zoom out.", ...credits];
    }
    store.setLeftPanel("");
    return ["Enjoy your voyage!", ...credits];
  },
};

register(explore);
