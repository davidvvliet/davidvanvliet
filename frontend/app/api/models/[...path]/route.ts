// Dev-only window onto the Blender harness (scripts/blender) for the /models dashboard:
//   /api/models/status          build status, plus each probe's spec summary and refs
//   /api/models/file/<path>     a file under out/, refs/ or baselines/
// Returns 404 in production, where the harness output does not exist.
import { execFile } from "child_process";
import { promises as fs } from "fs";
import path from "path";
import { NextRequest } from "next/server";

const ROOT = path.join(process.cwd(), "scripts", "blender");
const SERVED_DIRS = new Set(["out", "refs", "baselines"]);
const TYPES: Record<string, string> = {
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
  ".glb": "model/gltf-binary", ".json": "application/json",
};
const IMAGE = /\.(png|jpe?g|webp)$/i;

const notFound = () => new Response("Not found", { status: 404 });

async function readJson(file: string) {
  try { return JSON.parse(await fs.readFile(file, "utf8")); } catch { return null; }
}

async function listImages(dir: string) {
  try { return (await fs.readdir(dir)).filter((f) => IMAGE.test(f)).sort(); } catch { return []; }
}

// Whether each published model is behind the repo (scripts/blender/lib/published.py), cached
// briefly: the dashboard polls status often and this hashes every input file.
type Behind = Record<string, { own: string[]; shared: string[] }>;
let behindCache: { at: number; value: Behind } | null = null;
function behind(): Promise<Behind> {
  if (behindCache && Date.now() - behindCache.at < 5000) return Promise.resolve(behindCache.value);
  return new Promise((resolve) => {
    execFile("python3", ["-I", path.join(ROOT, "lib", "published.py")], { timeout: 10000 }, (err, out) => {
      let value: Behind = {};
      try { if (!err) value = JSON.parse(out); } catch {}
      behindCache = { at: Date.now(), value };
      resolve(value);
    });
  });
}

async function status() {
  const published = await behind();
  const build = (await readJson(path.join(ROOT, "out", "status.json"))) ?? { current: null, probes: {} };
  const names = (await fs.readdir(path.join(ROOT, "specs"))).filter((f) => f.endsWith(".json")).map((f) => f.slice(0, -5)).sort();
  const probes = await Promise.all(names.map(async (name) => {
    const spec = (await readJson(path.join(ROOT, "specs", `${name}.json`))) ?? {};
    return {
      name,
      title: spec.title ?? name,
      fixture: !!spec.fixture,
      note: spec.note ?? null,
      sources: spec.sources ?? [],
      referenceModel: spec.reference_model ?? null,
      refs: await listImages(path.join(ROOT, "refs", name)),
      build: build.probes?.[name] ?? null,
      published: published[name] ?? null,
    };
  }));
  return Response.json({ updated: build.updated ?? null, current: build.current ?? null, probes }, {
    headers: { "Cache-Control": "no-store" },
  });
}

export async function GET(_req: NextRequest, ctx: RouteContext<"/api/models/[...path]">) {
  if (process.env.NODE_ENV === "production") return notFound();
  const { path: parts } = await ctx.params;
  if (parts.length === 1 && parts[0] === "status") return status();
  if (parts[0] !== "file" || !SERVED_DIRS.has(parts[1])) return notFound();
  const file = path.resolve(ROOT, ...parts.slice(1));
  if (!file.startsWith(ROOT + path.sep)) return notFound();
  try {
    const body = await fs.readFile(file);
    return new Response(body, {
      headers: { "Content-Type": TYPES[path.extname(file).toLowerCase()] ?? "application/octet-stream", "Cache-Control": "no-store" },
    });
  } catch {
    return notFound();
  }
}
