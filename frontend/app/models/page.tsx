import fs from "fs";
import path from "path";
import { Suspense } from "react";
import { Metadata } from "next";
import PublishedModels from "./PublishedModels";

export const metadata: Metadata = {
  title: "Probe models",
  robots: { index: false, follow: false },
};

// Published models: public/models/<probe>.glb, written by `npm run model:approve` (fixtures never get there).
function published(): { probe: string; title: string; thumb: boolean }[] {
  const specs = path.join(process.cwd(), "scripts", "blender", "specs");
  const title = (probe: string) => {
    try { return JSON.parse(fs.readFileSync(path.join(specs, `${probe}.json`), "utf8")).title ?? probe; } catch { return probe; }
  };
  const dir = path.join(process.cwd(), "public", "models");
  try {
    const files = fs.readdirSync(dir);
    return files.filter((f) => f.endsWith(".glb")).map((f) => f.slice(0, -4)).sort()
      .map((probe) => ({ probe, title: title(probe), thumb: files.includes(`${probe}.webp`) }));
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
