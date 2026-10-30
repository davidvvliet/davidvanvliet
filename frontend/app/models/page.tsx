import fs from "fs";
import path from "path";
import { Suspense } from "react";
import { Metadata } from "next";
import PublishedModels, { Published } from "./PublishedModels";

export const metadata: Metadata = {
  title: "Models",
  robots: { index: false, follow: false },
};

type Spec = { title?: string; logos?: string[]; listed?: boolean; viewer?: { explore?: boolean; focus?: { part: string; label: string }[]; explode?: string[] }; sources?: { id: string; title: string; url: string; licence?: string }[] };

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
    // A spec with "listed": false (an engine shown only on its vehicle) stays off the page.
    return files.filter((f) => f.endsWith(".glb")).map((f) => f.slice(0, -4)).sort()
      .filter((probe) => spec(probe).listed !== false).map((probe) => {
      const s = spec(probe);
      const cited = citationCounts(s);
      // Licences are shown up to any ":" (the terms, not the harness's note on what it kept).
      return {
        probe, title: (s.title ?? probe).replace(/\s*\(.*\)\s*$/, ""), // the name only, not its note in brackets
        logos: s.logos ?? [], thumb: files.includes(`${probe}.webp`), explore: s.viewer?.explore !== false, focus: s.viewer?.focus ?? [], explode: s.viewer?.explode ?? [],
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
// The board the "My circuit experiments" card shows (public/circuits/, see app/circuits).
const CIRCUIT_CARD = "rocket-recorder";

export default function ModelsPage() {
  const circuit = fs.existsSync(path.join(process.cwd(), "public", "circuits", `${CIRCUIT_CARD}.glb`)) ? CIRCUIT_CARD : null;
  return <Suspense><PublishedModels models={published()} circuit={circuit} dashboard={process.env.NODE_ENV !== "production"} /></Suspense>;
}
