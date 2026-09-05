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
      "__DIM__JPL Horizons, spacecraft and planet ephemerides: https://ssd.jpl.nasa.gov/horizons/",
      "__DIM__NASA, JPL and USGS, mission and surface imagery",
      "__DIM__Apollo Image Archive (ASU), Apollo 17 orbit state vectors: https://apollo.sese.asu.edu/",
      "__DIM__NASA mission reports MSC-02680 and JSC-07904, Apollo 13 and 17 burn and entry conditions",
      "__DIM__John D. Anderson (JPL), Mariner 2 trajectory reconstruction, via Horizons",
      "__DIM__JPL Technical Report 32-740, Mariner 4 injection and encounter conditions",
      "__DIM__Solar System Scope, planet and ring textures: https://www.solarsystemscope.com/textures/",
      "__DIM__Björn Jónsson, planetary maps: https://bjj.mmedia.is/data/planetary_maps.html",
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
