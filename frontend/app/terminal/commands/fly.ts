import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";
import { BODY_NAMES, STAR_NAMES, MISSIONS } from "../../components/solarSystemData";

const findName = (list: string[], input: string) => list.find((n) => n.toLowerCase() === input.toLowerCase());

const fly: Command = {
  name: "fly",
  category: "explore",
  description: "Fly to a planet or moon, or turn toward a star",
  execute: (args) => {
    if (!args[0]) {
      return ["__DIM__Usage: fly <body | star>", "Type a planet or moon and you'll fly there. Type a star and you'll turn toward it."];
    }
    const input = args.join(" "); // multi-word names: "fly alpha centauri"
    const store = usePageStore.getState();
    // Launched missions are focusable bodies too (their tip marker).
    const body = findName([...BODY_NAMES, ...MISSIONS.map((m) => m.name)], input);
    if (body) {
      store.setLeftPanel("");
      store.requestFocus(body);
      return [`Flying to ${body}...`];
    }
    const star = findName(STAR_NAMES, input);
    if (star) {
      store.setLeftPanel("");
      store.setStarsVisible(true); // can't aim at a hidden sky
      store.requestFocus(star);
      return [`Turning toward ${star}...`];
    }
    return [`Unknown body or star: ${input}.`];
  },
  complete: (args) => (args.length <= 1 ? [...BODY_NAMES, ...STAR_NAMES] : []),
};

register(fly);

// Bare names work too: "mars" is the same as "fly mars". Multi-word star names
// need the fly prefix, since the terminal splits on spaces.
for (const name of [...BODY_NAMES, ...STAR_NAMES]) {
  if (name.includes(" ")) continue;
  register({
    name: name.toLowerCase(),
    description: `Fly to ${name}`,
    hidden: true,
    execute: () => fly.execute([name]),
  });
}
