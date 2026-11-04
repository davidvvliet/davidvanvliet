import * as THREE from "three";

// The launch site: the real terrain around the track (scripts/aether/terrain.py), rebuilt here on the
// curved Moon. Two frames are used:
//  - launch frame: origin on the track bed at the track's start, x along the track, y up (radial), z = x × y;
//  - orbit frame: the Moon's centre at the origin, the track's end (the low point) at -y, moving +x.
// Positions in the Moon's body-fixed frame come from the polar stereographic map coordinates.

export type TerrainMeta = {
  R: number; jd: number; start: [number, number]; heading: number; length: number;
  profile: { ds: number; z: number[] }; u: number[]; v: number[]; zmin: number; zstep: number;
};

type V3 = [number, number, number];
const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const scale = (a: V3, k: number): V3 => [a[0] * k, a[1] * k, a[2] * k];
const cross = (a: V3, b: V3): V3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a: V3): V3 => scale(a, 1 / Math.hypot(a[0], a[1], a[2]));

export class Site {
  meta: TerrainMeta;
  fwd: [number, number]; left: [number, number];
  origin: V3; ex: V3; ey: V3; ez: V3;          // launch frame, in body-fixed coordinates
  ox: V3; oy: V3; oz: V3;                      // orbit frame axes
  exitUp: THREE.Vector3; exitFwd: THREE.Vector3; exitPos: THREE.Vector3; // in the launch frame

  constructor(meta: TerrainMeta) {
    this.meta = meta;
    const h = (meta.heading * Math.PI) / 180;
    this.fwd = [Math.cos(h), Math.sin(h)];
    this.left = [-Math.sin(h), Math.cos(h)];
    const [sx, sy] = meta.start;
    const up = this.unit(sx, sy);
    this.origin = scale(up, meta.R + meta.profile.z[0]);
    this.ey = up;
    this.ex = this.tangent(sx, sy);
    this.ez = cross(this.ex, this.ey);
    const L = meta.length, ex = sx + this.fwd[0] * L, ey = sy + this.fwd[1] * L;
    const P = this.unit(ex, ey), H = this.tangent(ex, ey);
    this.ox = H; this.oy = scale(P, -1); this.oz = cross(this.ox, this.oy);
    const zEnd = meta.profile.z[meta.profile.z.length - 1];
    this.exitPos = this.toLaunch(scale(P, meta.R + zEnd));
    this.exitUp = this.dirToLaunch(P);
    this.exitFwd = this.dirToLaunch(H);
  }

  /** Polar stereographic (south) -> unit vector, body-fixed. */
  unit(x: number, y: number): V3 {
    const R = this.meta.R, rho = Math.hypot(x, y), lat = 2 * Math.atan(rho / (2 * R)) - Math.PI / 2, lon = Math.atan2(x, y);
    return [Math.cos(lat) * Math.cos(lon), Math.cos(lat) * Math.sin(lon), Math.sin(lat)];
  }
  /** The horizontal direction along the track at a map point, body-fixed. */
  tangent(x: number, y: number): V3 {
    const P = this.unit(x, y), Q = this.unit(x + this.fwd[0], y + this.fwd[1]);
    const d = sub(Q, P);
    return norm(sub(d, scale(P, dot(d, P))));
  }
  toLaunch(p: V3, out = new THREE.Vector3()) {
    const d = sub(p, this.origin);
    return out.set(dot(d, this.ex), dot(d, this.ey), dot(d, this.ez));
  }
  dirToLaunch(d: V3 | THREE.Vector3, out = new THREE.Vector3()) {
    const a: V3 = Array.isArray(d) ? d : [d.x, d.y, d.z];
    return out.set(dot(a, this.ex), dot(a, this.ey), dot(a, this.ez));
  }
  dirToOrbit(d: V3 | THREE.Vector3, out = new THREE.Vector3()) {
    const a: V3 = Array.isArray(d) ? d : [d.x, d.y, d.z];
    return out.set(dot(a, this.ox), dot(a, this.oy), dot(a, this.oz));
  }
  /** Rotation matrices (body-fixed -> frame), as 4x4 for building orientations. */
  launchBasis() { return new THREE.Matrix4().set(...this.ex, 0, ...this.ey, 0, ...this.ez, 0, 0, 0, 0, 1); }
  orbitBasis() { return new THREE.Matrix4().set(...this.ox, 0, ...this.oy, 0, ...this.oz, 0, 0, 0, 0, 1); }

  /** The track at distance s along it: bed position, up and forward, in the launch frame. */
  trackAt(s: number, pos: THREE.Vector3, up?: THREE.Vector3, fwd?: THREE.Vector3) {
    const { ds, z } = this.meta.profile;
    const f = Math.min(Math.max(s / ds, 0), z.length - 1.0001), i = Math.floor(f), t = f - i;
    const zz = z[i] * (1 - t) + z[i + 1] * t;
    const x = this.meta.start[0] + this.fwd[0] * s, y = this.meta.start[1] + this.fwd[1] * s;
    const P = this.unit(x, y);
    this.toLaunch(scale(P, this.meta.R + zz), pos);
    if (up) this.dirToLaunch(P, up);
    if (fwd) {
      const slope = (z[i + 1] - z[i]) / ds;
      const H = this.tangent(x, y);
      this.dirToLaunch(norm([H[0] + P[0] * slope, H[1] + P[1] * slope, H[2] + P[2] * slope]), fwd);
    }
    return pos;
  }
}

/** The terrain mesh: positions in the launch frame, baked sunlight as vertex colours. */
export function terrainGeometry(site: Site, bin: ArrayBuffer) {
  const { u, v, zmin, zstep, R, start } = site.meta;
  const nu = u.length, nv = v.length, n = nu * nv;
  const hq = new Uint16Array(bin, 0, n), lit = new Uint8Array(bin, n * 2, n);
  const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), uv = new Float32Array(n * 2);
  const p = new THREE.Vector3();
  for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) {
    const k = j * nu + i;
    const x = start[0] + site.fwd[0] * u[i] + site.left[0] * v[j], y = start[1] + site.fwd[1] * u[i] + site.left[1] * v[j];
    site.toLaunch(scale(site.unit(x, y), R + zmin + hq[k] * zstep), p);
    pos.set([p.x, p.y, p.z], k * 3);
    const c = 0.02 + 0.98 * (lit[k] / 255);   // the shadows get only earthshine
    col.set([c, c, c], k * 3);
    uv.set([p.x / 23, p.z / 23], k * 2);
  }
  const idx = new Uint32Array((nu - 1) * (nv - 1) * 6);
  let m = 0;
  for (let j = 0; j < nv - 1; j++) for (let i = 0; i < nu - 1; i++) {
    const a = j * nu + i, b = a + 1, c = a + nu, d = c + 1;
    idx.set([a, c, b, b, c, d], m); m += 6;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  g.computeVertexNormals();
  // Winding: make the normals point up.
  const nrm = g.attributes.normal as THREE.BufferAttribute;
  if (nrm.getY(Math.floor(n / 2)) < 0) { idx.reverse(); g.index!.needsUpdate = true; g.computeVertexNormals(); }
  g.computeBoundingSphere();
  return g;
}

/** A tileable regolith texture: fine grain and small pits, drawn once on a canvas. */
export function regolithTexture(size = 512) {
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d")!;
  const img = ctx.createImageData(size, size);
  let seed = 11;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  // Periodic value noise, a few octaves.
  const oct = [4, 8, 16, 32, 64, 128].map((cells, o) => {
    const g = Array.from({ length: cells * cells }, rnd);
    return { cells, g, amp: 0.5 ** (o * 0.7) };
  });
  const f = new Float32Array(size * size);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    let s = 0;
    for (const { cells, g, amp } of oct) {
      const fx = (x / size) * cells, fy = (y / size) * cells, x0 = Math.floor(fx), y0 = Math.floor(fy);
      const tx = fx - x0, ty = fy - y0, sx = tx * tx * (3 - 2 * tx), sy = ty * ty * (3 - 2 * ty);
      const at = (i: number, j: number) => g[((j % cells) * cells) + (i % cells)];
      const a = at(x0, y0), b = at(x0 + 1, y0), cc = at(x0, y0 + 1), d = at(x0 + 1, y0 + 1);
      s += amp * (a + (b - a) * sx + (cc - a) * sy + (a - b - cc + d) * sx * sy);
    }
    f[y * size + x] = s;
  }
  // Small craters: a dark floor and a bright rim, wrapped at the edges.
  for (let k = 0; k < 140; k++) {
    const cx = rnd() * size, cy = rnd() * size, r = 2 + 18 * rnd() ** 3;
    for (let dy = -r * 1.4; dy <= r * 1.4; dy++) for (let dx = -r * 1.4; dx <= r * 1.4; dx++) {
      const d = Math.hypot(dx, dy) / r;
      if (d > 1.4) continue;
      const x = ((Math.round(cx + dx) % size) + size) % size, y = ((Math.round(cy + dy) % size) + size) % size;
      f[y * size + x] += d < 1 ? -0.25 * (1 - d * d) : 0.18 * (1.4 - d) / 0.4;
    }
  }
  let lo = Infinity, hi = -Infinity;
  for (const x of f) { lo = Math.min(lo, x); hi = Math.max(hi, x); }
  for (let i = 0; i < f.length; i++) {
    const g = Math.round(255 * (0.62 + 0.38 * (f[i] - lo) / (hi - lo)));
    img.data.set([g, g, g, 255], i * 4);
  }
  ctx.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/** The track: a bed and two rails swept along the profile, from s0 to s1. */
export function trackGeometry(site: Site, s0: number, s1: number, step = 10) {
  // Cross-section (lateral, up) offsets of the parts, as boxes: [half-width centre, width, bottom, top].
  const parts: [number, number, number, number][] = [[0, 2.4, -0.05, 0.07], [-0.45, 0.08, 0.07, 0.19], [0.45, 0.08, 0.07, 0.19]];
  const pos: number[] = [], idx: number[] = [];
  const p = new THREE.Vector3(), up = new THREE.Vector3(), fwd = new THREE.Vector3(), side = new THREE.Vector3();
  const rings: THREE.Vector3[][] = [];
  for (let s = s0; s <= s1 + 1e-6; s += step) {
    site.trackAt(Math.min(s, s1), p, up, fwd);
    side.crossVectors(fwd, up).normalize();     // to the right
    rings.push(parts.flatMap(([c, w, b, t]) => [[c - w / 2, b], [c + w / 2, b], [c + w / 2, t], [c - w / 2, t]].map(
      ([x, y]) => p.clone().addScaledVector(side, x).addScaledVector(up, y))));
  }
  for (const r of rings) for (const q of r) pos.push(q.x, q.y, q.z);
  const per = parts.length * 4;
  for (let k = 0; k < rings.length - 1; k++) for (let b = 0; b < parts.length; b++) for (let e = 0; e < 4; e++) {
    const a0 = k * per + b * 4 + e, a1 = k * per + b * 4 + ((e + 1) % 4), b0 = a0 + per, b1 = a1 + per;
    idx.push(a0, b0, a1, a1, b0, b1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}
