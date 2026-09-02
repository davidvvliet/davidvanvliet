import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const explore: Command = {
  name: "explore",
  aliases: ["e"],
  description: "Explore the solar system",
  execute: () => {
    const credits = [
      "",
      "__DIM__Credits:",
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
