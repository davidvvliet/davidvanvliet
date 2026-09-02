import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";
import { BODY_NAMES } from "../../components/solarSystemData";

const findBody = (input: string) => BODY_NAMES.find((n) => n.toLowerCase() === input.toLowerCase());

const fly: Command = {
  name: "fly",
  description: "Fly to a planet or moon",
  hidden: true,
  execute: (args) => {
    if (!args[0]) {
      return ["__DIM__Usage: fly <body>", "", "Bodies:", `  ${BODY_NAMES.join("  ")}`];
    }
    const body = findBody(args[0]);
    if (!body) return [`Unknown body: ${args[0]}. Type "fly" to see the list.`];
    const store = usePageStore.getState();
    store.setLeftPanel("");
    store.requestFocus(body);
    return [`Flying to ${body}...`];
  },
  complete: (args) => (args.length <= 1 ? BODY_NAMES : []),
};

register(fly);

// Bare body names work too: "mars" is the same as "fly mars".
for (const name of BODY_NAMES) {
  register({
    name: name.toLowerCase(),
    description: `Fly to ${name}`,
    hidden: true,
    execute: () => fly.execute([name]),
  });
}
