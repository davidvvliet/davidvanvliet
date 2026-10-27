import { Command } from "../types";
import { run } from "../run";
import { register } from "../registry";
import { usePageStore } from "../../store/pageStore";
import { PHOTOS, getPhoto } from "../../photos";

const photos: Command = {
  name: "photos",
  aliases: ["p"],
  description: "Look through some photos",
  execute: (args) => {
    if (!args[0]) {
      usePageStore.getState().openPath("/photos/1");
      return [`Photos: ${PHOTOS.map((p) => run(`photos ${p.n}`, String(p.n))).join(" ")}`];
    }
    const n = Number(args[0]);
    if (!getPhoto(n)) return [`No photo ${args[0]}. There are ${PHOTOS.length}.`];
    usePageStore.getState().openPath(`/photos/${n}`);
    return [`Photo ${n} of ${PHOTOS.length}.`];
  },
  complete: (args) => (args.length <= 1 ? PHOTOS.map((p) => String(p.n)) : []),
};

register(photos);
