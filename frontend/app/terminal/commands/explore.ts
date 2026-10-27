import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const explore: Command = {
  name: "explore",
  category: "explore",
  aliases: ["e"],
  description: "Go back to exploring",
  execute: () => {
    const store = usePageStore.getState();
    if (store.view === "/") {
      return ["You're already on the explore page. Try to zoom out."];
    }
    store.openPath("/");
    return ["Enjoy your voyage!"];
  },
};

register(explore);
