import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import type { SceneExtension, SceneHandles } from "../../components/SolarSystem";
import { moonSceneQuaternion, SCENE_FROM_FIXED } from "../../components/moonOrientation";
import { Site, terrainGeometry, regolithTexture, trackGeometry, SINK } from "./ground";

// Altair Aether's launch, placed into the site's solar-system scene: the Sun, the Earth, the Moon and the
// stars are that scene's own, on the launch date. This adds the ground around the track (fixed to the
// Moon, turning with it), the craft and its flight, the lights, and the camera's shots.
// The numbers are the spec's (scripts/blender/specs/aether.json): a flat shot off a 12.0 km track at
// 14 g reaches 1.815 km/s; half an orbit later, 700 km up over the north pole, the 20 N engine burns
// 124.3 m/s to make the orbit circular at 700 km (polar, one plane of a constellation); then the wings unfold.
const G0 = 9.80665;
const GM = 4.9e12;                       // m^3/s^2 (NSSDCA)
const R = 1737.4e3;                      // m
const R_A = R + 700e3;                   // the shot's high point: the circular orbit's radius
const R_P = R_A;                         // the burn lifts the low point to it: circular
const ACC = 14 * G0;
const G_MOON = GM / (R * R);
const V = Math.sqrt((2 * GM * R_A) / (R * (R + R_A)));  // the flat shot's speed
export const TRACK = (V * V) / (2 * ACC);
const T_SHOT = V / ACC;                  // 15.8 s, shown in real time
const SEP = 4;                           // after the track's end
const COAST = 12;                        // 71 min, shown in 12 s
const BURN = 8;                          // 1865 s, shown in 8 s
const ROLL = 3;                          // the last seconds of the coast: the craft rolls over, dish to the Moon
const REVEAL = 4;
const ACT = 13;
const AFTER = 30;                       // once the wings are out, the orbit goes on at 30 times true speed
const DV = Math.sqrt(GM / R_A) - (V * R) / R_A;                // circular speed less the shot's at its high point, 124.3 m/s
const BURN_S = Math.round((300 * DV) / 20);                    // 300 kg on the 20 N engine, 1865 s
const HALF_S = Math.PI * Math.sqrt(((R + R_A) / 2) ** 3 / GM);  // half the shot orbit: track's end to the high point, 71 min
const PERIOD_MIN = (2 * Math.PI * Math.sqrt(R_A ** 3 / GM)) / 60;

const P_COAST = T_SHOT + SEP, P_BURN = P_COAST + COAST, P_REVEAL = P_BURN + BURN;
const P_ACT = P_REVEAL + REVEAL, TOTAL = P_ACT + ACT;
// Mission time in seconds at scene time t: real during the shot, the coast and burn sped up.
const missionSeconds = (t: number) =>
  t < P_COAST ? t
    : t < P_BURN ? P_COAST + ((t - P_COAST) / COAST) * (HALF_S - SEP)
      : t < P_REVEAL ? T_SHOT + HALF_S + ((t - P_BURN) / BURN) * BURN_S
        : t < TOTAL ? T_SHOT + HALF_S + BURN_S + (t - P_REVEAL)
          : T_SHOT + HALF_S + BURN_S + (TOTAL - P_REVEAL) + (t - TOTAL) * AFTER;
const T_IN = T_SHOT + HALF_S + BURN_S;  // mission seconds at the burn's end: from here the craft goes round the circular orbit

// Sled parts leave the craft at the track's end; the model's own short rails are replaced by the long track.
const SLED = ["sep_ring_lower", "pusher", "sled_lettering", "sled_base", "shoe0", "shoe1", "shoe2", "shoe3", "armature"];
const MODEL_TRACK = ["rail0", "rail1", "stator"];
const RAIL_TOP = 0.19;                   // ground.ts trackGeometry: the rails' top above the bed

type Hinge = { node: THREE.Object3D; axis: THREE.Vector3; rest: THREE.Quaternion; restDeg: number };
/** The orbit inset: the craft in the orbit frame (metres, x along the motion at the low point, y up
 * through the high point) and the current orbit's low-point radius. */
export type OrbitInset = { x: number; y: number; rp: number; target: number; moon: number; ra: number };
export type LaunchUi = { phase: string; caption: string; readout: string; orbit?: OrbitInset };

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
// The craft's velocity direction on an orbit at true anomaly nu (orbit frame).
const orbitTangent = (o: { a: number; e: number }, nu: number, out: THREE.Vector3) =>
  out.copy(orbitPoint(o, nu + 1e-5)).sub(orbitPoint(o, nu)).normalize();
const utc = (jd: number) => new Date((jd - 2440587.5) * 86400e3).toISOString().slice(0, 16).replace("T", " ");


const CAP = THREE.MathUtils.degToRad(15);   // the polar caps reach 15° from each pole
/** A grid on the Moon's sphere (in the sphere mesh's frame: body-fixed x, z, -y), from colatitude c0 to c1 with
 * `rows` rings of `seg` segments; uv(colat, lon) gives each vertex's texture coordinates. Faces point outward. */
function sphereGrid(radius: number, c0: number, c1: number, rows: number, seg: number,
  uv: (colat: number, lon: number) => [number, number]) {
  const pos: number[] = [], nrm: number[] = [], uvs: number[] = [], idx: number[] = [];
  for (let k = 0; k <= rows; k++) {
    const colat = c0 + ((c1 - c0) * k) / rows, lat = Math.PI / 2 - colat;
    for (let j = 0; j <= seg; j++) {
      const lon = (2 * Math.PI * j) / seg - Math.PI;   // as SphereGeometry: u = 0 at longitude -180°
      const x = Math.cos(lat) * Math.cos(lon), y = Math.cos(lat) * Math.sin(lon), z = Math.sin(lat);
      nrm.push(x, z, -y); pos.push(x * radius, z * radius, -y * radius); uvs.push(...uv(colat, lon));
    }
  }
  for (let k = 0; k < rows; k++) for (let j = 0; j < seg; j++) {
    const a = k * (seg + 1) + j, b = a + seg + 1;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  g.setIndex(idx);
  return g;
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
const X_AXIS = new THREE.Vector3(1, 0, 0);
function setUp(camera: THREE.Camera, controls: SceneHandles["controls"], up: THREE.Vector3) {
  camera.up.copy(up);
  const c = controls as unknown as { _quat: THREE.Quaternion; _quatInverse: THREE.Quaternion };
  c._quat.setFromUnitVectors(camera.up, Y);
  c._quatInverse.copy(c._quat).invert();
}

export function aetherLaunch(site: Site, bin: ArrayBuffer, on: { ui(u: LaunchUi): void; done(): void }): AetherLaunch {
  const JD0 = site.meta.jd;
  let startAt: number | null = null;
  const sceneTime = () => (startAt === null ? 0 : performance.now() / 1000 - startAt);

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


  // Frames: the launch frame turns with the Moon; the orbit frame is the body-fixed frame at the launch,
  // held still in space (it rides with the Moon's centre).
  const launchFrame = new THREE.Group(), orbitFrame = new THREE.Group();
  launchFrame.matrixAutoUpdate = false; orbitFrame.matrixAutoUpdate = false;
  const launchSet = new THREE.Group();
  launchSet.add(terrain, track, posts);
  launchFrame.add(launchSet, craft, sled);

  // Light: the Sun (with the terrain's and the craft's shadows) and the Earth's glow, both from where they are.
  const sunLight = new THREE.DirectionalLight("#ffffff", 2.2);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(2048, 2048);
  sunLight.shadow.bias = -0.000001; sunLight.shadow.normalBias = 0.04;
  // The shadow box is in metres: the scene is drawn in metres around the camera (SolarSystem's renderRelative).
  Object.assign(sunLight.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 60000 });
  sunLight.shadow.camera.updateProjectionMatrix();
  const earthshine = new THREE.DirectionalLight("#cfdcff", 0.1);
  // The Earth as a sunlit globe (the main page draws it as a wireframe with outlines): NASA's Blue Marble
  // Next Generation for January (https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-topography-bathymetry/),
  // with clouds taken from NASA SVS 3615 (https://svs.gsfc.nasa.gov/3615/; scripts/aether/earth_clouds.py), 2048 x 1024.
  // Equirectangular; a sphere puts its middle (longitude 0) on +x, the globe on -x.
  const earthTex = new THREE.TextureLoader().load("/models/aether-launch/earth.jpg");
  earthTex.colorSpace = THREE.SRGBColorSpace;
  let earthGlobe: THREE.Mesh | null = null;
  const hiddenOnGlobe: THREE.Object3D[] = [];

  let h0: SceneHandles | null = null;
  let unitsPerM = 1;
  let saved: { geometry: THREE.BufferGeometry; material: THREE.Material | THREE.Material[]; ambient: number; shadows: boolean } | null = null;
  let litMoon: THREE.MeshStandardMaterial | null = null, sunkMoon: THREE.BufferGeometry | null = null;
  const moonMaps: THREE.Texture[] = [];
  const caps: THREE.Mesh[] = [];

  // Camera shots. Each opens on its planned view; once the viewer turns or zooms, only the point the
  // camera circles follows the craft (the camera moves with it), so their angle and zoom stay.
  let touched = false, done = false, lastUi = "", placed = false, followed = false;
  const offLocal = new THREE.Vector3();
  // A clicked star: the camera swings round the craft until the star stands just above it, and
  // stays so until the viewer turns the view.
  let aimView: THREE.Vector3 | null = null, aimT0 = 0, loads = 0;
  const aimFrom = new THREE.Vector3(), aimQ = new THREE.Quaternion(), aimQk = new THREE.Quaternion();
  const grab = () => { touched = true; aimView = null; };
  const tmp = new THREE.Vector3(), q = new THREE.Quaternion();
  const v = { pos: new THREE.Vector3(), up: new THREE.Vector3(), fwd: new THREE.Vector3(), side: new THREE.Vector3(),
    sun: new THREE.Vector3(), m: new THREE.Matrix4(), cw: new THREE.Vector3(), ew: new THREE.Vector3(),
    up2: new THREE.Vector3(), fwd2: new THREE.Vector3(), side2: new THREE.Vector3(), m2: new THREE.Matrix4(),
    bx: new THREE.Vector3(), by: new THREE.Vector3(), bz: new THREE.Vector3(), b: new THREE.Matrix4(), binv: new THREE.Matrix4(),
    off: new THREE.Vector3() };

  return {
    start() { startAt = performance.now() / 1000; followed = false; touched = false; done = false; },

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
      // Up close the main page's 2k map is a blur: here an 8k colour map and a relief (normal) map, and the poles
      // as separate caps with their own top-down (polar stereographic) maps, so they don't pinch. NASA's Scientific
      // Visualization Studio, CGI Moon Kit (https://svs.gsfc.nasa.gov/4720/): the LROC colour map, and normals
      // computed from its LOLA elevation map (16 px/deg, km above 1737.4 km). Swapped in once all have arrived.
      const mat = litMoon, aniso = renderer.capabilities.getMaxAnisotropy();
      const loader = new THREE.TextureLoader();
      const names = ["moon-8k", "moon-normal", "moon-cap-n", "moon-cap-n-normal", "moon-cap-s", "moon-cap-s-normal"];
      Promise.all(names.map((n) => loader.loadAsync(`/models/aether-launch/${n}.jpg`))).then((tex) => {
        if (litMoon !== mat) { tex.forEach((t) => t.dispose()); return; }
        tex.forEach((t, i) => { t.anisotropy = aniso; if (i % 2 === 0) t.colorSpace = THREE.SRGBColorSpace; });
        moonMaps.push(...tex);
        mat.map = tex[0]; mat.normalMap = tex[1]; mat.needsUpdate = true;
        const r = h.moonRadius * (R + SINK) / R, seg = 256;
        const band = sphereGrid(r, CAP, Math.PI - CAP, 107, seg, (c, lon) => [(lon + Math.PI) / (2 * Math.PI), 1 - c / Math.PI]);
        // Caps: image x along body-fixed +x, image up along +y, out to the cap's edge (tan(colat / 2) scales the plane).
        const capUv = (c: number, lon: number): [number, number] => {
          const q = Math.tan(c / 2) / Math.tan(CAP / 2);
          return [0.5 + 0.5 * q * Math.cos(lon), 0.5 + 0.5 * q * Math.sin(lon)];
        };
        const north = sphereGrid(r, 0, CAP, 40, seg, capUv);
        const south = sphereGrid(r, Math.PI - CAP, Math.PI, 40, seg, (c, lon) => capUv(Math.PI - c, lon));
        sunkMoon?.dispose(); sunkMoon = band; moon.geometry = band;
        for (const [g, m, n] of [[north, tex[2], tex[3]], [south, tex[4], tex[5]]] as const) {
          const cap = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: m, normalMap: n, roughness: 1, metalness: 0 }));
          caps.push(cap); moon.add(cap);
        }
      });
      h.ambient.intensity = 0.03;
      h.showOrbits(false);   // the planets' rings would cross the sky from the ground
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;

      launchFrame.matrix.copy(frameMatrix(site.origin, site.ex, site.ey, site.ez, unitsPerM));
      moon.add(launchFrame);
      orbitFrame.matrix.copy(frameMatrix([0, 0, 0], site.ox, site.oy, site.oz, unitsPerM))
        // Body-fixed at the moment the craft leaves the track, so the hand-over from the turning ground is seamless.
        .premultiply(new THREE.Matrix4().makeRotationFromQuaternion(moonSceneQuaternion(JD0 + T_SHOT / 86400)));
      h.moonFrame.add(orbitFrame);
      h.scene.add(sunLight, sunLight.target, earthshine);
      earthGlobe = new THREE.Mesh(new THREE.SphereGeometry(h.earthRadius, 96, 48), new THREE.MeshLambertMaterial({ map: earthTex }));
      earthGlobe.rotation.y = Math.PI;
      h.globe.add(earthGlobe);

      const load = ++loads;   // a later init (React's dev double mount) supersedes this load
      new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).load("/models/aether.glb", (gltf) => {
        if (load !== loads) return;
        const root = gltf.scene;
        root.updateMatrixWorld(true);
        // The model's own rail tops, so the shoes sit on the long track's rails.
        const rails = new THREE.Box3();
        for (const n of ["rail0", "rail1"]) { const o = root.getObjectByName(n); if (o) rails.union(new THREE.Box3().setFromObject(o)); }
        lift = RAIL_TOP - (rails.isEmpty() ? -0.53 : rails.max.y);
        // Split the sled off in the model's own space (a group not yet in the scene), then hang it on the track.
        const sledParts = new THREE.Group();
        for (const n of SLED) { const o = root.getObjectByName(n); if (o) sledParts.attach(o); }
        sled.add(sledParts);
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
      // Only the textured Earth: the wireframe, outlines and dots (some added later, as they load) stay hidden.
      for (const c of h.globe.children) if (c !== earthGlobe && c.visible) { c.visible = false; hiddenOnGlobe.push(c); }
      const t = sceneTime();
      const onTrack = t < T_SHOT;
      plume.visible = t >= P_BURN && t < P_REVEAL;
      sled.visible = t < P_COAST + 2;
      if (onTrack && craft.parent !== launchFrame) launchFrame.add(craft);
      if (!onTrack && craft.parent !== orbitFrame) orbitFrame.add(craft);
      launchFrame.updateWorldMatrix(true, false);
      orbitFrame.updateWorldMatrix(true, false);
      const frame = onTrack ? launchFrame : orbitFrame;
      if (!placed) {
        // Before launch (the Moon is now turned to the launch date): in front of the craft at the track's start, looking back at it.
        placed = true;
        setUp(camera, controls, tmp.setFromMatrixColumn(launchFrame.matrixWorld, 1).normalize());
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

      // In the Moon's shadow (a cylinder its size, away from the Sun) the Sun stops lighting the craft.
      craft.getWorldPosition(v.cw);
      h.sun.getWorldPosition(v.sun).sub(v.cw).normalize();
      h.moon.getWorldPosition(v.ew).sub(v.cw);
      const along = v.ew.dot(v.sun);
      const lit = onTrack || along <= 0 || v.ew.lengthSq() - along * along > h.moonRadius * h.moonRadius;
      sunLight.intensity = lit ? 2.2 : 0;

      // Where the craft is, and its flight frame (forward along the motion, up away from the Moon), in `frame`.
      let u: LaunchUi = { phase: "", caption: "", readout: "" };
      let xs = 0, roll = 0, rp = R;
      if (onTrack) {
        const s = running ? 0.5 * ACC * t * t : 0; xs = s;
        site.trackAt(s, v.pos, v.up, v.fwd);
        v.pos.addScaledVector(v.up, lift);
        u = { phase: "Launch", caption: `On the mass driver 17 km from the south pole: 14 g along a ${(TRACK / 1000).toFixed(1)} km track, cut and banked through the real terrain.`,
          readout: `UTC    ${utc(jd)}\nspeed  ${((ACC * t) / 1000).toFixed(3)} km/s\naccel  14 g\ntrack  ${(s / 1000).toFixed(1)} / ${(TRACK / 1000).toFixed(1)} km` };
      } else {
        // Off the track: on the shot's orbit, by mission time since the track's end, up to the high point.
        // Its low point is drawn at the track's end (the bed less the 1737.4 km sphere, plus the craft's lift).
        const tau = Math.min(missionSeconds(t) - T_SHOT, HALF_S);
        // Held at the high point through the burn, then round the circular orbit.
        const circling = tau >= HALF_S, path = circling ? target : shot;
        const nu = circling ? Math.PI + (Math.max(0, missionSeconds(t) - T_IN) * 2 * Math.PI) / (PERIOD_MIN * 60)
          : trueAnomaly((Math.PI * tau) / HALF_S, shot.e);
        const zEnd = site.meta.profile.z[site.meta.profile.z.length - 1] + lift;
        v.pos.copy(orbitPoint(path, nu));
        v.up.copy(v.pos).normalize();
        v.pos.addScaledVector(v.up, zEnd);
        orbitTangent(path, nu, v.fwd);
        const tb = Math.min(t - T_SHOT, V / (30 * G0));
        xs = TRACK + V * tb - 0.5 * 30 * G0 * tb * tb;
        const r = v.pos.length(), vel = Math.sqrt(GM * (2 / r - 1 / shot.a));
        if (t < P_COAST) {
          const local = launchFrame.worldToLocal(orbitFrame.localToWorld(v.pos.clone()));
          const above = heightAt(local) - terrainZ(local.x, -local.z);
          u = { phase: "Separation", caption: `Off the end of the track at ${(V / 1000).toFixed(2)} km/s, a little over orbital speed. The sled brakes; the craft flies on, and the ground curves away beneath it.`,
            readout: `UTC    ${utc(jd)}\nspeed  ${(vel / 1000).toFixed(3)} km/s\nheight ${Math.max(0, above).toFixed(0)} m` };
        } else if (t < P_BURN) {
          u = { phase: "Coast", caption: `Coasting half an orbit, ${Math.round(HALF_S / 60)} minutes, up to ${km(R_A - R)} km over the north pole.`,
            readout: `UTC    ${utc(jd)}\nT+     ${Math.round(tau / 60)} min\nheight ${km(r - R)} km\nspeed  ${(vel / 1000).toFixed(3)} km/s` };
        } else if (t < P_REVEAL) {
          const f = (t - P_BURN) / BURN;
          rp = R + (R_P - R) * f;
          (plume.material as THREE.MeshBasicMaterial).opacity = 0.25 + 0.1 * Math.sin(t * 40);
          u = { phase: "Orbit insertion", caption: `At the high point the 20 N engine burns ${DV.toFixed(1)} m/s, lifting the orbit's low point from the surface to ${km(R_P - R)} km: the orbit becomes circular.`,
            readout: `Δv     ${(DV * f).toFixed(1)} / ${DV.toFixed(1)} m/s\nburn   ${Math.round(BURN_S * f)} / ${BURN_S} s` };
        } else if (t < P_ACT) {
          rp = R_P;
          u = { phase: "In orbit", caption: `A circular polar orbit ${km(R_A - R)} km up, one plane of the constellation; the Moon turning beneath the track puts each later launch in a new plane.`,
            readout: `orbit  ${km(R_A - R)} km circular, polar\nperiod ${Math.round(PERIOD_MIN)} min` };
        } else {
          rp = R_P;
          const step = a < 1.5 ? "The hold-downs release." : a < 10.3 ? "The wings unfold: the yoke, then the panels, one by one."
            : "Wings out, 663 W. The S-band dish looks down at the Moon; the X-band panel turns to the Earth.";
          u = t < TOTAL ? { phase: "Activation", caption: step, readout: `orbit  ${km(R_A - R)} km circular, polar\nwings  2 × 5 panels` }
            : { phase: "In orbit", caption: step, readout: `UTC    ${utc(jd)}\nclock  ${AFTER}× true speed\norbit  ${km(R_A - R)} km, ${Math.round(PERIOD_MIN)} min${lit ? "" : "\nin the Moon's shadow"}` };
        }
        // Before the burn the craft rolls over: the engine still along the motion, the dish now down to the Moon.
        roll = Math.PI * ease((t - (P_BURN - ROLL)) / ROLL);
        u.orbit = { x: v.pos.x, y: v.pos.y, rp, target: R_P, moon: R, ra: R_A };
      }
      v.fwd.sub(tmp.copy(v.up).multiplyScalar(v.fwd.dot(v.up))).normalize();   // level forward
      v.side.crossVectors(v.fwd, v.up).normalize();
      v.m.makeBasis(v.fwd, v.up, v.side);
      craft.quaternion.setFromRotationMatrix(v.m).multiply(q.setFromAxisAngle(X_AXIS, roll));
      craft.position.copy(v.pos);
      // The sled brakes to a stop on the track.
      site.trackAt(running ? Math.min(xs, TRACK) : 0, tmp, v.up2, v.fwd2);
      v.side2.crossVectors(v.fwd2, v.up2).normalize();
      sled.quaternion.setFromRotationMatrix(v.m2.makeBasis(v.fwd2, v.up2, v.side2));
      sled.position.copy(tmp).addScaledVector(v.up2, lift);

      // The camera rides with the craft, in its flight frame: behind and to the left on the track,
      // rising to look down past it at the Moon as it climbs. The viewer's own angle and zoom, once they
      // turn or zoom, are kept in that frame, so the Moon stays below.
      craft.getWorldPosition(v.cw);
      v.bx.copy(v.fwd).transformDirection(frame.matrixWorld);
      v.by.copy(v.up).transformDirection(frame.matrixWorld);
      v.bz.copy(v.side).transformDirection(frame.matrixWorld);
      v.b.makeBasis(v.bx, v.by, v.bz);
      if (running) {
        if (!followed) { followed = true; touched = false; setUp(camera, controls, v.by); }
        if (v.by.distanceToSquared(camera.up) > 1e-12) setUp(camera, controls, v.by);
        const alt = onTrack ? 0 : v.pos.length() - R;
        const k = ease(alt / 500e3);                     // 0 on the ground, 1 from 500 km up
        const look = tmp.set(2 * (1 - k), 0.8 * (1 - k), 0);
        controls.target.copy(v.cw).add(look.applyMatrix4(v.b).multiplyScalar(unitsPerM));
        if (!touched) {
          // Elevation of the view: 11 degrees on the track, 60 degrees looking down from orbit.
          const el = THREE.MathUtils.degToRad(11 + 49 * k), dist = 11.3 + 2 * k;
          offLocal.set(-Math.cos(el) * dist * 0.81, Math.sin(el) * dist, -Math.cos(el) * dist * 0.58);
        }
        const off = v.off.copy(offLocal).applyMatrix4(v.b).multiplyScalar(unitsPerM);
        camera.position.copy(controls.target).add(off);
        if (onTrack && !touched) {
          // Never inside a cutting's wall.
          const lc = launchFrame.worldToLocal(camera.position.clone());
          lc.y = Math.max(lc.y, groundY(lc.x, lc.z) + 1.5);
          camera.position.copy(launchFrame.localToWorld(lc));
        }
      }

      // The lights: from the Sun and the Earth as they stand now, the Sun's shadow box riding with the craft.
      h.sun.getWorldPosition(v.sun).sub(v.cw).normalize();
      sunLight.target.position.copy(v.cw);
      sunLight.position.copy(v.cw).addScaledVector(v.sun, 59000 * unitsPerM);
      sunLight.target.updateMatrixWorld();
      h.earthSystem.getWorldPosition(v.ew).sub(v.cw).normalize();
      earthshine.position.copy(v.cw).addScaledVector(v.ew, 1e4 * unitsPerM);
      earthshine.target.position.copy(v.cw); earthshine.target.updateMatrixWorld();

      if (running && t >= TOTAL && !done) { done = true; on.done(); }
      if (aimView) {
        aimQ.setFromUnitVectors(aimFrom, aimView);
        aimQk.identity().slerp(aimQ, ease((performance.now() / 1000 - aimT0) / 1.5));
        const d = camera.position.distanceTo(controls.target);
        camera.position.copy(controls.target).add(tmp.copy(aimFrom).applyQuaternion(aimQk).multiplyScalar(d));
      }
      // Near plane: a little in front of whatever the camera circles, so a close-up of the craft isn't clipped.
      const dist = camera.position.distanceTo(controls.target);
      camera.near = Math.max(dist * 1e-3, 0.01 * unitsPerM);
      controls.update();
      if (running && touched) {
        // Keep the viewer's angle and zoom in the flight frame.
        offLocal.copy(camera.position).sub(controls.target).divideScalar(unitsPerM).applyMatrix4(v.binv.copy(v.b).transpose());
      }

      const key = u.phase + u.caption + u.readout + (u.orbit ? `${u.orbit.x.toFixed(0)},${u.orbit.y.toFixed(0)},${u.orbit.rp.toFixed(0)}` : "");
      if (key !== lastUi) { lastUi = key; on.ui(running ? u : { phase: "", caption: "", readout: "" }); }
    },

    aimAt(dir) {
      const h = h0;
      if (!h) return;
      // Look a little below the star, so it shows just above the craft rather than behind it.
      const right = new THREE.Vector3().crossVectors(dir, h.camera.up).normalize();
      aimView = dir.clone().applyAxisAngle(right, -THREE.MathUtils.degToRad(10)).negate();
      aimFrom.copy(h.camera.position).sub(h.controls.target).normalize();
      aimT0 = performance.now() / 1000;
      touched = true;
    },

    dispose() {
      loads++;
      const h = h0;
      if (!h || !saved) return;
      h.controls.removeEventListener("start", grab);
      setUp(h.camera, h.controls, Y.clone());
      h.moon.remove(launchFrame); h.moonFrame.remove(orbitFrame);
      h.scene.remove(sunLight, sunLight.target, earthshine);
      for (const c of hiddenOnGlobe) c.visible = true;
      hiddenOnGlobe.length = 0;
      if (earthGlobe) { h.globe.remove(earthGlobe); earthGlobe.geometry.dispose(); (earthGlobe.material as THREE.Material).dispose(); earthGlobe = null; }
      h.moon.geometry = saved.geometry; h.moon.material = saved.material;
      h.ambient.intensity = saved.ambient;
      h.renderer.shadowMap.enabled = saved.shadows;
      litMoon?.dispose(); sunkMoon?.dispose(); litMoon = null;
      for (const t of moonMaps) t.dispose();
      for (const c of caps) { h.moon.remove(c); c.geometry.dispose(); (c.material as THREE.Material).dispose(); }
      caps.length = 0;
      moonMaps.length = 0;
      terrain.geometry.dispose(); (terrain.material as THREE.Material).dispose(); regolith.dispose();
      track.geometry.dispose(); (track.material as THREE.Material).dispose();
      posts.geometry.dispose(); (posts.material as THREE.Material).dispose();
      sunLight.dispose(); earthshine.dispose();
    },
  };
}
