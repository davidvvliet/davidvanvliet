"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, useTexture } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { STARS, SPECTRAL_COLORS } from "../../components/solarSystemData";
import { createSunGlowTexture } from "../../components/sunShader";
import { moonFixedFromIcrf, raDecToFixed, skyAt } from "./sky";
import { Site, terrainGeometry, regolithTexture, trackGeometry, type TerrainMeta } from "./ground";
import styles from "./aether.module.css";

// The numbers are the spec's (scripts/blender/specs/aether.json): a flat shot off a 17.2 km track at
// 14 g reaches 2.176 km/s; half an orbit later, 7331 km over the north pole, the 20 N engine burns
// 59.5 m/s to lift the low point from the surface to 673 km; then the wings unfold.
// The site, the date and the ground are real (scripts/aether/terrain.py): LOLA terrain 17 km from the
// south pole, the Sun, the Earth and the stars where they stand on 5 January 2028, 00:00 UTC.
const G0 = 9.80665;
const GM = 4.9e12;                       // m^3/s^2 (NSSDCA)
const R = 1737.4e3;                      // m
const R_A = R + 7331e3;                  // aposelene radius
const R_P = R + 673e3;                   // target periselene radius
const ACC = 14 * G0;
const G_MOON = GM / (R * R);
const V = Math.sqrt((2 * GM * R_A) / (R * (R + R_A)));  // the flat shot's speed
const TRACK = (V * V) / (2 * ACC);
const T_SHOT = V / ACC;                  // 15.8 s, shown in real time
const SEP = 4;                           // after the track's end
const COAST = 12;                        // 4.9 h, shown in 12 s
const BURN = 8;                          // 893 s, shown in 8 s
const REVEAL = 4;
const ACT = 13;
const DV = 59.5;
const BURN_S = 893;
const COAST_H = 4.9;
const SUN_DIST = 1e8;                    // where the Sun's disc is drawn (m), well inside the far plane
const STAR_DIST = 2e8;

const P_COAST = T_SHOT + SEP, P_BURN = P_COAST + COAST, P_REVEAL = P_BURN + BURN;
const P_ACT = P_REVEAL + REVEAL, TOTAL = P_ACT + ACT;
// Mission time in seconds at scene time t: real during the shot, the coast and burn sped up.
const missionSeconds = (t: number) =>
  t < P_COAST ? t
    : t < P_BURN ? P_COAST + ((t - P_COAST) / COAST) * COAST_H * 3600
      : t < P_REVEAL ? P_COAST + COAST_H * 3600 + ((t - P_BURN) / BURN) * BURN_S
        : P_COAST + COAST_H * 3600 + BURN_S + (t - P_REVEAL);

// Sled parts leave the craft at the track's end; the model's own short rails are replaced by the long track.
const SLED = ["sep_ring_lower", "pusher", "sled_base", "shoe0", "shoe1", "shoe2", "shoe3", "armature"];
const MODEL_TRACK = ["rail0", "rail1", "stator"];
const RAIL_TOP = 0.19;                   // ground.ts trackGeometry: the rails' top above the bed

type Hinge = { node: THREE.Object3D; axis: THREE.Vector3; rest: THREE.Quaternion; restDeg: number };
type Ui = { phase: string; caption: string; readout: string };
type Ground = { site: Site; bin: ArrayBuffer };

const ease = (u: number) => { const c = Math.min(1, Math.max(0, u)); return c * c * (3 - 2 * c); };
const shot = { a: (R + R_A) / 2, e: (R_A - R) / (R_A + R) };
const target = { a: (R_P + R_A) / 2, e: (R_A - R_P) / (R_A + R_P) };
// Orbit frame: periselene (the track's end) at -y, moving +x, so the high point is over the north pole.
const orbitPoint = (o: { a: number; e: number }, nu: number) => {
  const r = (o.a * (1 - o.e * o.e)) / (1 + o.e * Math.cos(nu));
  return new THREE.Vector3(r * Math.sin(nu), -r * Math.cos(nu), 0);
};
const trueAnomaly = (M: number, e: number) => {
  let E = M + e * Math.sin(M);
  for (let i = 0; i < 12; i++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
  return 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2));
};
const km = (m: number) => Math.round(m / 1000).toLocaleString("en-US");
const utc = (jd: number) => new Date((jd - 2440587.5) * 86400e3).toISOString().slice(0, 16).replace("T", " ");

function orbitLine(o: { a: number; e: number }, from: number, to: number, color: string, opacity: number) {
  const pts = Array.from({ length: 241 }, (_, i) => orbitPoint(o, from + ((to - from) * i) / 240));
  const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
  line.frustumCulled = false;
  return line;
}

// Body-fixed axes (x lon 0, y lon 90 E, z north) -> a three.js sphere's own axes (lon 0 at +x, north +y,
// lon 90 E at -z), the layout of an equirectangular map centred on longitude 0.
const SPHERE_FROM_FIXED = new THREE.Matrix4().set(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1);
const FIXED_FROM_SPHERE = SPHERE_FROM_FIXED.clone().invert();
// Earth's rotation: Greenwich mean sidereal time, as SolarSystem.tsx uses.
const gmstDeg = (jd: number) => 280.46061837 + 360.98564736629 * (jd - 2451545.0);
const MOON_SPIN_DEG_PER_DAY = 13.17635815; // NAIF pck00011 BODY301_PM

function stars(site: Site, jd: number, frame: "launch" | "orbit") {
  const R0 = moonFixedFromIcrf(jd);
  const groups = new THREE.Group();
  // Three sizes by magnitude: brighter stars are bigger dots.
  for (const [lo, hi, px] of [[-2, 1, 3.4], [1, 2.5, 2.3], [2.5, 9, 1.5]] as const) {
    const pos: number[] = [], col: number[] = [];
    const c = new THREE.Color();
    for (const s of STARS) {
      if (s.magnitude < lo || s.magnitude >= hi) continue;
      const d = raDecToFixed(s.raDeg, s.decDeg, R0);
      const v = frame === "launch" ? site.dirToLaunch(d) : site.dirToOrbit(d);
      v.multiplyScalar(STAR_DIST);
      pos.push(v.x, v.y, v.z);
      c.set(SPECTRAL_COLORS[s.spectral]);
      col.push(c.r, c.g, c.b);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    const p = new THREE.Points(g, new THREE.PointsMaterial({ size: px, sizeAttenuation: false, vertexColors: true }));
    p.frustumCulled = false;
    groups.add(p);
  }
  return groups;
}

function Scene({ start, onDone, ui, ground }: { start: number | null; onDone: () => void; ui: (u: Ui) => void; ground: Ground }) {
  const gltf = useGLTF("/models/aether.glb");
  const [moonMap, earthMap] = useTexture(["/moon.jpg", "/models/aether-launch/earth.jpg"]);
  const { camera } = useThree();
  const controls = useRef<OrbitControlsImpl>(null);
  const { site, bin } = ground;
  const JD0 = site.meta.jd;

  // The craft, with the sled split off into its own group and the joints found.
  const { craft, sled, hinges, lift } = useMemo(() => {
    const craft = gltf.scene.clone(true);
    craft.updateMatrixWorld(true);
    // The model's own rail tops, so the shoes sit on the long track's rails.
    const rails = new THREE.Box3();
    for (const n of ["rail0", "rail1"]) { const o = craft.getObjectByName(n); if (o) rails.union(new THREE.Box3().setFromObject(o)); }
    const lift = RAIL_TOP - (rails.isEmpty() ? -0.53 : rails.max.y);
    const sled = new THREE.Group();
    for (const n of SLED) { const o = craft.getObjectByName(n); if (o) sled.attach(o); }
    for (const n of MODEL_TRACK) { const o = craft.getObjectByName(n); if (o) o.visible = false; }
    const byName = new Map<string, Hinge>();
    craft.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) o.castShadow = o.receiveShadow = true;
      const u = o.userData;
      if (!Array.isArray(u.joint_axis)) return;
      byName.set(o.name, { node: o, axis: new THREE.Vector3(u.joint_axis[0], u.joint_axis[2], -u.joint_axis[1]).normalize(),
        rest: o.quaternion.clone(), restDeg: typeof u.angle_deg === "number" ? u.angle_deg : 0 });
    });
    sled.traverse((o) => { if ((o as THREE.Mesh).isMesh) o.castShadow = o.receiveShadow = true; });
    // Unfolding order: the yoke, the first panel, then the others outward.
    const order = (s: string) => [`yoke_${s}_j`, ...[0, 1, 2, 3, 4].map((n) => `panel_${s}${n}_j`)];
    const left = order("l"), right = order("r");
    const hinges = left.map((n, i) => [byName.get(n), byName.get(right[i])].filter((h): h is Hinge => !!h));
    return { craft, sled, hinges, lift };
  }, [gltf]);

  // The ground: terrain, the track, and a post every 500 m beside it.
  const { terrain, track, posts, heights } = useMemo(() => {
    const regolith = regolithTexture();
    const terrain = new THREE.Mesh(terrainGeometry(site, bin),
      // Earthshine: the shadows are never quite black (a faint glow, independent of the baked sunlight).
      new THREE.MeshStandardMaterial({ color: "#a9a49c", map: regolith, vertexColors: true, roughness: 1, metalness: 0, shadowSide: THREE.DoubleSide,
        emissive: "#15171b", emissiveMap: regolith }));
    terrain.receiveShadow = true; terrain.castShadow = true;   // the ridges shade the craft through the shadow map
    terrain.frustumCulled = false;
    const track = new THREE.Mesh(trackGeometry(site, -20, TRACK + 20),
      new THREE.MeshStandardMaterial({ color: "#5a5a5a", metalness: 0.5, roughness: 0.5 }));
    track.receiveShadow = true; track.castShadow = true;
    const n = Math.floor(TRACK / 500) + 1;
    const posts = new THREE.InstancedMesh(new THREE.BoxGeometry(0.2, 2, 0.2), new THREE.MeshStandardMaterial({ color: "#bbbbbb" }), n * 2);
    const p = new THREE.Vector3(), up = new THREE.Vector3(), fwd = new THREE.Vector3(), side = new THREE.Vector3(), m = new THREE.Matrix4();
    for (let i = 0; i < n; i++) {
      site.trackAt(i * 500, p, up, fwd); side.crossVectors(fwd, up).normalize();
      for (const k of [0, 1]) {
        m.makeBasis(fwd, up, side).setPosition(p.clone().addScaledVector(side, k ? 3.5 : -3.5).addScaledVector(up, 1));
        posts.setMatrixAt(i * 2 + k, m);
      }
    }
    posts.castShadow = posts.receiveShadow = true; posts.frustumCulled = false;
    const nu = site.meta.u.length, nv = site.meta.v.length;
    const heights = new Uint16Array(bin, 0, nu * nv);
    return { terrain, track, posts, heights };
  }, [site, bin]);

  // Terrain height (above the 1737.4 km sphere) at a point given along (u) and across (v, left) the track.
  const terrainZ = useMemo(() => {
    const { u, v, zmin, zstep } = site.meta, nu = u.length;
    const find = (a: number[], x: number) => {
      let lo = 0, hi = a.length - 2;
      if (x <= a[0]) return [0, 0] as const;
      if (x >= a[a.length - 1]) return [a.length - 2, 1] as const;
      while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (a[mid] <= x) lo = mid; else hi = mid - 1; }
      return [lo, (x - a[lo]) / (a[lo + 1] - a[lo])] as const;
    };
    return (uu: number, vv: number) => {
      const [i, ti] = find(u, uu), [j, tj] = find(v, vv);
      const h = (jj: number, ii: number) => zmin + heights[jj * nu + ii] * zstep;
      return (h(j, i) * (1 - ti) + h(j, i + 1) * ti) * (1 - tj) + (h(j + 1, i) * (1 - ti) + h(j + 1, i + 1) * ti) * tj;
    };
  }, [site, heights]);
  // The ground's height in the launch frame below a point (x, z): terrain less the frame's origin and the Moon's curve.
  const groundY = (x: number, z: number) => terrainZ(x, -z) - site.meta.profile.z[0] - (x * x + z * z) / (2 * R);

  const lines = useMemo(() => ({
    shotPath: orbitLine(shot, 0, Math.PI, "#ffffff", 0.5),
    target: orbitLine(target, 0, 2 * Math.PI, "#ffb347", 0.9),
  }), []);
  const starsLaunch = useMemo(() => stars(site, JD0, "launch"), [site, JD0]);
  const starsOrbit = useMemo(() => stars(site, JD0, "orbit"), [site, JD0]);
  const sunSprite = useMemo(() => {
    const disc = 0.08;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: createSunGlowTexture(disc), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
    // A white core the size of the real disc (0.53 deg) under the glow.
    const core = new THREE.Sprite(new THREE.SpriteMaterial({ color: "#fffaf0", depthWrite: false }));
    const g = new THREE.Group(); g.add(core, s);
    const discSize = 2 * SUN_DIST * Math.tan(THREE.MathUtils.degToRad(0.265));
    core.scale.setScalar(discSize * 0.9); s.scale.setScalar(discSize / disc);
    g.renderOrder = -1;
    return g;
  }, []);
  useEffect(() => { for (const t of [moonMap, earthMap]) { t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; t.needsUpdate = true; } }, [moonMap, earthMap]);

  const launchSet = useRef<THREE.Group>(null);
  const moon = useRef<THREE.Mesh>(null);
  const earth = useRef<THREE.Mesh>(null);
  const orbit = useRef<THREE.Group>(null);
  const marker = useRef<THREE.Mesh>(null);
  const plume = useRef<THREE.Mesh>(null);
  const craftRef = useRef<THREE.Group>(null);
  const sledRef = useRef<THREE.Group>(null);
  const sun = useRef<THREE.DirectionalLight>(null);
  const earthshine = useRef<THREE.DirectionalLight>(null);
  const last = useRef("");
  const done = useRef(false);
  const shotKey = useRef("");     // the planned shot now showing
  const touched = useRef(false);  // the viewer has turned or zoomed since that shot began
  const q = useMemo(() => new THREE.Quaternion(), []);
  const tmp = useMemo(() => new THREE.Vector3(), []);
  const shift = useMemo(() => new THREE.Vector3(), []);
  const v = useMemo(() => ({ pos: new THREE.Vector3(), up: new THREE.Vector3(), fwd: new THREE.Vector3(), side: new THREE.Vector3(),
    sun: new THREE.Vector3(), earth: new THREE.Vector3(), m: new THREE.Matrix4(), m2: new THREE.Matrix4() }), []);

  useEffect(() => {
    const ctl = controls.current;
    // Before launch: behind and to the left of the craft, as the launch shot will be, looking down the track.
    camera.position.set(14, 4, -7);
    if (!ctl) return;
    ctl.minDistance = 2; ctl.maxDistance = 500;
    ctl.target.set(0, 1.5, 0); ctl.update();
    const grab = () => { touched.current = true; };
    ctl.addEventListener("start", grab);
    return () => ctl.removeEventListener("start", grab);
  }, [camera, site, v]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { done.current = false; shotKey.current = ""; }, [start]);
  // R3F sets the shadow camera's box and range as props but leaves its projection stale.
  useEffect(() => { sun.current?.shadow.camera.updateProjectionMatrix(); }, []);

  // A launch-frame point in the body-fixed frame.
  const fixedOf = (p: THREE.Vector3) => {
    const o = site.origin;
    return [o[0] + site.ex[0] * p.x + site.ey[0] * p.y + site.ez[0] * p.z,
      o[1] + site.ex[1] * p.x + site.ey[1] * p.y + site.ez[1] * p.z,
      o[2] + site.ex[2] * p.x + site.ey[2] * p.y + site.ez[2] * p.z] as const;
  };
  const heightAt = (p: THREE.Vector3) => Math.hypot(...fixedOf(p)) - R;
  useFrame(() => {
    const running = start !== null;
    const t = running ? Math.min(TOTAL, performance.now() / 1000 - start) : 0;
    const c = craftRef.current, sl = sledRef.current;
    if (!c || !sl || !launchSet.current || !moon.current || !earth.current || !orbit.current || !marker.current || !plume.current || !sun.current) return;
    const local = t < P_COAST, orbitView = (t >= P_COAST && t < P_BURN) || (t >= P_REVEAL && t < P_ACT);
    launchSet.current.visible = local;
    sl.visible = local;
    starsLaunch.visible = local; starsOrbit.visible = !local;
    moon.current.visible = !local;
    orbit.current.visible = orbitView;
    c.visible = !orbitView;
    plume.current.visible = t >= P_BURN && t < P_REVEAL;

    // The sky at this moment, in this view's frame.
    const jd = JD0 + missionSeconds(t) / 86400;
    const sky = skyAt(jd, JD0);
    const toFrame = (d: THREE.Vector3, out: THREE.Vector3) => (local ? site.dirToLaunch(d, out) : site.dirToOrbit(d, out));
    toFrame(sky.sun.clone().normalize(), v.sun);
    // The Earth: its centre from the Moon's (km -> m), less the launch frame's origin; turned by its sidereal time.
    const e = sky.earth.clone().multiplyScalar(1000);
    if (local) site.toLaunch([e.x, e.y, e.z], earth.current.position);
    else site.dirToOrbit(e, earth.current.position);
    const basis = local ? site.launchBasis() : site.orbitBasis();
    v.m.copy(basis).multiply(moonFixedFromIcrf(JD0)).multiply(v.m2.makeRotationZ(THREE.MathUtils.degToRad(gmstDeg(jd)))).multiply(FIXED_FROM_SPHERE);
    earth.current.quaternion.setFromRotationMatrix(v.m);
    if (earthshine.current) { toFrame(sky.earth.clone().normalize(), earthshine.current.position).multiplyScalar(1e4); }
    // The Moon (orbit views): the body-fixed frame of the launch, turned by its spin since.
    v.m.copy(site.orbitBasis()).multiply(v.m2.makeRotationZ(THREE.MathUtils.degToRad(MOON_SPIN_DEG_PER_DAY * (jd - JD0)))).multiply(FIXED_FROM_SPHERE);
    moon.current.quaternion.setFromRotationMatrix(v.m);

    // Wings: folded until activation, then unfolded hinge by hinge.
    const a = t - P_ACT;
    const spans = [[1.5, 3.5], [3.5, 5.5], [5.5, 6.7], [6.7, 7.9], [7.9, 9.1], [9.1, 10.3]];
    hinges.forEach((pair, i) => {
      const u = ease((a - spans[i][0]) / (spans[i][1] - spans[i][0]));
      for (const h of pair) h.node.quaternion.copy(q.setFromAxisAngle(h.axis, THREE.MathUtils.degToRad(-h.restDeg * u)).multiply(h.rest));
    });

    let u: Ui;
    // Each shot opens on its planned view. Once the viewer turns or zooms, only the point the
    // camera circles follows the craft (the camera moves with it), so their angle and zoom stay.
    const ctl = controls.current;
    const cam = (key: string, pos: THREE.Vector3, look: THREE.Vector3, min: number, max: number) => {
      if (!running || t >= TOTAL || !ctl) return;
      if (key !== shotKey.current) {
        shotKey.current = key; touched.current = false;
        ctl.minDistance = min; ctl.maxDistance = max;
      }
      if (touched.current) camera.position.add(shift.copy(look).sub(ctl.target));
      else camera.position.copy(pos);
      ctl.target.copy(look); ctl.update();
    };
    if (local) {
      // On the track: the bed's position, up and forward; then free flight off its end.
      let xs: number;
      if (t < T_SHOT) {
        const s = 0.5 * ACC * t * t; xs = s;
        site.trackAt(s, v.pos, v.up, v.fwd);
        u = { phase: "Launch", caption: "On the mass driver 17 km from the south pole: 14 g along a 17.2 km track, cut and banked through the real terrain.",
          readout: `UTC    ${utc(jd)}\nspeed  ${((ACC * t) / 1000).toFixed(3)} km/s\naccel  14 g\ntrack  ${(s / 1000).toFixed(1)} / ${(TRACK / 1000).toFixed(1)} km` };
      } else {
        const tau = t - T_SHOT;
        // Off the end: along the last stretch of track, falling at lunar gravity (the ground falls away faster).
        v.pos.copy(site.exitPos).addScaledVector(site.exitFwd, V * tau).addScaledVector(site.exitUp, -0.5 * G_MOON * tau * tau);
        v.up.copy(site.exitUp); v.fwd.copy(site.exitFwd);
        const tb = Math.min(tau, V / (30 * G0));
        xs = TRACK + V * tb - 0.5 * 30 * G0 * tb * tb;
        const above = heightAt(v.pos) - terrainZ(v.pos.x, -v.pos.z);
        u = { phase: "Separation", caption: "Off the end of the track at 2.18 km/s. The sled brakes; the craft flies on, and the ground curves away beneath it.",
          readout: `UTC    ${utc(jd)}\nspeed  ${(V / 1000).toFixed(3)} km/s\nheight ${Math.max(0, above).toFixed(0)} m` };
      }
      // Craft: its +x along the track, +y up, lifted so its shoes sit on the rails.
      v.side.crossVectors(v.fwd, v.up).normalize();
      v.m.makeBasis(v.fwd, v.up, v.side);
      c.quaternion.setFromRotationMatrix(v.m);
      c.position.copy(v.pos).addScaledVector(v.up, lift);
      site.trackAt(Math.min(xs, TRACK), tmp, v.up, v.fwd);
      v.side.crossVectors(v.fwd, v.up).normalize();
      sl.quaternion.setFromRotationMatrix(v.m.makeBasis(v.fwd, v.up, v.side));
      sl.position.copy(tmp).addScaledVector(v.up, lift);
      // Chase camera: behind and to the left, looking past the craft toward the Earth.
      const back = t < T_SHOT ? 1 : 1 + (t - T_SHOT) * 1.5;
      const look = c.position.clone().addScaledVector(v.fwd, 2).addScaledVector(v.up, 0.8);
      const camPos = c.position.clone().addScaledVector(v.fwd, -9 * back).addScaledVector(v.up, 2.2 * back).addScaledVector(v.side, -6.5 * back);
      camPos.y = Math.max(camPos.y, groundY(camPos.x, camPos.z) + 1.5);   // never inside a cutting's wall
      cam("track", camPos, look, 2, 500);
      // The Sun's shadow camera rides with the craft.
      sun.current.target.position.copy(c.position);
      sun.current.position.copy(c.position).addScaledVector(v.sun, 59000);
    } else if (orbitView) {
      const coast = t < P_BURN;
      const f = coast ? (t - P_COAST) / COAST : 1;
      const nu = trueAnomaly(Math.PI * f, shot.e);
      const p = f >= 1 ? new THREE.Vector3(0, R_A, 0) : orbitPoint(shot, nu);
      marker.current.position.copy(p);
      (lines.target.material as THREE.LineBasicMaterial).opacity = coast ? 0.25 : 0.95;
      (lines.shotPath.material as THREE.LineBasicMaterial).opacity = coast ? 0.6 : 0.2;
      const r = p.length(), vel = Math.sqrt(GM * (2 / r - 1 / shot.a));
      u = coast
        ? { phase: "Coast", caption: "Coasting half an orbit, 4.9 hours, up to 7,331 km over the north pole.",
            readout: `UTC    ${utc(jd)}\nT+     ${(COAST_H * f).toFixed(1)} h\nheight ${km(r - R)} km\nspeed  ${(vel / 1000).toFixed(2)} km/s` }
        : { phase: "In orbit", caption: "The low point is lifted from the surface to 673 km: the relay's orbit.",
            readout: "orbit  673 × 7,331 km\nperiod 10.8 h" };
      cam(coast ? "coast" : "in orbit", tmp.set(0, 3.0e6, 2.8e7), new THREE.Vector3(0, 3.0e6, 0), 2.5e6, 1e8);
      sun.current.target.position.set(0, 0, 0);
      sun.current.position.copy(v.sun).multiplyScalar(1e7);
    } else {
      // At the high point: dish (+y) toward the Moon below, engine firing along the motion (-x).
      c.position.set(0, R_A, 0); c.rotation.set(0, 0, Math.PI);
      const burn = t < P_REVEAL;
      if (burn) {
        const f = (t - P_BURN) / BURN;
        const m = plume.current.material as THREE.MeshBasicMaterial;
        m.opacity = 0.25 + 0.1 * Math.sin(t * 40);
        u = { phase: "Orbit insertion", caption: "At the high point the 20 N engine burns 59.5 m/s, lifting the orbit's low point from the surface to 673 km.",
          readout: `Δv     ${(DV * f).toFixed(1)} / ${DV} m/s\nburn   ${Math.round(BURN_S * f)} / ${BURN_S} s` };
        // From above, looking down past the craft at the Moon 7,331 km below.
        const ang = 0.5 + 0.1 * (t - P_BURN);
        cam("burn", tmp.set(4 * Math.cos(ang), R_A + 10, 4 * Math.sin(ang)), new THREE.Vector3(0, R_A - 2, 0), 2, 2e7);
      } else {
        const step = a < 1.5 ? "The hold-downs release." : a < 10.3 ? "The wings unfold: the yoke, then the panels, one by one."
          : "Wings out, 663 W. The S-band dish looks down at the Moon; the X-band panel turns to the Earth.";
        u = { phase: "Activation", caption: step, readout: "orbit  673 × 7,331 km\nwings  2 × 5 panels" };
        // From the sunward side, so the unfolding wings are lit.
        const dir = v.sun.clone().multiplyScalar(0.8).add(tmp.set(0, -0.5, 0.6)).normalize();
        cam("activation", dir.multiplyScalar(15).add(new THREE.Vector3(0, R_A, 0)), new THREE.Vector3(0, R_A, 0), 2, 2e7);
      }
      sun.current.target.position.copy(c.position);
      sun.current.position.copy(c.position).addScaledVector(v.sun, 1500);
    }
    sun.current.target.updateMatrixWorld();
    sunSprite.position.copy(camera.position).addScaledVector(v.sun, SUN_DIST);
    const key = u.phase + u.caption + u.readout;
    if (key !== last.current) { last.current = key; ui(running ? u : { phase: "", caption: "", readout: "" }); }

    if (ctl && running && t >= TOTAL && !done.current) {
      done.current = true;
      c.getWorldPosition(tmp); camera.position.add(shift.copy(tmp).sub(ctl.target)); ctl.target.copy(tmp);
      onDone();
    }
    if (!running) {
      // Idle: on the track at its start, lit as it is there.
      site.trackAt(0, v.pos, v.up, v.fwd);
      v.side.crossVectors(v.fwd, v.up).normalize();
      v.m.makeBasis(v.fwd, v.up, v.side);
      c.quaternion.setFromRotationMatrix(v.m); sl.quaternion.copy(c.quaternion);
      c.position.copy(v.pos).addScaledVector(v.up, lift); sl.position.copy(c.position);
      sun.current.target.position.copy(c.position); sun.current.target.updateMatrixWorld();
      sun.current.position.copy(c.position).addScaledVector(v.sun, 59000);
    }
  });

  return (
    <>
      <ambientLight intensity={0.03} />
      <directionalLight ref={earthshine} intensity={0.12} color="#cfdcff" />
      <directionalLight ref={sun} intensity={3.2} castShadow
        shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-bias={-0.000001} shadow-normalBias={0.04}
        shadow-camera-left={-8} shadow-camera-right={8} shadow-camera-top={8} shadow-camera-bottom={-8}
        shadow-camera-near={1} shadow-camera-far={60000} />
      <primitive object={starsLaunch} />
      <primitive object={starsOrbit} />
      <primitive object={sunSprite} />
      <group ref={launchSet}>
        <primitive object={terrain} />
        <primitive object={track} />
        <primitive object={posts} />
      </group>
      <mesh ref={moon}>
        <sphereGeometry args={[R, 128, 64]} />
        <meshStandardMaterial map={moonMap} roughness={1} />
      </mesh>
      <mesh ref={earth}>
        <sphereGeometry args={[6371e3, 96, 48]} />
        <meshStandardMaterial map={earthMap} roughness={0.8} />
      </mesh>
      <group ref={orbit}>
        <primitive object={lines.shotPath} />
        <primitive object={lines.target} />
        <mesh ref={marker}>
          <sphereGeometry args={[90e3, 16, 8]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
      </group>
      <group ref={craftRef}>
        <primitive object={craft} />
        <mesh ref={plume} position={[0.055 - 0.45, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <coneGeometry args={[0.14, 0.9, 24, 1, true]} />
          <meshBasicMaterial color="#cfe3ff" transparent opacity={0.3} depthWrite={false} blending={THREE.AdditiveBlending} side={THREE.DoubleSide} />
        </mesh>
      </group>
      <group ref={sledRef}><primitive object={sled} /></group>
      <OrbitControls ref={controls} makeDefault enablePan={false} />
    </>
  );
}

export default function AetherLaunch() {
  const [start, setStart] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [ui, setUi] = useState<Ui>({ phase: "", caption: "", readout: "" });
  const [ground, setGround] = useState<Ground | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all([
      fetch("/models/aether-launch/terrain.json").then((r) => r.json() as Promise<TerrainMeta>),
      fetch("/models/aether-launch/terrain.bin").then((r) => r.arrayBuffer()),
    ]).then(([meta, bin]) => { if (live) setGround({ site: new Site(meta), bin }); });
    return () => { live = false; };
  }, []);
  return (
    <div className={styles.page}>
      <Canvas className={styles.canvas} shadows gl={{ logarithmicDepthBuffer: true, antialias: true }}
        camera={{ fov: 40, near: 0.05, far: 5e8, position: [-16, 11, -13] }}>
        <Suspense fallback={null}>
          {ground && <Scene start={start} ui={setUi} ground={ground} onDone={() => setRunning(false)} />}
        </Suspense>
      </Canvas>
      <div className={styles.title}>Altair Aether</div>
      {ui.phase && (
        <div className={styles.phase}>
          <div className={styles.phaseName}>{ui.phase}</div>
          <div className={styles.caption}>{ui.caption}</div>
          <div className={styles.readout}>{ui.readout}</div>
        </div>
      )}
      <button className={styles.launch} disabled={running || !ground}
        onClick={() => { setStart(performance.now() / 1000); setRunning(true); }}>
        Launch
      </button>
    </div>
  );
}
