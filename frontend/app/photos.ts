import fs from "node:fs";
import path from "node:path";
import type { Photo } from "./photoTypes";

// Everything in public/photos is shown, in filename order. An image and a video
// with the same name are one clip (the image is its still). Server only: the
// list is read when the pages are built.
const DIR = path.join(process.cwd(), "public", "photos");
const IMAGE = /\.(webp|jpe?g|png|avif|gif)$/i;
const VIDEO = /\.(webm|mp4)$/i;

export function getPhotos(): Photo[] {
  let files: string[] = [];
  try { files = fs.readdirSync(DIR); } catch { return []; }
  const groups = new Map<string, { image?: string; video?: string }>();
  for (const file of files) {
    const kind = IMAGE.test(file) ? "image" : VIDEO.test(file) ? "video" : null;
    if (!kind) continue;
    const name = file.replace(/\.[^.]+$/, "");
    groups.set(name, { ...groups.get(name), [kind]: `/photos/${encodeURIComponent(file)}` });
  }
  return [...groups.keys()]
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .map((name, i) => ({ n: i + 1, ...groups.get(name)! }));
}
