import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const REAL_SECONDS_PER_DAY = 86400;
const MIN_SECONDS_PER_DAY = 0.05; // below ~33ms Earth spins more than half a turn per frame at 60 fps and strobes

// "60", "60s", "10ms", "2m", "1h", "real"
function parseSeconds(input: string): number | null {
  if (input === "real") return REAL_SECONDS_PER_DAY;
  const m = /^(\d+(?:\.\d+)?)\s*(ms|s|m|h)?$/.exec(input);
  if (!m) return null;
  const n = parseFloat(m[1]);
  const unit = m[2] ?? "s";
  const factor = unit === "ms" ? 0.001 : unit === "m" ? 60 : unit === "h" ? 3600 : 1;
  return n * factor;
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
  description: "Set how long an Earth day takes",
  execute: (args) => {
    const store = usePageStore.getState();
    if (!args[0]) {
      return [
        "__DIM__Usage: time <duration> | real",
        `One Earth day currently takes ${describe(store.secondsPerDay)}.`,
      ];
    }
    const seconds = parseSeconds(args[0].toLowerCase());
    if (seconds === null) return [`Couldn't read "${args[0]}". Use a number with ms, s, m or h, or "real".`];
    if (seconds < MIN_SECONDS_PER_DAY) return ["That's too fast matey. Minimum is 50ms per day."];
    store.setSecondsPerDay(seconds);
    return [`One Earth day now takes ${describe(seconds)}.`];
  },
  complete: (args) => (args.length <= 1 ? ["10s", "60s", "1m", "real"] : []),
};

register(time);
