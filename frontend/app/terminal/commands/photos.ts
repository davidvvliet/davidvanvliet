import { Command } from "../types";
import { run } from "../run";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";

const photos: Command = {
  name: "photos",
  aliases: ["p"],
  description: "Look through some photos",
  execute: (args) => {
    const slugs = usePageStore.getState().photoSlugs;
    const count = slugs.length;
    if (count === 0) return ["No photos yet."];
    const numbers = Array.from({ length: count }, (_, i) => i + 1);
    if (!args[0]) {
      usePageStore.getState().openPath(`/photos/${slugs[0]}`);
      return [`Photos: ${numbers.map((n) => run(`photos ${n}`, String(n))).join(" ")}`];
    }
    const n = Number(args[0]);
    if (!Number.isInteger(n) || n < 1 || n > count) return [`No photo ${args[0]}. There are ${count}.`];
    usePageStore.getState().openPath(`/photos/${slugs[n - 1]}`);
    return [`Photo ${n} of ${count}.`];
  },
  complete: (args) => (args.length <= 1 ? Array.from({ length: usePageStore.getState().photoSlugs.length }, (_, i) => String(i + 1)) : []),
};

register(photos);
