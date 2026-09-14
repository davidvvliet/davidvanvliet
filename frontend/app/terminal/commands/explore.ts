import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const explore: Command = {
  name: "explore",
  category: "explore",
  aliases: ["e"],
  description: "Go back to exploring",
  execute: () => {
    const credits = [
      "",
      "__SMALL__Credits:",
      "__SMALL__JPL Horizons, spacecraft and planet ephemerides: https://ssd.jpl.nasa.gov/horizons/",
      "__SMALL__VSOP87 (Bretagnon & Francou), the position of Mars",
      "__SMALL__NASA, JPL and USGS, mission and surface imagery; NASA/JPL-Caltech, Perseverance landing video; NASA, Apollo 11 landing loop",
      "__SMALL__Apollo Image Archive (ASU), Apollo 17 orbit state vectors: https://apollo.sese.asu.edu/",
      "__SMALL__NASA mission reports MSC-00171, MSC-02680 and JSC-07904, Apollo 11, 13 and 17 burn and entry conditions",
      "__SMALL__Apollo Flight Journal and Apollo Lunar Surface Journal, transcripts: https://www.apollojournals.org/",
      "__SMALL__John D. Anderson (JPL), Mariner 2 trajectory reconstruction, via Horizons",
      "__SMALL__JPL Technical Report 32-740, Mariner 4 injection and encounter conditions",
      "__SMALL__Hibberd, Hein and Eubanks (2020) and Hibberd, Hein, Eubanks and Kennedy (2022), Project Lyra mission designs: https://arxiv.org/abs/1902.04935 and https://arxiv.org/abs/2201.04240",
      "__SMALL__Solar System Scope, planet and ring textures: https://www.solarsystemscope.com/textures/",
      "__SMALL__Björn Jónsson, planetary maps: https://bjj.mmedia.is/data/planetary_maps.html",
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
