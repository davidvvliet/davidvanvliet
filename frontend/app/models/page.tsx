import fs from "fs";
import path from "path";
import { Suspense } from "react";
import { Metadata } from "next";
import PublishedModels, { Published } from "./PublishedModels";

export const metadata: Metadata = {
  title: "Models",
  robots: { index: false, follow: false },
};

type Spec = { title?: string; sources?: { id: string; title: string; url: string; licence?: string }[] };

// How many values in the spec cite each source: every `source` outside the top-level list, a
// citation string that starts with the source's id ("nssdca, p.83"), as scripts/blender/lib/sources.py.
function citationCounts(spec: Spec): Map<string, number> {
  const counts = new Map<string, number>();
  const walk = (o: unknown, top: boolean) => {
    if (Array.isArray(o)) { o.forEach((v) => walk(v, false)); return; }
    if (!o || typeof o !== "object") return;
    for (const [k, v] of Object.entries(o)) {
      if (top && k === "sources") continue;
      if (k === "source") {
        for (const c of Array.isArray(v) ? v : [v]) {
          const id = typeof c === "string" ? c.match(/^[a-z0-9_]+/)?.[0] : undefined;
          if (id) counts.set(id, (counts.get(id) ?? 0) + 1);
        }
      } else walk(v, false);
    }
  };
  walk(spec, true);
  return counts;
}

// Published models: public/models/<probe>.glb, written by `npm run model:approve` (fixtures never get there),
// with their spec's title and sources.
function published(): Published[] {
  const specs = path.join(process.cwd(), "scripts", "blender", "specs");
  const spec = (probe: string): Spec => {
    try { return JSON.parse(fs.readFileSync(path.join(specs, `${probe}.json`), "utf8")); } catch { return {}; }
  };
  const dir = path.join(process.cwd(), "public", "models");
  try {
    const files = fs.readdirSync(dir);
    return files.filter((f) => f.endsWith(".glb")).map((f) => f.slice(0, -4)).sort().map((probe) => {
      const s = spec(probe);
      const cited = citationCounts(s);
      // Licences are shown up to any ":" (the terms, not the harness's note on what it kept).
      return {
        probe, title: s.title ?? probe, thumb: files.includes(`${probe}.webp`),
        sources: (s.sources ?? []).map((x) => ({ title: x.title, url: x.url, licence: x.licence?.split(":")[0] ?? null, cited: cited.get(x.id) ?? 0 })),
      };
    });
  } catch {
    return [];
  }
}

// The published models, listed when the site is built (?probe=<name> opens one). Locally the
// same page, plus /models?dashboard: the build dashboard, which watches the Blender harness in
// scripts/blender (see its README).
export default function ModelsPage() {
  return <Suspense><PublishedModels models={published()} dashboard={process.env.NODE_ENV !== "production"} /></Suspense>;
}
