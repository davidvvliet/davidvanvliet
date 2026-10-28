import fs from "node:fs";
import path from "node:path";
import type { Photo } from "./photoTypes";
import captions from "./photoCaptions.json";

// Everything in public/photos is shown, in filename order. An image and a video
// with the same name are one clip (the image is its still). Captions live in
// photoCaptions.json, keyed by file name without extension, each with the short
// slug its URL uses (/photos/<slug>). Server only: the list is read when the
// pages are built.
const DIR = path.join(process.cwd(), "public", "photos");
const IMAGE = /\.(webp|jpe?g|png|avif|gif)$/i;
const VIDEO = /\.(webm|mp4)$/i;
const CAPTIONS: Record<string, { caption: string; slug?: string }> = captions;

const slugify = (s: string) =>
  s.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

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
  const used = new Set<string>();
  return [...groups.keys()]
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .map((name, i) => {
      const n = i + 1;
      const caption = CAPTIONS[name]?.caption;
      let slug = slugify(CAPTIONS[name]?.slug ?? caption ?? "") || String(n);
      if (used.has(slug) || (/^\d+$/.test(slug) && slug !== String(n))) slug = `${slug}-${n}`;
      used.add(slug);
      return { n, slug, ...(caption ? { caption } : {}), ...groups.get(name)! };
    });
}
