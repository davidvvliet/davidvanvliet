import { Command } from "../types";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const jdToDate = (jd: number) => new Date((jd - 2440587.5) * 86400000);
const dateToJd = (d: Date) => d.getTime() / 86400000 + 2440587.5;
const fmt = (d: Date) => d.toISOString().slice(0, 16).replace("T", " ") + " UTC";

const date: Command = {
  name: "date",
  category: "explore",
  description: "Show or set the simulated date",
  execute: (args) => {
    const store = usePageStore.getState();
    if (!args[0]) {
      if (!store.simJD) return ["The clock hasn't started yet."];
      return [`Simulated date: ${fmt(jdToDate(store.simJD))}`];
    }
    if (args[0].toLowerCase() === "now") {
      store.requestDate(dateToJd(new Date()));
      return ["Clock set to now."];
    }
    const d = new Date(args.join(" ") + (args[0].length <= 10 ? "T00:00:00Z" : ""));
    if (isNaN(d.getTime())) return [`Couldn't read "${args.join(" ")}". Use YYYY-MM-DD, or "now".`];
    store.requestDate(dateToJd(d));
    return [`Clock set to ${fmt(d)}.`];
  },
  complete: (args) => (args.length <= 1 ? ["now"] : []),
};

register(date);
