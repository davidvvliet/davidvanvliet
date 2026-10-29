// Dev-only window onto the Blender harness (scripts/blender) for the /models dashboard:
//   /api/models/status                    build status, plus each probe's spec summary and refs
//   /api/models/file/<worktree>/<path>    a file under that worktree's out/, refs/ or baselines/;
//                                         circuit/<path>: under scripts/circuit/out/ (the /circuit boards)
// Circuit boards (scripts/circuit/build.py) are listed as probes too, with kind "circuit".
// Every git worktree of this repo is read, so sessions working in their own worktrees all show
// up on the one dashboard: each probe lists the builds found per worktree, newest first.
// Returns 404 in production, where the harness output does not exist.
import { execFile } from "child_process";
import { promises as fs } from "fs";
import path from "path";
import { NextRequest } from "next/server";

const HARNESS = path.join("scripts", "blender");
const ROOT = path.join(process.cwd(), HARNESS); // this server's own checkout
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

const run = (cmd: string, args: string[], cwd?: string) => new Promise<string | null>((resolve) => {
  execFile(cmd, args, { cwd, timeout: 10000 }, (err, out) => resolve(err ? null : out));
});

// The repo's worktrees (`git worktree list`), cached briefly: the dashboard polls every second.
// `id` (the folder name) goes in file URLs; `label` is what the dashboard shows ("main" for the
// main checkout, else the folder name without the main checkout's name, e.g. "x15").
// `working`: probes whose own files (spec, script, refs) the worktree has changed, uncommitted
// or in commits not on origin/main: that is where someone is working on them.
type Worktree = { id: string; label: string; branch: string | null; root: string; working: string[] };

async function working(dir: string, harness: string) {
  const circuit = path.join(path.dirname(harness), "circuit");
  const [changed, ahead] = await Promise.all([
    run("git", ["status", "--porcelain", "--untracked-files=all", "--", harness, circuit], dir),
    run("git", ["diff", "--name-only", "origin/main...HEAD", "--", harness, circuit], dir),
  ]);
  const files = [...(changed ?? "").split("\n").map((l) => l.slice(3).split(" -> ").pop()!), ...(ahead ?? "").split("\n")];
  const own = new RegExp(`^${harness.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/(?:specs/([^/]+)\\.json|probes/([^/]+)\\.py|refs/([^/]+)/)`);
  const board = new RegExp(`^${circuit.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/boards/([^/]+)/`);
  const names = new Set<string>();
  for (const f of files) { const m = f.match(own) ?? f.match(board); if (m) names.add(m[1] ?? m[2] ?? m[3]); }
  return [...names];
}
let treesCache: { at: number; value: Worktree[] } | null = null;
async function worktrees(): Promise<Worktree[]> {
  if (treesCache && Date.now() - treesCache.at < 5000) return treesCache.value;
  const out = await run("git", ["worktree", "list", "--porcelain"], process.cwd());
  const entries: { dir: string; branch: string | null }[] = [];
  for (const block of (out ?? "").split("\n\n")) {
    const dir = block.match(/^worktree (.+)$/m)?.[1];
    if (dir) entries.push({ dir, branch: block.match(/^branch refs\/heads\/(.+)$/m)?.[1] ?? null });
  }
  // Where this server's frontend sits inside its own worktree, the same in every worktree.
  const own = entries.filter((e) => process.cwd() === e.dir || process.cwd().startsWith(e.dir + path.sep))
    .sort((a, b) => b.dir.length - a.dir.length)[0];
  const rel = own ? path.relative(own.dir, process.cwd()) : "";
  const main = entries[0] ? path.basename(entries[0].dir) : "";
  const value: Worktree[] = [];
  for (const [i, e] of entries.entries()) {
    const root = path.join(e.dir, rel, HARNESS);
    try { await fs.access(path.join(root, "specs")); } catch { continue; } // gone, or no harness
    const id = path.basename(e.dir);
    if (value.some((w) => w.id === id)) continue; // same folder name twice: first one wins
    const label = i === 0 ? "main" : id.startsWith(main + "-") ? id.slice(main.length + 1) : id;
    value.push({ id, label, branch: e.branch, root, working: await working(e.dir, path.join(rel, HARNESS)) });
  }
  if (!value.length) value.push({ id: path.basename(path.dirname(process.cwd())), label: "main", branch: null, root: ROOT, working: [] });
  treesCache = { at: Date.now(), value };
  return value;
}

// Whether each published model is behind the repo (scripts/blender/lib/published.py), cached
// briefly: the dashboard polls status often and this hashes every input file. Always this
// server's checkout: that is what the site ships.
type Behind = Record<string, { own: string[]; shared: string[] }>;
let behindCache: { at: number; value: Behind } | null = null;
async function behind(): Promise<Behind> {
  if (behindCache && Date.now() - behindCache.at < 5000) return behindCache.value;
  const out = await run("python3", ["-I", path.join(ROOT, "lib", "published.py")]);
  let value: Behind = {};
  try { if (out) value = JSON.parse(out); } catch {}
  behindCache = { at: Date.now(), value };
  return value;
}

type Build = { started: number } & Record<string, unknown>;
type Current = { probe: string; state: string; at: number } & Record<string, unknown>;

async function status() {
  const [published, trees] = await Promise.all([behind(), worktrees()]);
  const perTree = await Promise.all(trees.map(async (w) => {
    const build = (await readJson(path.join(w.root, "out", "status.json"))) ?? {};
    let names: string[] = [];
    try { names = (await fs.readdir(path.join(w.root, "specs"))).filter((f) => f.endsWith(".json")).map((f) => f.slice(0, -5)); } catch {}
    const circuit = path.join(w.root, "..", "circuit");
    let boards: string[] = [];
    try { boards = (await fs.readdir(path.join(circuit, "boards"))).filter((b) => !b.startsWith(".")); } catch {}
    const boardBuilds = ((await readJson(path.join(circuit, "out", "status.json"))) ?? {}).boards ?? {};
    return { w, names, probes: (build.probes ?? {}) as Record<string, Build>, current: (build.current ?? null) as Current | null, updated: (build.updated ?? null) as number | null,
      boards, boardBuilds: boardBuilds as Record<string, Build> };
  }));
  const names = [...new Set(perTree.flatMap((t) => t.names))].sort();
  const probes = await Promise.all(names.map(async (name) => {
    // The worktrees that have built this probe or are changing it: those changing it first, then
    // newest build first. With none, the main checkout's (unbuilt) copy.
    const rows = await Promise.all(perTree.filter((t) => t.names.includes(name)).map(async (t) => ({
      worktree: t.w.id, label: t.w.label, branch: t.w.branch,
      working: t.w.working.includes(name),
      build: t.probes[name] ?? null,
      refs: await listImages(path.join(t.w.root, "refs", name)),
    })));
    const shown = rows.filter((r) => r.build || r.working);
    const sources = (shown.length ? shown : rows.slice(0, 1))
      .sort((a, b) => Number(b.working) - Number(a.working) || (b.build?.started ?? -1) - (a.build?.started ?? -1));
    const spec = (await readJson(path.join(trees.find((w) => w.id === sources[0].worktree)!.root, "specs", `${name}.json`))) ?? {};
    return {
      name,
      title: spec.title ?? name,
      fixture: !!spec.fixture,
      note: spec.note ?? null,
      sources: spec.sources ?? [],
      referenceModel: spec.reference_model ?? null,
      published: published[name] ?? null,
      worktrees: sources,
    };
  }));
  const boardNames = [...new Set(perTree.flatMap((t) => t.boards))].sort();
  const boards = await Promise.all(boardNames.map(async (name) => {
    const rows = perTree.filter((t) => t.boards.includes(name)).map((t) => ({
      worktree: t.w.id, label: t.w.label, branch: t.w.branch, working: t.w.working.includes(name),
      build: t.boardBuilds[name] ?? null, refs: [] as string[],
    }));
    const shown = rows.filter((r) => r.build || r.working);
    const sources = (shown.length ? shown : rows.slice(0, 1))
      .sort((a, b) => Number(b.working) - Number(a.working) || (b.build?.started ?? -1) - (a.build?.started ?? -1));
    const root = trees.find((w) => w.id === sources[0].worktree)!.root;
    const meta = (await readJson(path.join(root, "..", "circuit", "boards", name, "board.json"))) ?? {};
    return {
      name, kind: "circuit", title: meta.title ?? name, fixture: false, note: meta.purpose ?? null,
      sources: meta.source ? [{ title: meta.source.title, url: meta.source.url }] : [], referenceModel: null,
      published: null, worktrees: sources,
    };
  }));
  // The build happening now: a running one anywhere, else the latest to finish.
  const currents = perTree.filter((t) => t.current).map((t) => ({ ...t.current!, worktree: t.w.id, label: t.w.label }));
  currents.sort((a, b) => Number(b.state === "running") - Number(a.state === "running") || b.at - a.at);
  const updated = Math.max(0, ...perTree.map((t) => t.updated ?? 0)) || null;
  return Response.json({ updated, current: currents[0] ?? null, probes: [...probes, ...boards] }, {
    headers: { "Cache-Control": "no-store" },
  });
}

export async function GET(_req: NextRequest, ctx: RouteContext<"/api/models/[...path]">) {
  if (process.env.NODE_ENV === "production") return notFound();
  const { path: parts } = await ctx.params;
  if (parts.length === 1 && parts[0] === "status") return status();
  if (parts[0] !== "file" || parts.length < 4 || !(SERVED_DIRS.has(parts[2]) || parts[2] === "circuit")) return notFound();
  const tree = (await worktrees()).find((w) => w.id === parts[1]);
  if (!tree) return notFound();
  const base = parts[2] === "circuit" ? path.resolve(tree.root, "..", "circuit", "out") : tree.root;
  const file = path.resolve(base, ...parts.slice(parts[2] === "circuit" ? 3 : 2));
  if (!file.startsWith(base + path.sep)) return notFound();
  try {
    const body = await fs.readFile(file);
    return new Response(body, {
      headers: { "Content-Type": TYPES[path.extname(file).toLowerCase()] ?? "application/octet-stream", "Cache-Control": "no-store" },
    });
  } catch {
    return notFound();
  }
}
