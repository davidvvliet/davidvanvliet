import fs from "node:fs";
import path from "node:path";
import type { GlobePaths } from "./photoTypes";

// A still of the home page's Earth, centred on one place with north up, drawn
// as two SVG paths in a -50..50 viewBox. It is built from what the 3D globe is
// built from (SolarSystem.tsx): the wireframe of THREE.SphereGeometry(r, 32, 32)
// and the outlines in public/continents.json, both as straight chords between
// their points, with the far side hidden. Server only: runs when pages build.

const R = 50;
const SEGMENTS = 32;
const LAND_TOLERANCE = 0.4; // viewBox units; under half a pixel at the largest size shown
const D2R = Math.PI / 180;

type V = [number, number, number]; // x right, y up, z toward the viewer (z > 0 is the near side)
type LonLat = [number, number];

let land: LonLat[][] | null = null;
function continentRings(): LonLat[][] {
  if (land) return land;
  const geo = JSON.parse(fs.readFileSync(path.join(process.cwd(), "public", "continents.json"), "utf8"));
  land = [];
  for (const f of geo.features) {
    const g = f.geometry;
    if (!g) continue;
    const polygons = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
    for (const polygon of polygons) for (const ring of polygon) if (ring.length >= 3) land.push(ring);
  }
  return land;
}

// Orthographic view from above (lat0, lon0).
function viewFrom(lat0: number, lon0: number) {
  const s0 = Math.sin(lat0 * D2R), c0 = Math.cos(lat0 * D2R);
  return ([lon, lat]: LonLat): V => {
    const p = lat * D2R, l = (lon - lon0) * D2R;
    const cp = Math.cos(p), sp = Math.sin(p);
    return [cp * Math.sin(l), c0 * sp - s0 * cp * Math.cos(l), s0 * sp + c0 * cp * Math.cos(l)];
  };
}

// The near-side pieces of a polyline, cut where a chord passes behind the globe.
function nearRuns(points: V[]): V[][] {
  const runs: V[][] = [];
  let run: V[] = [];
  points.forEach((p, i) => {
    const q = points[i - 1];
    if (q && q[2] > 0 !== p[2] > 0) {
      const t = q[2] / (q[2] - p[2]);
      run.push([q[0] + t * (p[0] - q[0]), q[1] + t * (p[1] - q[1]), 0]);
      if (q[2] > 0) { runs.push(run); run = []; }
    }
    if (p[2] > 0) run.push(p);
  });
  if (run.length) runs.push(run);
  return runs;
}

const num = (v: number) => String(Math.round(v * 10) / 10).replace(/^-0$/, "0");

// Douglas–Peucker: drop points that stray less than tolerance from the line
// between their neighbours, so a coastline keeps its shape with far fewer points.
function simplify(pts: [number, number][], tolerance: number): [number, number][] {
  if (tolerance <= 0 || pts.length < 3) return pts;
  const keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length - 1] = 1;
  const stack: [number, number][] = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop()!;
    const [ax, ay] = pts[a], [bx, by] = pts[b];
    const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy);
    let far = -1, farDist = tolerance;
    for (let i = a + 1; i < b; i++) {
      const [px, py] = pts[i];
      const dist = len ? Math.abs(dy * (px - ax) - dx * (py - ay)) / len : Math.hypot(px - ax, py - ay);
      if (dist > farDist) { far = i; farDist = dist; }
    }
    if (far > 0) { keep[far] = 1; stack.push([a, far], [far, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}

function toPath(view: (p: LonLat) => V, tolerance: number, src: LonLat[][]): string {
  let d = "";
  for (const line of src) {
    for (const run of nearRuns(line.map(view))) {
      const pts = run.map((v): [number, number] => [v[0] * R, -v[1] * R]);
      const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
      // Islands too small to see at this size are left out.
      if (Math.max(...xs) - Math.min(...xs) < tolerance * 2 && Math.max(...ys) - Math.min(...ys) < tolerance * 2) continue;
      const kept = simplify(pts, tolerance);
      if (kept.length > 1) d += "M" + kept.map(([x, y]) => `${num(x)} ${num(y)}`).join("L");
    }
  }
  return d;
}

// The sphere's wireframe as THREE draws it: a vertex every 360/32 degrees of
// longitude (column ix sits at lon ix * 11.25, from lonLatToVector3's mapping)
// and 180/32 of latitude, joined along each parallel, each meridian, and one
// diagonal per quad (row iy, column ix to row iy + 1, column ix + 1).
function gridLines(): LonLat[][] {
  const at = (iy: number, ix: number): LonLat => [ix * (360 / SEGMENTS), 90 - iy * (180 / SEGMENTS)];
  const lines: LonLat[][] = [];
  for (let iy = 1; iy < SEGMENTS; iy++) lines.push(Array.from({ length: SEGMENTS + 1 }, (_, ix) => at(iy, ix)));
  for (let ix = 0; ix < SEGMENTS; ix++) lines.push(Array.from({ length: SEGMENTS + 1 }, (_, iy) => at(iy, ix)));
  for (let k = 0; k < SEGMENTS; k++) lines.push(Array.from({ length: SEGMENTS + 1 }, (_, iy) => at(iy, k + iy)));
  return lines;
}

export function globePaths(lat: number, lon: number): GlobePaths {
  const view = viewFrom(lat, lon);
  return {
    grid: toPath(view, 0, gridLines()),
    land: toPath(view, LAND_TOLERANCE, continentRings()),
  };
}
