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
      return ["__DIM__Usage: launch <mission> | off", `Missions: ${MISSIONS.map((m) => m.name).join(", ")}`];
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
    if (mission.secondsPerDay) {
      store.setSecondsPerDay(mission.secondsPerDay);
      const ms = Math.round(mission.secondsPerDay * 1000);
      const shown = ms < 1000 ? `${ms}ms` : `${mission.secondsPerDay}s`;
      return [`Launching ${mission.name}. One Earth day now takes ${shown}. Use "time" to change it.`];
    }
    return [`Launching ${mission.name}. Use "time" to speed up the clock.`];
  },
  complete: (args) => (args.length <= 1 ? [...MISSIONS.map((m) => m.id), "off"] : []),
};

register(launch);
