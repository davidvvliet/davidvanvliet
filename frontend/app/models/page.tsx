import fs from "fs";
import path from "path";
import { Suspense } from "react";
import { Metadata } from "next";
import ModelsDashboard from "./ModelsDashboard";
import PublishedModels from "./PublishedModels";

export const metadata: Metadata = {
  title: "Probe models",
  robots: { index: false, follow: false },
};

// Published models: public/models/<probe>.glb, written by `npm run model:approve` (fixtures never get there).
function published(): { probe: string; title: string }[] {
  const specs = path.join(process.cwd(), "scripts", "blender", "specs");
  const title = (probe: string) => {
    try { return JSON.parse(fs.readFileSync(path.join(specs, `${probe}.json`), "utf8")).title ?? probe; } catch { return probe; }
  };
  try {
    return fs.readdirSync(path.join(process.cwd(), "public", "models"))
      .filter((f) => f.endsWith(".glb")).map((f) => f.slice(0, -4)).sort().map((probe) => ({ probe, title: title(probe) }));
  } catch {
    return [];
  }
}

// Locally: the build dashboard, which watches the Blender harness in scripts/blender (see its README).
// On the live site: the published models, listed when the site is built (?probe=<name> picks one).
export default function ModelsPage() {
  if (process.env.NODE_ENV !== "production") return <ModelsDashboard />;
  return <Suspense><PublishedModels models={published()} /></Suspense>;
}
