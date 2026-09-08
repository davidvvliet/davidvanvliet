import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const REAL_SECONDS_PER_DAY = 86400;
const MIN_SECONDS_PER_DAY = 0.01; // Earth's spin strobes below ~33ms per day; accepted down to 10ms

// "60", "60s", "10ms", "2m", "2 minutes", "1.5 hours", "real"
const UNIT_SECONDS: Record<string, number> = {
  ms: 0.001, millisecond: 0.001, milliseconds: 0.001,
  s: 1, sec: 1, secs: 1, second: 1, seconds: 1,
  m: 60, min: 60, mins: 60, minute: 60, minutes: 60,
  h: 3600, hr: 3600, hrs: 3600, hour: 3600, hours: 3600,
};
function parseSeconds(input: string): number | null {
  if (input === "real") return REAL_SECONDS_PER_DAY;
  const m = /^(\d+(?:\.\d+)?)\s*([a-z]*)$/.exec(input);
  if (!m) return null;
  const factor = m[2] ? UNIT_SECONDS[m[2]] : 1;
  if (factor === undefined) return null;
  return parseFloat(m[1]) * factor;
}

function describe(seconds: number): string {
  if (seconds === REAL_SECONDS_PER_DAY) return "real time";
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${+seconds.toFixed(2)}s`;
  if (seconds < 3600) return `${+(seconds / 60).toFixed(2)}m`;
  return `${+(seconds / 3600).toFixed(2)}h`;
}

const time: Command = {
  name: "time",
  category: "explore",
  description: "Set how long an Earth day takes",
  execute: (args) => {
    const store = usePageStore.getState();
    if (!args[0]) {
      return [
        "__DIM__Usage: time <duration> | real",
        `One Earth day currently takes ${describe(store.secondsPerDay)}.`,
      ];
    }
    const input = args.join(" ").trim().toLowerCase(); // "2 minutes" arrives as two words
    const seconds = parseSeconds(input);
    if (seconds === null) return [`Couldn't read "${input}". Use a number with ms, s, m or h, or "real".`];
    if (seconds < MIN_SECONDS_PER_DAY) return ["That's too fast matey. Minimum is 10ms per day."];
    store.setSecondsPerDay(seconds);
    return [`One Earth day now takes ${describe(seconds)}.`];
  },
  complete: (args) => (args.length <= 1 ? ["10s", "60s", "1m", "real"] : []),
};

register(time);
