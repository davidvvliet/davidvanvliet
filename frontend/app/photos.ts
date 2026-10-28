import fs from "node:fs";
import path from "node:path";
import type { Photo } from "./photoTypes";
import captions from "./photoCaptions.json";

// Everything in public/photos is shown, in filename order. An image and a video
// with the same name are one clip (the image is its still). Titles, captions and
// the short slug each URL uses (/photos/<slug>) and where it was taken
// ("loc": [lat, lon], for the globe beside it) live in photoCaptions.json, keyed
// by file name without extension. Server only: the list is read when the
// pages are built.
const DIR = path.join(process.cwd(), "public", "photos");
const IMAGE = /\.(webp|jpe?g|png|avif|gif)$/i;
const VIDEO = /\.(webm|mp4)$/i;
const CAPTIONS: Record<string, { title?: string; caption?: string; slug?: string; loc?: number[] }> = captions;

// Pixel size from a WebP or PNG header, so the page knows portrait from
// landscape without decoding the image. Other formats give undefined.
function imageSize(file: string): { width: number; height: number } | undefined {
  let b: Buffer;
  try {
    const fd = fs.openSync(path.join(DIR, file), "r");
    b = Buffer.alloc(32);
    fs.readSync(fd, b, 0, 32, 0);
    fs.closeSync(fd);
  } catch { return undefined; }
  const tag = (at: number, len: number) => b.toString("latin1", at, at + len);
  if (tag(1, 3) === "PNG") return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
  if (tag(0, 4) !== "RIFF" || tag(8, 4) !== "WEBP") return undefined;
  const chunk = tag(12, 4);
  if (chunk === "VP8 ") return { width: b.readUInt16LE(26) & 0x3fff, height: b.readUInt16LE(28) & 0x3fff };
  if (chunk === "VP8L") return { width: 1 + (b[21] | ((b[22] & 0x3f) << 8)), height: 1 + ((b[22] >> 6) | (b[23] << 2) | ((b[24] & 0x0f) << 10)) };
  if (chunk === "VP8X") return { width: 1 + b.readUIntLE(24, 3), height: 1 + b.readUIntLE(27, 3) };
  return undefined;
}

const slugify = (s: string) =>
  s.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export function getPhotos(): Photo[] {
  let files: string[] = [];
  try { files = fs.readdirSync(DIR); } catch { return []; }
  const groups = new Map<string, { image?: string; video?: string; width?: number; height?: number }>();
  for (const file of files) {
    const kind = IMAGE.test(file) ? "image" : VIDEO.test(file) ? "video" : null;
    if (!kind) continue;
    const name = file.replace(/\.[^.]+$/, "");
    groups.set(name, { ...groups.get(name), [kind]: `/photos/${encodeURIComponent(file)}`, ...(kind === "image" ? imageSize(file) : {}) });
  }
  const used = new Set<string>();
  return [...groups.keys()]
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .map((name, i) => {
      const n = i + 1;
      const { title, caption, slug: short, loc } = CAPTIONS[name] ?? {};
      let slug = slugify(short ?? title ?? "") || String(n);
      if (used.has(slug) || (/^\d+$/.test(slug) && slug !== String(n))) slug = `${slug}-${n}`;
      used.add(slug);
      return { n, slug, ...(title ? { title } : {}), ...(caption ? { caption } : {}),
        ...(loc?.length === 2 ? { loc: [loc[0], loc[1]] as [number, number] } : {}), ...groups.get(name)! };
    });
}
