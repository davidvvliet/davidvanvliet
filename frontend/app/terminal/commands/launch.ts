import { Command } from "../types";
import { run } from "../run";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";
import { MISSIONS } from '../../missions';

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
      const proposed = (m: (typeof MISSIONS)[number]) => /^lyra/.test(m.id);
      const rows = (list: typeof MISSIONS) => {
        // Each number launches its mission; a program with no numbers is itself the mission.
        const programs = new Map<string, { id: string; number: string | null }[]>();
        for (const m of list) {
          const match = m.name.match(/^(.*?)\s+([0-9]+[a-z]?|[IVX]+)$/);
          const program = match ? match[1] : m.name;
          programs.set(program, [...(programs.get(program) ?? []), { id: m.id, number: match ? match[2] : null }]);
        }
        return [...programs].map(([program, missions]) => {
          const numbered = missions.filter((m) => m.number);
          const name = numbered.length ? program : run(`launch ${missions[0].id}`, program);
          return `__COL__${name}__COL__${numbered.map((m) => run(`launch ${m.id}`, m.number!)).join("  ")}`;
        });
      };
      return [
        `__DIM__Usage: launch <mission> | ${run("launch off", "off")}`,
        "",
        "__DIM__Manned:",
        ...rows(MISSIONS.filter(crewed)),
        "",
        "__DIM__Unmanned:",
        ...rows(MISSIONS.filter((m) => !crewed(m) && !proposed(m))),
        "",
        "__DIM__Proposed:",
        ...rows(MISSIONS.filter(proposed)),
      ];
    }
    if (arg === "off") {
      store.requestTrack(null);
      // Back to the clock rate the user had before launching.
      if (store.clockRateBeforeMission !== null) {
        store.setSecondsPerDay(store.clockRateBeforeMission);
        store.setClockRateBeforeMission(null);
      }
      return ["Mission cleared."];
    }
    const mission = MISSIONS.find((m) => m.id === arg.replace(/\s+/g, "") || m.name.toLowerCase() === arg);
    if (!mission) return [`Unknown mission: ${args.join(" ")}. Type "${run("launch")}" to see the list.`];
    store.openPath("/");
    if (store.scaleMode !== "true") store.setScaleMode("true"); // flybys only line up at true scale
    if (!store.orbitsHighlighted) store.setOrbitsHighlighted(true); // paths make the flybys readable
    // Remember the pre-mission rate once; launching another mission keeps the original.
    if (store.clockRateBeforeMission === null) store.setClockRateBeforeMission(store.secondsPerDay);
    store.requestTrack(mission.id);
    const note = mission.note ? [mission.note] : [];
    if (mission.secondsPerDay) {
      store.setSecondsPerDay(mission.secondsPerDay);
      const ms = Math.round(mission.secondsPerDay * 1000);
      const shown = ms < 1000 ? `${ms}ms` : `${mission.secondsPerDay}s`;
      return [`__GRAY__Launching ${mission.name}. One Earth day now takes ${shown}. Use "${run("time")}" to change it.`, ...note];
    }
    return [`__GRAY__Launching ${mission.name}. Use "${run("time")}" to speed up the clock.`, ...note];
  },
  complete: (args) => (args.length <= 1 ? [...MISSIONS.map((m) => m.id), "off"] : []),
};

register(launch);
