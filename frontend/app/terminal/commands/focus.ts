import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";
import { BODY_NAMES, STAR_NAMES, MISSIONS } from "../../components/solarSystemData";

const findName = (list: string[], input: string) => list.find((n) => n.toLowerCase() === input.toLowerCase());

const focus: Command = {
  name: "focus",
  category: "explore",
  description: "Focus on a planet or moon, or turn toward a star",
  execute: (args) => {
    if (!args[0]) {
      return ["__DIM__Usage: focus <body | star>", "Type a planet or moon and you'll fly there. Type a star and you'll turn toward it."];
    }
    const input = args.join(" "); // multi-word names: "focus alpha centauri"
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

register(focus);

// Bare names work too: "mars" is the same as "focus mars". Multi-word star names
// need the focus prefix, since the terminal splits on spaces.
for (const name of [...BODY_NAMES, ...STAR_NAMES]) {
  if (name.includes(" ")) continue;
  register({
    name: name.toLowerCase(),
    description: `Focus on ${name}`,
    hidden: true,
    execute: () => focus.execute([name]),
  });
}
