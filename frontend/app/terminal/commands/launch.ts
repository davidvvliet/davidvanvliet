import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";
import { MISSIONS } from "../../components/solarSystemData";

const launch: Command = {
  name: "launch",
  category: "explore",
  description: "Launch a mission and trace its path",
  execute: (args) => {
    const store = usePageStore.getState();
    const arg = args.join(" ").toLowerCase();
    if (!arg) {
      // One line per program; missions of the same program list their numbers in the second column.
      const crewed = (m: (typeof MISSIONS)[number]) => /^(apollo|artemis)/.test(m.id);
      const rows = (list: typeof MISSIONS) => {
        const programs = new Map<string, string[]>();
        for (const m of list) {
          const match = m.name.match(/^(.*?)\s+([0-9]+|[IVX]+)$/);
          const program = match ? match[1] : m.name;
          programs.set(program, [...(programs.get(program) ?? []), ...(match ? [match[2]] : [])]);
        }
        return [...programs].map(([program, numbers]) => `__COL__${program}__COL__${numbers.join("  ")}`);
      };
      return [
        "__DIM__Usage: launch <mission> | off",
        "",
        "__DIM__Manned:",
        ...rows(MISSIONS.filter(crewed)),
        "",
        "__DIM__Unmanned:",
        ...rows(MISSIONS.filter((m) => !crewed(m))),
      ];
    }
    if (arg === "off") {
      store.requestTrack(null);
      return ["Mission cleared."];
    }
    const mission = MISSIONS.find((m) => m.id === arg.replace(/\s+/g, "") || m.name.toLowerCase() === arg);
    if (!mission) return [`Unknown mission: ${args.join(" ")}. Type "launch" to see the list.`];
    store.setLeftPanel("");
    if (store.scaleMode !== "true") store.setScaleMode("true"); // flybys only line up at true scale
    if (!store.orbitsHighlighted) store.setOrbitsHighlighted(true); // paths make the flybys readable
    store.requestTrack(mission.id);
    const note = mission.note ? [`__GRAY__${mission.note}`] : [];
    if (mission.secondsPerDay) {
      store.setSecondsPerDay(mission.secondsPerDay);
      const ms = Math.round(mission.secondsPerDay * 1000);
      const shown = ms < 1000 ? `${ms}ms` : `${mission.secondsPerDay}s`;
      return [`Launching ${mission.name}. One Earth day now takes ${shown}. Use "time" to change it.`, ...note];
    }
    return [`Launching ${mission.name}. Use "time" to speed up the clock.`, ...note];
  },
  complete: (args) => (args.length <= 1 ? [...MISSIONS.map((m) => m.id), "off"] : []),
};

register(launch);
