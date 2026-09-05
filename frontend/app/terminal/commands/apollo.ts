import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

// Hidden: fly to the Moon and mark the six Apollo landing sites.
const apollo: Command = {
  name: "apollo",
  description: "Apollo landing sites",
  hidden: true,
  execute: () => {
    const store = usePageStore.getState();
    store.setLeftPanel("");
    store.setApolloVisible(true);
    store.requestFocus("Moon");
    return ["Flying to the Moon, just like those brave gentlemen."];
  },
};

register(apollo);
