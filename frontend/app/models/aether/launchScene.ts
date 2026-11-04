import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import type { SceneExtension, SceneHandles } from "../../components/SolarSystem";
import { moonSceneQuaternion, SCENE_FROM_FIXED } from "../../components/moonOrientation";
import { Site, terrainGeometry, regolithTexture, trackGeometry, SINK } from "./ground";

// Altair Aether's launch, placed into the site's solar-system scene: the Sun, the Earth, the Moon and the
// stars are that scene's own, on the launch date. This adds the ground around the track (fixed to the
// Moon, turning with it), the craft and its flight, the lights, and the camera's shots.
// The numbers are the spec's (scripts/blender/specs/aether.json): a flat shot off a 17.2 km track at
// 14 g reaches 2.176 km/s; half an orbit later, 7331 km over the north pole, the 20 N engine burns
// 59.5 m/s to lift the low point from the surface to 673 km; then the wings unfold.
const G0 = 9.80665;
const GM = 4.9e12;                       // m^3/s^2 (NSSDCA)
const R = 1737.4e3;                      // m
const R_A = R + 7331e3;                  // aposelene radius
const R_P = R + 673e3;                   // target periselene radius
const ACC = 14 * G0;
const G_MOON = GM / (R * R);
const V = Math.sqrt((2 * GM * R_A) / (R * (R + R_A)));  // the flat shot's speed
export const TRACK = (V * V) / (2 * ACC);
const T_SHOT = V / ACC;                  // 15.8 s, shown in real time
const SEP = 4;                           // after the track's end
const COAST = 12;                        // 4.9 h, shown in 12 s
const BURN = 8;                          // 893 s, shown in 8 s
const REVEAL = 4;
const ACT = 13;
const DV = 59.5;
const BURN_S = 893;
const COAST_H = 4.9;

const P_COAST = T_SHOT + SEP, P_BURN = P_COAST + COAST, P_REVEAL = P_BURN + BURN;
const P_ACT = P_REVEAL + REVEAL, TOTAL = P_ACT + ACT;
// Mission time in seconds at scene time t: real during the shot, the coast and burn sped up.
const missionSeconds = (t: number) =>
  t < P_COAST ? t
    : t < P_BURN ? P_COAST + ((t - P_COAST) / COAST) * COAST_H * 3600
      : t < P_REVEAL ? P_COAST + COAST_H * 3600 + ((t - P_BURN) / BURN) * BURN_S
        : P_COAST + COAST_H * 3600 + BURN_S + (t - P_REVEAL);

// Sled parts leave the craft at the track's end; the model's own short rails are replaced by the long track.
const SLED = ["sep_ring_lower", "pusher", "sled_lettering", "sled_base", "shoe0", "shoe1", "shoe2", "shoe3", "armature"];
const MODEL_TRACK = ["rail0", "rail1", "stator"];
const RAIL_TOP = 0.19;                   // ground.ts trackGeometry: the rails' top above the bed

type Hinge = { node: THREE.Object3D; axis: THREE.Vector3; rest: THREE.Quaternion; restDeg: number };
export type LaunchUi = { phase: string; caption: string; readout: string };

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

/** A frame given in the Moon's body-fixed axes (metres), as a matrix in a Moon-aligned scene object. */
function frameMatrix(origin: number[], ax: number[], ay: number[], az: number[], unitsPerM: number) {
  const v = (a: number[]) => new THREE.Vector3(a[0], a[1], a[2]).applyMatrix4(SCENE_FROM_FIXED);
  const m = new THREE.Matrix4().makeBasis(v(ax), v(ay), v(az));
  m.scale(new THREE.Vector3(unitsPerM, unitsPerM, unitsPerM));
  const o = v(origin).multiplyScalar(unitsPerM);
  return m.setPosition(o);
}

export type AetherLaunch = SceneExtension & { start(): void };

const Y = new THREE.Vector3(0, 1, 0);
function setUp(camera: THREE.Camera, controls: SceneHandles["controls"], up: THREE.Vector3) {
  camera.up.copy(up);
  const c = controls as unknown as { _quat: THREE.Quaternion; _quatInverse: THREE.Quaternion };
  c._quat.setFromUnitVectors(camera.up, Y);
  c._quatInverse.copy(c._quat).invert();
}

export function aetherLaunch(site: Site, bin: ArrayBuffer, on: { ui(u: LaunchUi): void; done(): void }): AetherLaunch {
  const JD0 = site.meta.jd;
  let startAt: number | null = null;
  const sceneTime = () => (startAt === null ? 0 : Math.min(TOTAL, performance.now() / 1000 - startAt));

  // The craft (filled in when the model arrives), the sled, the wing hinges.
  const craft = new THREE.Group(), sled = new THREE.Group(), model = new THREE.Group();
  craft.add(model);
  let hinges: Hinge[][] = [];
  let lift = RAIL_TOP + 0.53;
  const plume = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.9, 24, 1, true),
    new THREE.MeshBasicMaterial({ color: "#cfe3ff", transparent: true, opacity: 0.3, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
  plume.position.set(0.055 - 0.45, 0, 0); plume.rotation.set(0, 0, Math.PI / 2);
  craft.add(plume);

  // The ground: terrain, the track, and a post every 500 m beside it. In the launch frame (metres).
  const regolith = regolithTexture();
  const terrain = new THREE.Mesh(terrainGeometry(site, bin),
    // Earthshine: the shadows are never quite black (a faint glow, independent of the baked sunlight).
    // Matte (Lambert): regolith has no shine, and a specular lobe glares at a 1-degree Sun.
    new THREE.MeshLambertMaterial({ color: "#a9a49c", map: regolith, vertexColors: true, shadowSide: THREE.DoubleSide,
      emissive: "#15171b", emissiveMap: regolith }));
  terrain.receiveShadow = true; terrain.castShadow = true;   // the ridges shade the craft through the shadow map
  terrain.frustumCulled = false;
  const track = new THREE.Mesh(trackGeometry(site, -20, TRACK + 20),
    new THREE.MeshStandardMaterial({ color: "#5a5a5a", metalness: 0.5, roughness: 0.5 }));
  track.receiveShadow = true; track.castShadow = true; track.frustumCulled = false;
  const nPosts = Math.floor(TRACK / 500) + 1;
  const posts = new THREE.InstancedMesh(new THREE.BoxGeometry(0.2, 2, 0.2), new THREE.MeshStandardMaterial({ color: "#bbbbbb" }), nPosts * 2);
  {
    const p = new THREE.Vector3(), up = new THREE.Vector3(), fwd = new THREE.Vector3(), side = new THREE.Vector3(), m = new THREE.Matrix4();
    for (let i = 0; i < nPosts; i++) {
      site.trackAt(i * 500, p, up, fwd); side.crossVectors(fwd, up).normalize();
      for (const k of [0, 1]) {
        m.makeBasis(fwd, up, side).setPosition(p.clone().addScaledVector(side, k ? 3.5 : -3.5).addScaledVector(up, 1));
        posts.setMatrixAt(k + i * 2, m);
      }
    }
  }
  posts.castShadow = posts.receiveShadow = true; posts.frustumCulled = false;

  // Terrain height (above the 1737.4 km sphere) at a point given along (u) and across (v, left) the track.
  const { u: gu, v: gv, zmin, zstep } = site.meta, nu = gu.length;
  const heights = new Uint16Array(bin, 0, nu * gv.length);
  const find = (a: number[], x: number) => {
    let lo = 0, hi = a.length - 2;
    if (x <= a[0]) return [0, 0] as const;
    if (x >= a[a.length - 1]) return [a.length - 2, 1] as const;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (a[mid] <= x) lo = mid; else hi = mid - 1; }
    return [lo, (x - a[lo]) / (a[lo + 1] - a[lo])] as const;
  };
  const terrainZ = (uu: number, vv: number) => {
    const [i, ti] = find(gu, uu), [j, tj] = find(gv, vv);
    const h = (jj: number, ii: number) => zmin + heights[jj * nu + ii] * zstep;
    return (h(j, i) * (1 - ti) + h(j, i + 1) * ti) * (1 - tj) + (h(j + 1, i) * (1 - ti) + h(j + 1, i + 1) * ti) * tj;
  };
  // The ground's height in the launch frame below a point (x, z): terrain less the frame's origin and the Moon's curve.
  const groundY = (x: number, z: number) => terrainZ(x, -z) - site.meta.profile.z[0] - (x * x + z * z) / (2 * R);
  const fixedOf = (p: THREE.Vector3) => {
    const o = site.origin;
    return [o[0] + site.ex[0] * p.x + site.ey[0] * p.y + site.ez[0] * p.z,
      o[1] + site.ex[1] * p.x + site.ey[1] * p.y + site.ez[1] * p.z,
      o[2] + site.ex[2] * p.x + site.ey[2] * p.y + site.ez[2] * p.z] as const;
  };
  const heightAt = (p: THREE.Vector3) => Math.hypot(...fixedOf(p)) - R;

  // The orbit: the shot's path and the target orbit, with a marker for the craft (orbit frame, metres).
  const shotPath = orbitLine(shot, 0, Math.PI, "#ffffff", 0.5);
  const targetPath = orbitLine(target, 0, 2 * Math.PI, "#ffb347", 0.9);
  const marker = new THREE.Mesh(new THREE.SphereGeometry(90e3, 16, 8), new THREE.MeshBasicMaterial({ color: "#ffffff" }));
  const orbitSet = new THREE.Group();
  orbitSet.add(shotPath, targetPath, marker);

  // Frames: the launch frame turns with the Moon; the orbit frame is the body-fixed frame at the launch,
  // held still in space (it rides with the Moon's centre).
  const launchFrame = new THREE.Group(), orbitFrame = new THREE.Group();
  launchFrame.matrixAutoUpdate = false; orbitFrame.matrixAutoUpdate = false;
  const launchSet = new THREE.Group();
  launchSet.add(terrain, track, posts);
  launchFrame.add(launchSet, craft, sled);
  orbitFrame.add(orbitSet);

  // Light: the Sun (with the terrain's and the craft's shadows) and the Earth's glow, both from where they are.
  const sunLight = new THREE.DirectionalLight("#ffffff", 2.2);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(2048, 2048);
  sunLight.shadow.bias = -0.000001; sunLight.shadow.normalBias = 0.04;
  // The shadow box is in metres: the scene is drawn in metres around the camera (SolarSystem's renderRelative).
  Object.assign(sunLight.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 60000 });
  sunLight.shadow.camera.updateProjectionMatrix();
  const earthshine = new THREE.DirectionalLight("#cfdcff", 0.1);

  let h0: SceneHandles | null = null;
  let unitsPerM = 1;
  let saved: { geometry: THREE.BufferGeometry; material: THREE.Material | THREE.Material[]; ambient: number; shadows: boolean } | null = null;
  let litMoon: THREE.MeshStandardMaterial | null = null, sunkMoon: THREE.SphereGeometry | null = null;

  // Camera shots. Each opens on its planned view; once the viewer turns or zooms, only the point the
  // camera circles follows the craft (the camera moves with it), so their angle and zoom stay.
  let shotKey = "", touched = false, done = false, lastUi = "", placed = false;
  const grab = () => { touched = true; };
  const tmp = new THREE.Vector3(), shift = new THREE.Vector3(), q = new THREE.Quaternion();
  const v = { pos: new THREE.Vector3(), up: new THREE.Vector3(), fwd: new THREE.Vector3(), side: new THREE.Vector3(),
    sun: new THREE.Vector3(), m: new THREE.Matrix4(), cw: new THREE.Vector3(), ew: new THREE.Vector3() };

  return {
    start() { startAt = performance.now() / 1000; shotKey = ""; touched = false; done = false; },

    init(h) {
      h0 = h;
      unitsPerM = h.unitsPerKm / 1000;
      const { renderer, moon, controls } = h;
      saved = { geometry: moon.geometry, material: moon.material, ambient: h.ambient.intensity, shadows: renderer.shadowMap.enabled };
      // The Moon lit by the Sun, and sunk a little below the lowest ground here, so its sphere never
      // shows through the terrain; the terrain's edges come down to meet it.
      const map = (moon.material as THREE.MeshBasicMaterial).map;
      litMoon = new THREE.MeshStandardMaterial({ map, roughness: 1, metalness: 0 });
      moon.material = litMoon;
      sunkMoon = new THREE.SphereGeometry(h.moonRadius * (R + SINK) / R, 256, 128);
      moon.geometry = sunkMoon;
      h.ambient.intensity = 0.03;
      h.showOrbits(false);   // the planets' rings would cross the sky from the ground
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;

      launchFrame.matrix.copy(frameMatrix(site.origin, site.ex, site.ey, site.ez, unitsPerM));
      moon.add(launchFrame);
      orbitFrame.matrix.copy(frameMatrix([0, 0, 0], site.ox, site.oy, site.oz, unitsPerM))
        .premultiply(new THREE.Matrix4().makeRotationFromQuaternion(moonSceneQuaternion(JD0)));
      h.moonFrame.add(orbitFrame);
      h.scene.add(sunLight, sunLight.target, earthshine);

      new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).load("/models/aether.glb", (gltf) => {
        const root = gltf.scene;
        root.updateMatrixWorld(true);
        // The model's own rail tops, so the shoes sit on the long track's rails.
        const rails = new THREE.Box3();
        for (const n of ["rail0", "rail1"]) { const o = root.getObjectByName(n); if (o) rails.union(new THREE.Box3().setFromObject(o)); }
        lift = RAIL_TOP - (rails.isEmpty() ? -0.53 : rails.max.y);
        for (const n of SLED) { const o = root.getObjectByName(n); if (o) sled.attach(o); }
        for (const n of MODEL_TRACK) { const o = root.getObjectByName(n); if (o) o.visible = false; }
        const byName = new Map<string, Hinge>();
        root.traverse((o) => {
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
        hinges = left.map((n, i) => [byName.get(n), byName.get(right[i])].filter((x): x is Hinge => !!x));
        model.add(root);
      });

      controls.addEventListener("start", grab);
      controls.minDistance = 2 * unitsPerM; controls.maxDistance = 2e8 * unitsPerM;
    },

    clock() {
      return JD0 + missionSeconds(sceneTime()) / 86400;
    },

    frame(h, jd) {
      const { camera, controls } = h;
      const running = startAt !== null;
      const t = sceneTime();
      const local = t < P_COAST, orbitView = (t >= P_COAST && t < P_BURN) || (t >= P_REVEAL && t < P_ACT);
      launchSet.visible = local;
      sled.visible = local;
      orbitSet.visible = orbitView;
      craft.visible = !orbitView;
      plume.visible = t >= P_BURN && t < P_REVEAL;
      if (local && craft.parent !== launchFrame) launchFrame.add(craft);
      if (!local && craft.parent !== orbitFrame) orbitFrame.add(craft);
      launchFrame.updateWorldMatrix(true, false);
      orbitFrame.updateWorldMatrix(true, false);
      const frame = local ? launchFrame : orbitFrame;
      // The camera's up is the frame's up (the local vertical on the ground), not the solar system's north,
      // which at the south pole points into the ground. OrbitControls keeps its own copy of it.
      tmp.setFromMatrixColumn(frame.matrixWorld, 1).normalize();
      if (tmp.distanceToSquared(camera.up) > 1e-12) setUp(camera, controls, tmp);
      if (!placed) {
        // Before launch (the Moon is now turned to the launch date): in front of the craft at the track's start, looking back at it.
        placed = true;
        controls.target.copy(launchFrame.localToWorld(new THREE.Vector3(0, 1.5, 0)));
        camera.position.copy(launchFrame.localToWorld(new THREE.Vector3(14, 4, -7)));
      }

      // Wings: folded until activation, then unfolded hinge by hinge.
      const a = t - P_ACT;
      const spans = [[1.5, 3.5], [3.5, 5.5], [5.5, 6.7], [6.7, 7.9], [7.9, 9.1], [9.1, 10.3]];
      hinges.forEach((pair, i) => {
        const k = ease((a - spans[i][0]) / (spans[i][1] - spans[i][0]));
        for (const hg of pair) hg.node.quaternion.copy(q.setFromAxisAngle(hg.axis, THREE.MathUtils.degToRad(-hg.restDeg * k)).multiply(hg.rest));
      });

      const cam = (key: string, pos: THREE.Vector3, look: THREE.Vector3, min: number, max: number) => {
        // pos and look are in `frame`, in metres; min and max too.
        if (!running || t >= TOTAL) return;
        const lookW = frame.localToWorld(look.clone()), posW = frame.localToWorld(pos.clone());
        if (key !== shotKey) {
          shotKey = key; touched = false;
          controls.minDistance = min * unitsPerM; controls.maxDistance = max * unitsPerM;
        }
        if (touched) camera.position.add(shift.copy(lookW).sub(controls.target));
        else camera.position.copy(posW);
        controls.target.copy(lookW);
      };

      let u: LaunchUi = { phase: "", caption: "", readout: "" };
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
        if (!running) site.trackAt(0, v.pos, v.up, v.fwd);
        // Craft: its +x along the track, +y up, lifted so its shoes sit on the rails.
        v.side.crossVectors(v.fwd, v.up).normalize();
        v.m.makeBasis(v.fwd, v.up, v.side);
        craft.quaternion.setFromRotationMatrix(v.m);
        craft.position.copy(v.pos).addScaledVector(v.up, lift);
        site.trackAt(running ? Math.min(xs, TRACK) : 0, tmp, v.up, v.fwd);
        v.side.crossVectors(v.fwd, v.up).normalize();
        sled.quaternion.setFromRotationMatrix(v.m.makeBasis(v.fwd, v.up, v.side));
        sled.position.copy(tmp).addScaledVector(v.up, lift);
        // Chase camera: behind and to the left, looking past the craft toward the Earth.
        const back = t < T_SHOT ? 1 : 1 + (t - T_SHOT) * 1.5;
        const look = craft.position.clone().addScaledVector(v.fwd, 2).addScaledVector(v.up, 0.8);
        const camPos = craft.position.clone().addScaledVector(v.fwd, -9 * back).addScaledVector(v.up, 2.2 * back).addScaledVector(v.side, -6.5 * back);
        camPos.y = Math.max(camPos.y, groundY(camPos.x, camPos.z) + 1.5);   // never inside a cutting's wall
        cam("track", camPos, look, 2, 2e8);
      } else if (orbitView) {
        const coast = t < P_BURN;
        const f = coast ? (t - P_COAST) / COAST : 1;
        const nu = trueAnomaly(Math.PI * f, shot.e);
        const p = f >= 1 ? new THREE.Vector3(0, R_A, 0) : orbitPoint(shot, nu);
        marker.position.copy(p);
        craft.position.copy(p);
        (targetPath.material as THREE.LineBasicMaterial).opacity = coast ? 0.25 : 0.95;
        (shotPath.material as THREE.LineBasicMaterial).opacity = coast ? 0.6 : 0.2;
        const r = p.length(), vel = Math.sqrt(GM * (2 / r - 1 / shot.a));
        u = coast
          ? { phase: "Coast", caption: "Coasting half an orbit, 4.9 hours, up to 7,331 km over the north pole.",
              readout: `UTC    ${utc(jd)}\nT+     ${(COAST_H * f).toFixed(1)} h\nheight ${km(r - R)} km\nspeed  ${(vel / 1000).toFixed(2)} km/s` }
          : { phase: "In orbit", caption: "The low point is lifted from the surface to 673 km: the relay's orbit.",
              readout: "orbit  673 × 7,331 km\nperiod 10.8 h" };
        cam(coast ? "coast" : "in orbit", tmp.set(0, 3.0e6, 2.8e7), new THREE.Vector3(0, 3.0e6, 0), 2.5e6, 2e8);
      } else {
        // At the high point: dish (+y) toward the Moon below, engine firing along the motion (-x).
        craft.position.set(0, R_A, 0); craft.rotation.set(0, 0, Math.PI);
        if (t < P_REVEAL) {
          const f = (t - P_BURN) / BURN;
          (plume.material as THREE.MeshBasicMaterial).opacity = 0.25 + 0.1 * Math.sin(t * 40);
          u = { phase: "Orbit insertion", caption: "At the high point the 20 N engine burns 59.5 m/s, lifting the orbit's low point from the surface to 673 km.",
            readout: `Δv     ${(DV * f).toFixed(1)} / ${DV} m/s\nburn   ${Math.round(BURN_S * f)} / ${BURN_S} s` };
          // From above, looking down past the craft at the Moon 7,331 km below.
          const ang = 0.5 + 0.1 * (t - P_BURN);
          cam("burn", tmp.set(4 * Math.cos(ang), R_A + 10, 4 * Math.sin(ang)), new THREE.Vector3(0, R_A - 2, 0), 2, 2e8);
        } else {
          const step = a < 1.5 ? "The hold-downs release." : a < 10.3 ? "The wings unfold: the yoke, then the panels, one by one."
            : "Wings out, 663 W. The S-band dish looks down at the Moon; the X-band panel turns to the Earth.";
          u = { phase: "Activation", caption: step, readout: "orbit  673 × 7,331 km\nwings  2 × 5 panels" };
          // From the sunward side, so the unfolding wings are lit.
          craft.getWorldPosition(v.cw);
          h.sun.getWorldPosition(tmp).sub(v.cw).normalize();
          orbitFrame.worldToLocal(tmp.add(v.cw)).sub(craft.position).normalize();
          const dir = tmp.multiplyScalar(0.8).add(new THREE.Vector3(0, -0.5, 0.6)).normalize();
          cam("activation", dir.multiplyScalar(15).add(new THREE.Vector3(0, R_A, 0)), new THREE.Vector3(0, R_A, 0), 2, 2e8);
        }
      }

      // The lights: from the Sun and the Earth as they stand now, the Sun's shadow box riding with the craft.
      craft.getWorldPosition(v.cw);
      const lit = orbitView ? orbitFrame.localToWorld(new THREE.Vector3()) : v.cw;
      h.sun.getWorldPosition(v.sun).sub(lit).normalize();
      sunLight.target.position.copy(lit);
      sunLight.position.copy(lit).addScaledVector(v.sun, (local ? 59000 : orbitView ? 1e7 : 1500) * unitsPerM);
      sunLight.target.updateMatrixWorld();
      h.earthSystem.getWorldPosition(v.ew).sub(lit).normalize();
      earthshine.position.copy(lit).addScaledVector(v.ew, 1e4 * unitsPerM);
      earthshine.target.position.copy(lit); earthshine.target.updateMatrixWorld();

      // Once it is over, the camera keeps circling the craft.
      if (running && t >= TOTAL && !done) { done = true; on.done(); }
      if (done) { camera.position.add(shift.copy(v.cw).sub(controls.target)); controls.target.copy(v.cw); }
      // Near plane: a little in front of whatever the camera circles, so a close-up of the craft isn't clipped.
      const dist = camera.position.distanceTo(controls.target);
      camera.near = Math.max(dist * 1e-3, 0.01 * unitsPerM);
      controls.update();

      const key = u.phase + u.caption + u.readout;
      if (key !== lastUi) { lastUi = key; on.ui(running ? u : { phase: "", caption: "", readout: "" }); }
    },

    dispose() {
      const h = h0;
      if (!h || !saved) return;
      h.controls.removeEventListener("start", grab);
      setUp(h.camera, h.controls, Y.clone());
      h.moon.remove(launchFrame); h.moonFrame.remove(orbitFrame);
      h.scene.remove(sunLight, sunLight.target, earthshine);
      h.moon.geometry = saved.geometry; h.moon.material = saved.material;
      h.ambient.intensity = saved.ambient;
      h.renderer.shadowMap.enabled = saved.shadows;
      litMoon?.dispose(); sunkMoon?.dispose();
      terrain.geometry.dispose(); (terrain.material as THREE.Material).dispose(); regolith.dispose();
      track.geometry.dispose(); (track.material as THREE.Material).dispose();
      posts.geometry.dispose(); (posts.material as THREE.Material).dispose();
      for (const l of [shotPath, targetPath]) { l.geometry.dispose(); (l.material as THREE.Material).dispose(); }
      marker.geometry.dispose(); (marker.material as THREE.Material).dispose();
      sunLight.dispose(); earthshine.dispose();
    },
  };
}
