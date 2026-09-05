"use client";

import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { usePageStore } from '../store/pageStore';
import { PLANETS, MOONS, STARS, SPECTRAL_COLORS, APOLLO_SITES, MISSIONS } from './solarSystemData';
import { moonPositionJ2000Km } from './lunar';

interface PersonaDot {
  id: number;
  lat: number;
  lon: number;
  color: string;
  size: number;
  opacity?: number;
  persona?: any;
  info?: string;
  label?: string;
  description?: string;
}

interface SolarSystemProps {
  className?: string;
  size?: number;
  color?: string;
  speed?: number;
  dots?: PersonaDot[];
  onDotClick?: (dot: PersonaDot) => void;
  onDotHover?: (dot: PersonaDot | null) => void;
  onBodyHover?: (name: string | null) => void;
  onStarHover?: (star: { name: string; lightYears: number; spectral?: string; fact?: string } | null) => void;
  onFocusChange?: (name: string | null) => void; // null when the camera is far from the focused body
  dotSizeMultiplier?: number;
}

// --- Scene layout ---
// The scene is heliocentric: the Sun sits at the origin and everything orbits
// it. The camera follows one focused body (Earth on load); clicking another
// body makes it the focus. Focus never changes on its own.
const EARTH_RADIUS = 1.3;              // Base unit; everything else is relative to this
const CAMERA_FOV = 50;
const DEFAULT_CAMERA_DISTANCE = 4.5;   // Initial view; also the closest allowed zoom
const MAX_CAMERA_DISTANCE = 180;       // How far out the user can scroll

// Planet orbits and moon orbits use TRUE distance ratios (orbit radius =
// ORBIT_SCALE * AU for planets; planet radii for moons). Body sizes are the
// one compressed thing: at true ratio Earth would be 0.004 units across.
// Bodies are never drawn smaller than MIN_BODY_PX so the outer system still
// reads as a system rather than empty space.
// TRUE SCALE: one AU is Earth's radius divided by Earth's real radius-to-AU ratio
// (6371 km / 149,597,870 km), so sizes, planet orbits (AU) and moon orbits
// (planet radii) all sit on one consistent scale. Earth orbits at ~30,500 units.
const EARTH_RADIUS_PER_AU = 6371 / 149597870;
// Two scale modes (terminal `scale` command). "true": every ratio exact.
// "compact": the cinematic layout, distances squeezed toward their parents so
// the Moon and the Sun are close enough to see from Earth's default view.
export type ScaleMode = 'true' | 'compact';
const SCALES: Record<ScaleMode, { orbitScale: number; sunRadius: number; moonOrbitRadius: number; starSphereRadius: number; farPlane: number; sunGlowScale: number }> = {
  true: {
    orbitScale: EARTH_RADIUS / EARTH_RADIUS_PER_AU, // ~30,500 units per AU
    sunRadius: EARTH_RADIUS * 109.2,
    moonOrbitRadius: EARTH_RADIUS * (384400 / 6371), // 384,400 km, on the same km scale as orbitScale
    starSphereRadius: 8e6,                          // beyond the max zoom-out (~3.7M at Pluto), inside the far plane
    farPlane: 3e7,
    sunGlowScale: 4.5,                              // glow sprite size as a multiple of the Sun's diameter
  },
  compact: {
    orbitScale: 260,
    sunRadius: 20,
    moonOrbitRadius: 6,
    starSphereRadius: 50000,
    farPlane: 1e5,
    sunGlowScale: 2.5,                              // the Sun is already big here; keep the glare modest
  },
};
const EARTH_ORBIT_AU = 1;
const VIEW_KEY = 'explore-view'; // persisted camera view: focused body + offset in body radii
const MIN_BODY_PX = 3;                 // Minimum on-screen radius of any body, in pixels
// A body's enforced size is capped relative to its parent (moons to their
// planet, planets to the Sun), so it can't outgrow what it orbits as you zoom
// out; below a pixel it is hidden.
const CHILD_MAX_PARENT_FRACTION = 1 / 3;  // upper bound for any child; planets vs the Sun use exactly this
// Moons get their own cap from their real size ratio to their planet, times a
// tolerance, bounded above by the fraction. Io ends up ~0.10, Earth's Moon 1/3.
const MOON_RATIO_TOLERANCE = 4;
// While the planet is drawn large, a moon may still use the pixel floor even if
// its cap is below it, so km-scale moons show as dots at the planet's close-up.
const DOT_MOON_PARENT_PX = 100;
const CHILD_HIDE_PX = 1;
const MIN_CLOSE_DISTANCE = 0.5;        // Closest zoom for any body, so tiny moons stay past the near plane
const ORBIT_RING_STYLE = { color: 0xffffff, opacity: 0.45 }; // rings are hidden until the `orbits` command shows them

// One clock for all motion: a simulated Julian date, advanced by real seconds /
// secondsPerDay (live: see the `time` command). Positions are functions of the
// date, seeded from real J2000 orbital elements, so the sky matches real dates.
let secondsPerDay = 10;
const J2000 = 2451545.0;
const jdNow = () => Date.now() / 86400000 + 2440587.5;
const EARTH_MEAN_LONGITUDE_DEG = 100.464; // J2000
// Earth's rotation from the date: Greenwich mean sidereal time.
const gmstDeg = (jd: number) => 280.46061837 + 360.98564736629 * (jd - J2000);
const EARTH_DAY_DAYS = 0.99727;        // Sidereal rotation period, in days
const MOON_ORBIT_DAYS = 27.32;         // Sidereal month
const EARTH_YEAR_DAYS = 365.25;
const EARTH_ECCENTRICITY = 0.0167;
const EARTH_PERIHELION_DEG = 102.9;    // longitude of perihelion (J2000)
const angularSpeed = (periodDays: number) => (2 * Math.PI) / (periodDays * secondsPerDay); // rad/s

const MOON_RADIUS = EARTH_RADIUS * 0.273; // True ratio: Moon diameter is 27.3% of Earth's
const MOON_INCLINATION_DEG = 5.14;     // Real inclination of the Moon's orbit
const MOON_TEXTURE = '/moon.jpg';      // Equirectangular map


const SUN_COLOR = 0xfff4e8;            // G2V: near-white, faintly warm (the yellow is atmospheric)
const SUN_ROTATION_DAYS = 25.05;       // sidereal rotation at the equator

// Stars: one sprite each on a sphere that is re-centred on the camera every
// frame (no parallax, which is physically right at this scale). Directions are
// true; the sphere radius just has to sit inside the far plane. The sprite is a
// telescope-style star: saturated core, tinted halo, diffraction spikes. Size
// follows brightness, so only the bright ones show spikes.
const STAR_BASE_PX = 22;               // on-screen size (pixels) of a magnitude-0 star's sprite
const STAR_MIN_PX = 4;                 // faint stars (mag 4-5) still show as a small dot
const STAR_MAG_EXPONENT = 0.18;        // size = base * 10^(-exp * mag); 0.2 matches real flux by area, lower is gentler
const OBLIQUITY_DEG = 23.44;           // equatorial -> ecliptic; matches Earth's tilt in the scene

// Draws the star sprite texture once: core + halo + 4 main spikes + 4 fainter diagonals.
function makeStarTexture(): THREE.CanvasTexture {
  const size = 256;
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d')!;
  const mid = size / 2;
  ctx.clearRect(0, 0, size, size);
  ctx.globalCompositeOperation = 'lighter';

  const spike = (angle: number, length: number, width: number, alpha: number) => {
    ctx.save();
    ctx.translate(mid, mid);
    ctx.rotate(angle);
    const g = ctx.createLinearGradient(-length, 0, length, 0);
    g.addColorStop(0, 'rgba(255,255,255,0)');
    g.addColorStop(0.5, `rgba(255,255,255,${alpha})`);
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.fillRect(-length, -width / 2, length * 2, width);
    ctx.restore();
  };
  // Main cross, then a fainter diagonal cross (secondary struts).
  spike(0, mid, 2.2, 0.9);
  spike(Math.PI / 2, mid, 2.2, 0.9);
  spike(Math.PI / 4, mid * 0.55, 1.4, 0.35);
  spike(-Math.PI / 4, mid * 0.55, 1.4, 0.35);

  // Halo (wide, soft) and core (small, saturated).
  const halo = ctx.createRadialGradient(mid, mid, 0, mid, mid, mid * 0.5);
  halo.addColorStop(0, 'rgba(255,255,255,1)');
  halo.addColorStop(0.15, 'rgba(255,255,255,0.65)');
  halo.addColorStop(0.5, 'rgba(255,255,255,0.15)');
  halo.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = halo;
  ctx.fillRect(0, 0, size, size);
  const core = ctx.createRadialGradient(mid, mid, 0, mid, mid, mid * 0.09);
  core.addColorStop(0, 'rgba(255,255,255,1)');
  core.addColorStop(0.6, 'rgba(255,255,255,1)');
  core.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = core;
  ctx.fillRect(0, 0, size, size);

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// "Fit" distance: how far back the camera must be for an extent to fit the
// canvas width. Used for per-body zoom limits.
const FIT_MARGIN = 1.15;               // Extra room for perspective
const WIDE_VIEW_PLANET = 'Jupiter';    // The Sun's default (click / fly) view fits this planet's orbit; zoom-out still reaches the outermost

// Focus / picking
const MIN_DISTANCE_RADII = DEFAULT_CAMERA_DISTANCE / EARTH_RADIUS; // closest zoom, in body radii
// These are multiples of a body's closest zoom distance (which has a floor for
// tiny bodies), so they stay reachable for moons a few km across.
const NAME_VISIBLE_FACTOR = 10 / MIN_DISTANCE_RADII;   // ~2.9x close-up: focused body's name shows within 10 radii
const ROOT_NAME_VISIBLE_FACTOR = 1.15;                 // for the Sun, relative to its wide-view fly-in distance
const REFOCUS_FACTOR = 20 / MIN_DISTANCE_RADII;        // ~5.8x close-up: beyond this, clicking the focused body zooms back in
const FOCUS_TRANSITION_SECONDS = 0.9;  // base duration; fly-ins add time per decade of distance covered
const FOCUS_SECONDS_PER_DECADE = 0.45; // Earth -> Moon ~1.6 s, Earth -> Pluto ~3.5 s
const PICK_MIN_PX = 12;                // click tolerance floor, in pixels
const PICK_RADIUS_MULTIPLE = 4;        // tolerance = drawn radius * this (capped: big bodies use their outline)
const PICK_CAP_PX = 30;                // above this drawn radius, the outline itself is the hitbox
const DRAG_THRESHOLD_PX = 5;           // pointer movement beyond this is a drag, not a click

type Body = {
  name: string;
  object: THREE.Object3D;   // world position is read from this each frame
  visual: THREE.Object3D;   // what gets scaled up to enforce MIN_BODY_PX
  radius: number;
  parent: Body | null;
  systemRadius: number;     // radius of its satellites' orbits (0 = none)
  scale: number;            // current enforced scale (1 = true size)
  focusRadii?: number;      // click fly-in distance override, in radii
};

// --- GeoJSON outline helpers ---
const loadGeoJsonData = async () => {
  try {
    const response = await fetch('/continents.json');
    return await response.json();
  } catch (error) {
    console.warn('Failed to load continent data:', error);
    return null;
  }
};

const lonLatToVector3 = (lon: number, lat: number, radius: number) => {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (-lon + 180) * (Math.PI / 180); // Fixed: negate longitude to correct inversion
  const x = radius * Math.sin(phi) * Math.cos(theta);
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.sin(theta);
  return new THREE.Vector3(x, y, z);
};

const drawGeoJsonContoursAndFill = (
  geoJson: any,
  group: THREE.Group,
  radius: number,
  outlineColor = "#fff",
  outlineOpacity = 0.85
) => {
  geoJson.features.forEach((feature: any) => {
    const geometry = feature.geometry;
    if (!geometry) return;
    const coordsList = geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.coordinates;

    coordsList.forEach((polygon: any) => {
      polygon.forEach((ring: any) => {
        if (ring.length < 3) return;
        const vec3Points = ring.map(([lon, lat]: [number, number]) =>
          lonLatToVector3(lon, lat, radius)
        );
        const outlineGeom = new THREE.BufferGeometry().setFromPoints(vec3Points);
        const line = new THREE.Line(
          outlineGeom,
          new THREE.LineBasicMaterial({
            color: outlineColor,
            transparent: true,
            opacity: outlineOpacity
          })
        );
        group.add(line);
      });
    });
  });
};

export function SolarSystem({
  className,
  size,
  color = "#333333",
  speed = 0.003,
  dots = [],
  onDotClick,
  onDotHover,
  onBodyHover,
  onStarHover,
  onFocusChange,
  dotSizeMultiplier = 1
}: SolarSystemProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const globeRef = useRef<THREE.Group | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const animationIdRef = useRef<number | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const autoRotateRef = useRef<boolean>(true);
  const hoverPausedRef = useRef<boolean>(false); // Earth's spin pauses while the pointer is over it
  const dotsRef = useRef<THREE.Mesh[]>([]);
  const moonDotsRef = useRef<THREE.Mesh[]>([]); // Apollo site hitboxes (kept apart from the Earth dots effect)
  const apolloGroupRef = useRef<THREE.Group | null>(null);
  const handledDateSeqRef = useRef(0);
  const trackRequest = usePageStore((s) => s.trackRequest);
  const handledTrackSeqRef = useRef(0);
  const trackRef = useRef<((id: string | null) => void) | null>(null);
  const apolloVisible = usePageStore((s) => s.apolloVisible);
  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster());
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2());
  const initializedRef = useRef<boolean>(false);
  const hoveredDotRef = useRef<PersonaDot | null>(null);
  const simJDRef = useRef<number>(0);        // current simulated Julian date (read by the `date` command via the store)
  const dateRequestRef = useRef<number | null>(null); // a requested jump, consumed by the loop
  const dateRequest = usePageStore((s) => s.dateRequest);
  const earthSystemRef = useRef<THREE.Group | null>(null);
  const hoveredBodyRef = useRef<string | null>(null);
  const hoveredStarRef = useRef<string | null>(null);
  const pointerDownPosRef = useRef<{ x: number; y: number } | null>(null);
  const focusByNameRef = useRef<((name: string) => void) | null>(null);
  // Saved across a scene rebuild (scale switch): which body was focused and the
  // camera's offset from it in body radii, so the view is restored, not reset.
  const savedViewRef = useRef<{ name: string; dir: THREE.Vector3; radii: number } | null>(null);
  // The same snapshot also persists to localStorage (VIEW_KEY), restored once per page load.
  const restoredStoredViewRef = useRef(false);
  const aimAtStarRef = useRef<((star: { sprite: THREE.Sprite; px: number; name: string; lightYears: number; spectral: string; fact?: string }) => void) | null>(null);
  const focusRequest = usePageStore((s) => s.focusRequest);
  const starsVisible = usePageStore((s) => s.starsVisible);
  const orbitsHighlighted = usePageStore((s) => s.orbitsHighlighted);
  const scaleMode = usePageStore((s) => s.scaleMode);
  const storeSecondsPerDay = usePageStore((s) => s.secondsPerDay);
  secondsPerDay = storeSecondsPerDay; // picked up by angularSpeed() on the next frame
  const setOrbitStyleRef = useRef<((on: boolean) => void) | null>(null);
  const starFieldRef = useRef<THREE.Group | null>(null);
  const handledFocusSeqRef = useRef<number>(0);
  const isPointerDownRef = useRef<boolean>(false);
  const moonMaterialRef = useRef<THREE.MeshBasicMaterial | null>(null);
  const sunMaterialRef = useRef<THREE.MeshBasicMaterial | null>(null);
  const sunGlowMaterialRef = useRef<THREE.SpriteMaterial | null>(null);

  // Memoize dots comparison to prevent unnecessary updates
  const dotsString = useMemo(() => JSON.stringify(dots), [dots]);

  const latLonToVector3 = (lat: number, lon: number, radius: number) => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (-lon + 180) * (Math.PI / 180); // Fixed: negate longitude to correct inversion
    const x = radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.cos(phi);
    const z = radius * Math.sin(phi) * Math.sin(theta);
    return new THREE.Vector3(x, y, z);
  };

  // Initialize the scene only once
  useEffect(() => {
    if (!mountRef.current || initializedRef.current) return;
    const { orbitScale, sunRadius: SUN_RADIUS, moonOrbitRadius: MOON_ORBIT_RADIUS, starSphereRadius: STAR_SPHERE_RADIUS, farPlane, sunGlowScale: SUN_GLOW_SCALE } = SCALES[scaleMode];
    const orbitRadiusForAU = (au: number) => orbitScale * au;

    // Clean up any existing content first
    while (mountRef.current.firstChild) {
      mountRef.current.removeChild(mountRef.current.firstChild);
    }

    // Scene setup
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Camera setup
    const mount = mountRef.current;
    const initialWidth = size ?? (mount.clientWidth || 500);
    const initialHeight = size ?? (mount.clientHeight || 500);
    const camera = new THREE.PerspectiveCamera(CAMERA_FOV, initialWidth / initialHeight, 0.1, farPlane);
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true,
      logarithmicDepthBuffer: true, // near 0.1 to far 3e7 without z-fighting
    });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(initialWidth, initialHeight);
    renderer.setClearColor(new THREE.Color(0x000000), 0);
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.outline = 'none';
    renderer.domElement.style.userSelect = 'none';
    rendererRef.current = renderer;
    mountRef.current.appendChild(renderer.domElement);

    // Earth system: a position-only group that orbits the Sun. It holds the
    // tilted/spinning globe and the Moon's pivot as siblings, so the Moon does
    // not inherit Earth's daily spin, and Earth's axis stays fixed in space as
    // it goes around (which is what gives correct seasons).
    const earthSystem = new THREE.Group();
    earthSystemRef.current = earthSystem;
    scene.add(earthSystem);

    // Globe group
    const globeGroup = new THREE.Group();
    globeRef.current = globeGroup;
    earthSystem.add(globeGroup);

    // Add Earth's realistic tilt (23.5 degrees)
    globeGroup.rotation.x = -THREE.MathUtils.degToRad(OBLIQUITY_DEG); // pole leans toward -z (ecliptic longitude 90)

    // Create wireframe sphere
    const globeRadius = EARTH_RADIUS;
    const sphereGeometry = new THREE.SphereGeometry(globeRadius, 32, 32);
    const wireframeMaterial = new THREE.MeshBasicMaterial({
      color: color,
      wireframe: true,
      transparent: true,
      opacity: 0.4
    });
    const wireframeSphere = new THREE.Mesh(sphereGeometry, wireframeMaterial);
    globeGroup.add(wireframeSphere);

    // Occluder sphere: writes to depth buffer only, hides continents behind the globe
    const occluderGeometry = new THREE.SphereGeometry(globeRadius - 0.01, 32, 32);
    const occluderMaterial = new THREE.MeshBasicMaterial({
      colorWrite: false,
    });
    const occluderSphere = new THREE.Mesh(occluderGeometry, occluderMaterial);
    globeGroup.add(occluderSphere);

    // Moon: added as an orbiter of the Earth system below (after the orbit
    // machinery is defined), with its real precessing node and perigee.

    const moonGeometry = new THREE.SphereGeometry(MOON_RADIUS, 32, 32);
    const moonTexture = new THREE.TextureLoader().load(MOON_TEXTURE);
    moonTexture.colorSpace = THREE.SRGBColorSpace;
    const moonMaterial = new THREE.MeshBasicMaterial({
      map: moonTexture,
      transparent: true,
      opacity: 1,
    });
    moonMaterialRef.current = moonMaterial;
    const moon = new THREE.Mesh(moonGeometry, moonMaterial);
    // (Position and tidal-lock rotation are set every frame by the orbiter update:
    // the map's centre, lon 0, is turned to face Earth.)

    // Apollo landing sites: green dots on the Moon, like Earth's location dots.
    // Placed via the sphere's own texture mapping (u = lon, v = lat), so they
    // sit on the map features regardless of how the mesh is turned.
    const apolloGroup = new THREE.Group();
    apolloGroup.visible = usePageStore.getState().apolloVisible;
    apolloGroupRef.current = apolloGroup;
    moon.add(apolloGroup);
    const apolloDisposables: (THREE.BufferGeometry | THREE.Material)[] = [];
    APOLLO_SITES.forEach((site, i) => {
      const u = site.lon / 360 + 0.5;
      const v = (90 - site.lat) / 180;
      const r = MOON_RADIUS + 0.004;
      const pos = new THREE.Vector3(
        -r * Math.cos(u * 2 * Math.PI) * Math.sin(v * Math.PI),
        r * Math.cos(v * Math.PI),
        r * Math.sin(u * 2 * Math.PI) * Math.sin(v * Math.PI),
      );
      const size = MOON_RADIUS * 0.025;
      const g = new THREE.SphereGeometry(size, 8, 8);
      const m = new THREE.MeshBasicMaterial({ color: '#00ff00', transparent: true, opacity: 0.9 });
      const dot = new THREE.Mesh(g, m);
      dot.position.copy(pos);
      apolloGroup.add(dot);
      const hg = new THREE.SphereGeometry(size * 4, 8, 8);
      const hm = new THREE.MeshBasicMaterial({ visible: false });
      const hit = new THREE.Mesh(hg, hm);
      hit.position.copy(pos);
      hit.userData = { dot: { id: 1000 + i, lat: site.lat, lon: site.lon, color: '#00ff00', size: 1, label: site.mission, subtitle: String(site.year), description: site.site } };
      apolloGroup.add(hit);
      moonDotsRef.current.push(hit);
      apolloDisposables.push(g, m, hg, hm);
    });

    // Sun: a solid sphere at the origin plus a soft additive glow sprite that
    // always faces the camera.
    const sunGeometry = new THREE.SphereGeometry(SUN_RADIUS, 48, 48);
    const sunMaterial = new THREE.MeshBasicMaterial({
      color: SUN_COLOR,
      transparent: true,
      opacity: 1,
    });
    sunMaterialRef.current = sunMaterial;
    const sun = new THREE.Mesh(sunGeometry, sunMaterial);
    scene.add(sun);

    const glowCanvas = document.createElement('canvas');
    glowCanvas.width = glowCanvas.height = 256;
    const glowCtx = glowCanvas.getContext('2d')!;
    const gradient = glowCtx.createRadialGradient(128, 128, 0, 128, 128, 128);
    gradient.addColorStop(0, 'rgba(255, 244, 232, 1)');
    gradient.addColorStop(0.3, 'rgba(255, 244, 232, 0.85)');
    gradient.addColorStop(0.6, 'rgba(255, 236, 214, 0.3)');
    gradient.addColorStop(1, 'rgba(255, 236, 214, 0)');
    glowCtx.fillStyle = gradient;
    glowCtx.fillRect(0, 0, 256, 256);
    const glowTexture = new THREE.CanvasTexture(glowCanvas);
    const sunGlowMaterial = new THREE.SpriteMaterial({
      map: glowTexture,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      transparent: true,
      opacity: 1,
    });
    sunGlowMaterialRef.current = sunGlowMaterial;
    const sunGlow = new THREE.Sprite(sunGlowMaterial);
    const glowSize = SUN_RADIUS * 2 * SUN_GLOW_SCALE;
    sunGlow.scale.set(glowSize, glowSize, 1);
    sunGlow.position.copy(sun.position);
    scene.add(sunGlow);

    // Star field. Equatorial (RA/Dec) -> scene frame: the vernal equinox is +x,
    // the celestial north pole is Earth's tilted pole (0, cos e, sin e), and the
    // third axis completes a right-handed set. Same rotation as Earth's globe.
    const starField = new THREE.Group();
    const starTexture = makeStarTexture();
    const starSprites: { sprite: THREE.Sprite; px: number; name: string; lightYears: number; spectral: string; fact?: string }[] = [];
    // Anything on the sky that gets a hover label.
    const skyPickables: { object: THREE.Object3D; px: number; name: string; lightYears: number; spectral?: string; fact?: string }[] = [];
    {
      const e = THREE.MathUtils.degToRad(OBLIQUITY_DEG);
      const e1 = new THREE.Vector3(1, 0, 0);
      const e2 = new THREE.Vector3(0, -Math.sin(e), -Math.cos(e));
      const e3 = new THREE.Vector3(0, Math.cos(e), -Math.sin(e));
      for (const star of STARS) {
        const ra = THREE.MathUtils.degToRad(star.raDeg);
        const dec = THREE.MathUtils.degToRad(star.decDeg);
        const pos = new THREE.Vector3()
          .addScaledVector(e1, Math.cos(dec) * Math.cos(ra))
          .addScaledVector(e2, Math.cos(dec) * Math.sin(ra))
          .addScaledVector(e3, Math.sin(dec))
          .multiplyScalar(STAR_SPHERE_RADIUS);
        const material = new THREE.SpriteMaterial({
          map: starTexture,
          color: SPECTRAL_COLORS[star.spectral],
          blending: THREE.AdditiveBlending,
          depthWrite: false,
          depthTest: true, // hidden by anything nearer (Earth's occluder, planets)
          transparent: true,
        });
        const sprite = new THREE.Sprite(material);
        sprite.renderOrder = 1; // draw last so depth from every body is already there (renderOrder isn't inherited from the group)
        sprite.position.copy(pos);
        // Sprite size in pixels from magnitude.
        const px = Math.max(STAR_MIN_PX, STAR_BASE_PX * Math.pow(10, -STAR_MAG_EXPONENT * star.magnitude));
        starSprites.push({ sprite, px, name: star.name, lightYears: star.lightYears, spectral: star.spectral, fact: star.fact });
        skyPickables.push({ object: sprite, px, name: star.name, lightYears: star.lightYears, spectral: star.spectral, fact: star.fact });
        starField.add(sprite);
      }
    }
    // Sprites live at a fixed distance, so a pixel size maps to a fixed world size
    // for a given canvas height; recomputed on resize.
    const updateStarSizes = () => {
      const h = renderer.domElement.clientHeight || 1;
      const worldPerPx = (2 * STAR_SPHERE_RADIUS * Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2))) / h;
      for (const { sprite, px } of starSprites) sprite.scale.setScalar(px * worldPerPx);
    };
    updateStarSizes();

    starField.visible = usePageStore.getState().starsVisible;
    starFieldRef.current = starField;
    scene.add(starField);

    // Screen-space star hit test: within the sprite's core-ish radius or a minimum.
    const pickStar = (clientX: number, clientY: number) => {
      const rect = renderer.domElement.getBoundingClientRect();
      const px = clientX - rect.left;
      const py = clientY - rect.top;
      let best: (typeof skyPickables)[number] | null = null;
      let bestD = Infinity;
      if (!starField.visible) return null;
      for (const s of skyPickables) {
        if (!s.object.visible) continue;
        s.object.getWorldPosition(tmpA);
        tmpB.copy(tmpA).project(camera);
        if (tmpB.z > 1) continue;
        const sx = ((tmpB.x + 1) / 2) * rect.width;
        const sy = ((1 - tmpB.y) / 2) * rect.height;
        const d = Math.hypot(sx - px, sy - py);
        const tolerance = Math.max(PICK_MIN_PX, s.px * 0.35);
        if (d <= tolerance && d < bestD) { best = s; bestD = d; }
      }
      return best;
    };

    // Create latitude and longitude lines
    const createLatitudeLines = () => {
      const latitudes: THREE.Line[] = [];
      for (let i = -80; i <= 80; i += 20) {
        const phi = (90 - i) * (Math.PI / 180);
        const radius = Math.sin(phi) * globeRadius;
        const y = Math.cos(phi) * globeRadius;
        const curve = new THREE.EllipseCurve(0, 0, radius, radius, 0, 2 * Math.PI, false, 0);
        const points = curve.getPoints(64);
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const positions = geometry.attributes.position.array as Float32Array;
        for (let j = 0; j < positions.length; j += 3) {
          const x = positions[j];
          const z = positions[j + 1];
          positions[j] = x;
          positions[j + 1] = y;
          positions[j + 2] = z;
        }
        const lineMaterial = new THREE.LineBasicMaterial({
          color: color,
          transparent: true,
          opacity: 0.1
        });
        const line = new THREE.Line(geometry, lineMaterial);
        latitudes.push(line);
      }
      return latitudes;
    };

    const createLongitudeLines = () => {
      const longitudes: THREE.Line[] = [];
      for (let i = 0; i < 180; i += 20) {
        const curve = new THREE.EllipseCurve(0, 0, globeRadius, globeRadius, 0, Math.PI, false, 0);
        const points = curve.getPoints(32);
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const lineMaterial = new THREE.LineBasicMaterial({
          color: color,
          transparent: true,
          opacity: 0.1
        });
        const line = new THREE.Line(geometry, lineMaterial);
        line.rotation.y = (i * Math.PI) / 180;
        longitudes.push(line);
      }
      return longitudes;
    };

    // createLatitudeLines().forEach(line => globeGroup.add(line));
    // createLongitudeLines().forEach(line => globeGroup.add(line));

    // Load GeoJSON data once
    loadGeoJsonData()
      .then((geoJson) => {
        if (geoJson && sceneRef.current && globeGroup.parent) {
          drawGeoJsonContoursAndFill(geoJson, globeGroup, globeRadius + 0.002, "#ffffff", 0.85);
        }
      });

    // Ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.1);
    scene.add(ambientLight);


    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enableZoom = true;
    controls.zoomSpeed = 0.8;
    controls.enablePan = false;
    controls.minDistance = DEFAULT_CAMERA_DISTANCE; // can't zoom in past the default view
    controls.maxDistance = MAX_CAMERA_DISTANCE;
    controlsRef.current = controls;

    // Orbiters: anything that goes around the Sun. Each sits in an inclined
    // pivot; its position is computed from an angle each frame (not by rotating
    // the pivot), so axial tilts stay fixed in space.
    // Keplerian orbits: `orbitRadius` is the semi-major axis, `angle` the mean
    // anomaly. Eccentric orbits solve Kepler's equation each frame; e = 0 is a circle.
    // Positions come from the simulated date: M(t) = M0 + n (t - J2000), with the
    // orbit plane set by node (rotation about y) and inclination (about the node
    // line), and perihelion measured from the node inside that plane.
    type Orbiter = {
      object: THREE.Object3D; pivot: THREE.Group; orbitRadius: number; e: number;
      M0: number; n: number;                 // mean anomaly at J2000 (rad), mean motion (rad/day)
      argPeri: number; node: number;         // rad
      periRate?: number; nodeRate?: number;  // rad/day (the Moon precesses)
      spin?: THREE.Object3D; rotationDays?: number; spinPhase?: number;
      tidallyLocked?: boolean; faceOffset?: number;
    };
    const orbiters: Orbiter[] = [];
    const orbitRings: THREE.LineLoop[] = [];
    const ringByObject = new Map<THREE.Object3D, THREE.LineLoop>();
    // Position in the orbit plane for eccentric anomaly E (angle measured from perihelion).
    const keplerPoint = (a: number, e: number, perihelion: number, E: number, out: THREE.Vector3) => {
      const nu = 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2));
      const r = a * (1 - e * Math.cos(E));
      const theta = nu + perihelion;
      out.set(r * Math.cos(theta), 0, -r * Math.sin(theta));
      return theta;
    };
    const solveKepler = (M: number, e: number) => {
      let E = e < 0.8 ? M : Math.PI;
      for (let i = 0; i < 5; i++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
      return E;
    };
    type OrbitOpts = {
      spin?: THREE.Object3D; rotationDays?: number; spinPhaseDeg?: number; parent?: THREE.Object3D;
      tidallyLocked?: boolean; faceOffsetDeg?: number; eccentricity?: number;
      perihelionDeg?: number;      // longitude of perihelion (from the reference direction)
      nodeDeg?: number;            // longitude of the ascending node
      meanLongitudeDeg?: number;   // mean longitude at J2000 (preferred)
      meanAnomalyDeg?: number;     // mean anomaly at J2000 (fallback)
      periRateDegPerDay?: number; nodeRateDegPerDay?: number;
    };
    const RING_SAG_TOLERANCE = EARTH_RADIUS * (100 / 6371); // 100 km at true scale; the same fraction of Earth's drawn radius in compact mode
    const addOrbiter = (object: THREE.Object3D, orbitRadius: number, periodDays: number, inclinationDeg: number, o: OrbitOpts = {}) => {
      const parent = o.parent ?? scene;
      const eccentricity = o.eccentricity ?? 0;
      const nodeDeg = o.nodeDeg ?? 0;
      const periLonDeg = o.perihelionDeg ?? 0;
      const pivot = new THREE.Group();
      pivot.rotation.order = 'YXZ';
      pivot.rotation.y = THREE.MathUtils.degToRad(nodeDeg);
      pivot.rotation.x = THREE.MathUtils.degToRad(inclinationDeg);
      pivot.add(object);
      parent.add(pivot);
      const perihelion = THREE.MathUtils.degToRad(periLonDeg - nodeDeg); // argument of perihelion
      // Faint orbit ring: an ellipse with the parent at one focus. A polygon's
      // chords sag inside the true curve by ~a*pi^2/(2N^2), so pick N from the
      // orbit size to keep that under RING_SAG_TOLERANCE (else a small body seen
      // up close sits visibly outside its own line: Pluto was 20 radii off at
      // 1024 segments). Vertices are spaced in true anomaly, which puts them
      // where an eccentric orbit bends most, near perihelion.
      const ringPoints: THREE.Vector3[] = [];
      const RING_SEGMENTS = THREE.MathUtils.clamp(Math.ceil(Math.PI * Math.sqrt(orbitRadius / (2 * RING_SAG_TOLERANCE))), 1024, 32768);
      for (let i = 0; i < RING_SEGMENTS; i++) {
        const pt = new THREE.Vector3();
        const nu = (i / RING_SEGMENTS) * Math.PI * 2;
        const E = 2 * Math.atan2(Math.sqrt(1 - eccentricity) * Math.sin(nu / 2), Math.sqrt(1 + eccentricity) * Math.cos(nu / 2));
        keplerPoint(orbitRadius, eccentricity, perihelion, E, pt);
        ringPoints.push(pt);
      }
      const ring = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(ringPoints),
        new THREE.LineBasicMaterial({ color: ORBIT_RING_STYLE.color, transparent: true, opacity: ORBIT_RING_STYLE.opacity })
      );
      pivot.add(ring);
      orbitRings.push(ring);
      ringByObject.set(object, ring);
      const M0deg = o.meanLongitudeDeg !== undefined ? o.meanLongitudeDeg - periLonDeg : (o.meanAnomalyDeg ?? 0);
      orbiters.push({
        object, pivot, orbitRadius, e: eccentricity,
        M0: THREE.MathUtils.degToRad(M0deg), n: (2 * Math.PI) / periodDays,
        argPeri: perihelion, node: THREE.MathUtils.degToRad(nodeDeg),
        periRate: o.periRateDegPerDay !== undefined ? THREE.MathUtils.degToRad(o.periRateDegPerDay) : undefined,
        nodeRate: o.nodeRateDegPerDay !== undefined ? THREE.MathUtils.degToRad(o.nodeRateDegPerDay) : undefined,
        spin: o.spin, rotationDays: o.rotationDays, spinPhase: THREE.MathUtils.degToRad(o.spinPhaseDeg ?? 0),
        tidallyLocked: o.tidallyLocked ?? false, faceOffset: THREE.MathUtils.degToRad(o.faceOffsetDeg ?? 0),
      });
    };
    const updateOrbiters = (jd: number) => {
      const t = jd - J2000;
      for (const o of orbiters) {
        let argPeri = o.argPeri;
        if (o.periRate !== undefined || o.nodeRate !== undefined) {
          // Precessing elements (the Moon): node and perigee drift with time.
          const node = o.node + (o.nodeRate ?? 0) * t;
          const periLon = o.argPeri + o.node + (o.periRate ?? 0) * t;
          o.pivot.rotation.y = node;
          argPeri = periLon - node;
        }
        const M = o.M0 + o.n * t;
        const E = o.e > 0 ? solveKepler(((M % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI), o.e) : M;
        const theta = keplerPoint(o.orbitRadius, o.e, argPeri, E, o.object.position);
        if (o.spin && o.rotationDays) o.spin.rotation.y = (o.spinPhase ?? 0) + (2 * Math.PI * t) / o.rotationDays;
        // Tidal lock: one rotation per orbit, with the map's centre (+x on the
        // sphere) always pointing back at the parent.
        if (o.tidallyLocked) o.object.rotation.y = theta + Math.PI + (o.faceOffset ?? 0);
      }
    };

    // Earth (its spin is driven separately, gated by auto-rotate).
    const earthOrbitRadius = orbitRadiusForAU(EARTH_ORBIT_AU);
    scene.remove(earthSystem);
    addOrbiter(earthSystem, earthOrbitRadius, EARTH_YEAR_DAYS, 0, {
      eccentricity: EARTH_ECCENTRICITY, perihelionDeg: EARTH_PERIHELION_DEG, meanLongitudeDeg: EARTH_MEAN_LONGITUDE_DEG,
    });
    // The Moon, in Earth's frame, from the lunar theory (see lunar.ts): position
    // and tidal-lock rotation are set every frame. Its ring is the theory's path
    // over one orbit around the current date, refreshed as the date moves.
    earthSystem.add(moon);
    const MOON_KM_TO_UNITS = MOON_ORBIT_RADIUS / 384400; // true scale: km -> units; compact: same shape, squeezed
    const moonPosAt = (jd: number, out: THREE.Vector3) => {
      const k = moonPositionJ2000Km(jd);
      return out.set(k.x * MOON_KM_TO_UNITS, k.z * MOON_KM_TO_UNITS, -k.y * MOON_KM_TO_UNITS);
    };
    const MOON_RING_SAMPLES = 256;
    const moonRingPositions = new Float32Array((MOON_RING_SAMPLES + 1) * 3);
    const moonRingGeometry = new THREE.BufferGeometry();
    moonRingGeometry.setAttribute('position', new THREE.BufferAttribute(moonRingPositions, 3));
    const moonRing = new THREE.Line(moonRingGeometry, new THREE.LineBasicMaterial({ color: ORBIT_RING_STYLE.color, transparent: true, opacity: ORBIT_RING_STYLE.opacity }));
    earthSystem.add(moonRing);
    orbitRings.push(moonRing as unknown as THREE.LineLoop);
    ringByObject.set(moon, moonRing as unknown as THREE.LineLoop);
    let moonRingJD = -Infinity;
    // A frame at the Moon's position that does not spin with it: Moon-centred mission segments live here.
    const moonFrame = new THREE.Group();
    earthSystem.add(moonFrame);
    const updateMoon = (jd: number) => {
      moonPosAt(jd, moon.position);
      moonFrame.position.copy(moon.position);
      // Tidal lock: the map's centre (+x on the sphere) faces Earth.
      moon.rotation.y = Math.atan2(-moon.position.z, moon.position.x) + Math.PI;
      if (Math.abs(jd - moonRingJD) > 0.25) {
        moonRingJD = jd;
        const v = new THREE.Vector3();
        for (let i = 0; i <= MOON_RING_SAMPLES; i++) {
          moonPosAt(jd - MOON_ORBIT_DAYS / 2 + (i / MOON_RING_SAMPLES) * MOON_ORBIT_DAYS, v);
          moonRingPositions.set([v.x, v.y, v.z], i * 3);
        }
        (moonRingGeometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
      }
    };

    // Bodies that can be focused (clicked).
    const sunBody: Body = { name: 'Sun', object: sun, visual: sun, radius: SUN_RADIUS, parent: null, systemRadius: earthOrbitRadius, scale: 1 };
    const earthBody: Body = { name: 'Earth', object: earthSystem, visual: globeGroup, radius: EARTH_RADIUS, parent: sunBody, systemRadius: MOON_ORBIT_RADIUS, scale: 1 };
    const moonBody: Body = { name: 'Moon', object: moon, visual: moon, radius: MOON_RADIUS, parent: earthBody, systemRadius: 0, scale: 1 };
    const bodies: Body[] = [sunBody, earthBody, moonBody];

    // Other planets, from the table.
    const planetDisposables: { geometry: THREE.BufferGeometry; material: THREE.Material }[] = [];
    const textureLoader = new THREE.TextureLoader();
    const textures: THREE.Texture[] = [];
    let outermostOrbit = earthOrbitRadius; // basis for the max zoom-out
    const tiltedByPlanet = new Map<string, THREE.Group>(); // moons orbit in their planet's equatorial plane
    for (const spec of PLANETS) {
      const radius = EARTH_RADIUS * spec.radiusEarths;
      // More segments for bigger bodies so large wireframes don't look like
      // polygons; textured bodies always get enough for a round silhouette.
      const segments = spec.texture ? 48 : THREE.MathUtils.clamp(Math.round(12 + radius * 2.5), 16, 48);
      const geometry = new THREE.SphereGeometry(radius, segments, segments);
      const solid = spec.solid || !!spec.texture;
      const material = new THREE.MeshBasicMaterial({ color: spec.texture ? 0xffffff : spec.color, wireframe: !solid, transparent: true, opacity: solid ? 1 : 0.8 });
      if (spec.texture) {
        const tex = textureLoader.load(spec.texture);
        tex.colorSpace = THREE.SRGBColorSpace;
        material.map = tex;
        material.needsUpdate = true;
        textures.push(tex);
      }
      const mesh = new THREE.Mesh(geometry, material);
      planetDisposables.push({ geometry, material });
      const holder = new THREE.Group(); // position-only; the tilted body spins inside it
      const tilted = new THREE.Group(); // carries the axial tilt; moons' pivots attach here
      tiltedByPlanet.set(spec.name, tilted);
      // The visual group (planet mesh + rings) is what the size floor scales.
      // It's a sibling of the moon pivots, so inflating a distant planet never
      // inflates its moons or their orbits along with it.
      const visual = new THREE.Group();
      visual.add(mesh);
      tilted.add(visual);
      holder.add(tilted);
      if (spec.rings) {
        const ringInner = radius * spec.rings.innerRadii;
        const ringOuter = radius * spec.rings.outerRadii;
        const ringGeometry = new THREE.RingGeometry(ringInner, ringOuter, 128);
        const ringMaterial = new THREE.MeshBasicMaterial({ color: spec.rings.texture ? 0xffffff : spec.rings.color, transparent: true, opacity: spec.rings.texture ? 1 : spec.rings.opacity, side: THREE.DoubleSide, depthWrite: false });
        if (spec.rings.texture) {
          // RingGeometry's UVs are planar; remap them radially so a strip texture
          // (inner edge at u=0, outer edge at u=1) wraps around the ring.
          const pos = ringGeometry.attributes.position;
          const uv = ringGeometry.attributes.uv;
          for (let i = 0; i < pos.count; i++) {
            const r = Math.hypot(pos.getX(i), pos.getY(i));
            uv.setXY(i, (r - ringInner) / (ringOuter - ringInner), 0.5);
          }
          uv.needsUpdate = true;
          const ringTex = textureLoader.load(spec.rings.texture);
          ringTex.colorSpace = THREE.SRGBColorSpace;
          ringMaterial.map = ringTex;
          ringMaterial.needsUpdate = true;
          textures.push(ringTex);
        }
        const ringMesh = new THREE.Mesh(ringGeometry, ringMaterial);
        ringMesh.rotation.x = -Math.PI / 2; // lie in the equatorial plane
        visual.add(ringMesh);
        planetDisposables.push({ geometry: ringGeometry, material: ringMaterial });
      }
      const orbitRadius = orbitRadiusForAU(spec.au);
      addOrbiter(holder, orbitRadius, spec.periodDays, spec.inclinationDeg, {
        spin: mesh, rotationDays: spec.rotationDays, spinPhaseDeg: spec.spinPhaseDeg,
        eccentricity: spec.eccentricity, perihelionDeg: spec.perihelionDeg, nodeDeg: spec.nodeDeg,
        meanLongitudeDeg: spec.meanLongitudeDeg, meanAnomalyDeg: spec.phaseDeg,
      });
      // Axial tilt: lean the pole by axialTiltDeg toward ecliptic longitude poleLonDeg
      // (scene x = longitude 0; a rotation about y advances longitude). The pivot is
      // already rotated by the orbit's node and inclination, so undo that first.
      {
        const lean = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, THREE.MathUtils.degToRad((spec.poleLonDeg ?? 180) - 180), THREE.MathUtils.degToRad(spec.axialTiltDeg ?? 0), 'YZX'));
        tilted.quaternion.copy((holder.parent as THREE.Object3D).quaternion).invert().multiply(lean);
      }
      bodies.push({ name: spec.name, object: holder, visual, radius, parent: sunBody, systemRadius: 0, scale: 1, focusRadii: spec.focusRadii });
      outermostOrbit = Math.max(outermostOrbit, orbitRadius);
      if (spec.name === WIDE_VIEW_PLANET) sunBody.systemRadius = orbitRadius;
    }

    // Moons from the table: each orbits inside its planet's position-only
    // holder, so it follows the planet without inheriting its spin.
    for (const spec of MOONS) {
      const planetBody = bodies.find((b) => b.name === spec.planet);
      if (!planetBody) continue;
      const radius = EARTH_RADIUS * spec.radiusEarths;
      // Real-sized moons get a wireframe like the planets; km-scale ones that
      // only ever render as dots stay solid so they read as a point.
      const isDot = radius < 0.03; // km-scale moons (Phobos, Deimos); Mimas at 0.04 is a real sphere
      const solid = isDot || !!spec.texture || !!spec.solid;
      const segments = isDot ? 8 : spec.texture ? 48 : THREE.MathUtils.clamp(Math.round(12 + radius * 2.5), 16, 48);
      const geometry = new THREE.SphereGeometry(radius, segments, segments);
      const material = new THREE.MeshBasicMaterial({ color: spec.texture ? 0xffffff : spec.color, wireframe: !solid, transparent: true, opacity: solid ? 1 : 0.8 });
      if (spec.texture) {
        const tex = textureLoader.load(spec.texture);
        tex.colorSpace = THREE.SRGBColorSpace;
        material.map = tex;
        material.needsUpdate = true;
        textures.push(tex);
      }
      const mesh = new THREE.Mesh(geometry, material);
      planetDisposables.push({ geometry, material });
      const orbitRadius = planetBody.radius * spec.orbitPlanetRadii;
      // Table moon inclinations are given to the planet's equator, so they orbit
      // inside the planet's tilted group (Titan then sits in Saturn's ring plane).
      addOrbiter(mesh, orbitRadius, spec.periodDays, spec.inclinationDeg, {
        parent: tiltedByPlanet.get(spec.planet) ?? planetBody.object, tidallyLocked: true,
        faceOffsetDeg: spec.faceOffsetDeg, meanAnomalyDeg: spec.phaseDeg,
      });
      bodies.push({ name: spec.name, object: mesh, visual: mesh, radius, parent: planetBody, systemRadius: 0, scale: 1 });
      planetBody.systemRadius = Math.max(planetBody.systemRadius, orbitRadius);
    }
    let simJD = jdNow();
    simJDRef.current = simJD;
    updateOrbiters(simJD);
    updateMoon(simJD);
    const earthPosition = new THREE.Vector3();
    earthSystem.getWorldPosition(earthPosition);
    const worldPos = (b: Body, out: THREE.Vector3) => b.object.getWorldPosition(out);

    // Focus state: the camera target follows `focus`. A transition eases the
    // target (and optionally the distance) from the previous body.
    let focus: Body = earthBody;
    // For zoomTo transitions, `startOffset` is the camera's offset from the old
    // body at the start; the camera then flies straight toward the new body
    // along the line of sight, so it never passes through the parent.
    let transition: { from: Body; t: number; distTo: number | null; startOffset: THREE.Vector3; seconds: number } | null = null;
    // Turning toward a star: rotates the camera's offset around the focus so the
    // star ends up just beside the focused body's disc (a little past its
    // angular radius), rather than hidden behind it. Distance is kept.
    let aim: { from: THREE.Vector3; to: THREE.Vector3; t: number; distFrom: number; distTo: number } | null = null;
    // A plain distance ease (no turn), used by `launch` to pull back from a close-up.
    let zoomEase: { t: number; distFrom: number; distTo: number } | null = null;
    const LAUNCH_MIN_RADII = 40; // far enough to watch a craft leave the focused body
    const AIM_SECONDS = 1.0;
    const AIM_MARGIN_RAD = THREE.MathUtils.degToRad(8); // clearance beyond the disc's edge
    // Closer than this the star would land outside the frame (disc ~17 degrees at
    // the close-up + margin > the 25 degree half-height), so ease out to it first.
    const AIM_MIN_RADII = 8;
    // A star label engaged by `fly` stays pinned until a drag/zoom or focus change;
    // mouse hover can temporarily replace it but not clear it.
    type StarInfo = { name: string; lightYears: number; spectral?: string; fact?: string };
    let pinnedStar: StarInfo | null = null;
    const clearPinnedStar = () => {
      if (!pinnedStar) return;
      pinnedStar = null;
      if (hoveredStarRef.current !== null) {
        hoveredStarRef.current = null;
        onStarHover?.(null);
      }
    };
    const focusPoint = new THREE.Vector3();
    const tmpA = new THREE.Vector3();
    const tmpB = new THREE.Vector3();

    const halfWidthPerUnit = () => Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2)) * camera.aspect;
    const fitDistance = (extent: number) => (extent * FIT_MARGIN) / halfWidthPerUnit();
    // The root frame (the Sun) is only ever a wide view: its closest zoom is
    // where its whole system fits on screen. Other bodies allow a close-up.
    // Closest zoom: a few radii for everything, the Sun included.
    const minDistanceFor = (b: Body) => Math.max(b.radius * MIN_DISTANCE_RADII, MIN_CLOSE_DISTANCE);
    // Where the Sun's system fits on screen: its click fly-in, and the basis for the max zoom-out.
    const wideViewDistance = (b: Body) => fitDistance(b.systemRadius + b.radius);

    const shownInTerminal = new Set<string>();
    const setFocus = (next: Body, opts: { zoomTo?: boolean; fromClick?: boolean } = {}) => {
      hasInteracted = true; // a click or `fly` counts as interaction
      // Surface photos shown in the terminal the first time a body is focused.
      const SURFACE_PHOTOS: Record<string, [string, string]> = {
        Titan: ['/titan-huygens-1.jpg,/titan-huygens-2.jpg,/titan-huygens-3.jpg,/titan-huygens-4.jpg,/titan-huygens-5.jpg,/titan-huygens-6.jpg,/titan-huygens.jpg', "The Huygens lander on Titan, 14 January 2005. My mind was completely blown when I learned we had landed and imaged its surface. One of only four planets or moons we've landed on outside of Earth, the others being the Moon, Mars and Venus."],
        Venus: ['/venus-venera13.jpg', "Venera 13 on the surface of Venus, 1 March 1982. It survived 127 minutes at 457 degrees C. I find these surface images to be the most impressive accomplishment of the Soviets during the space race."],
      };
      const photo = SURFACE_PHOTOS[next.name];
      if (photo && next !== focus && !shownInTerminal.has(next.name)) {
        shownInTerminal.add(next.name);
        // A typed `fly` already echoed its command; a click didn't, so give the
        // photo the same context the terminal would have printed.
        const context = opts.fromClick ? [`__IN__${next.name.toLowerCase()}`, `Flying to ${next.name}...`] : [];
        usePageStore.getState().pushTerminalLines([...context, `__IMG__${photo[0]}`, `__DIM__${photo[1]}`]);
      }
      clearPinnedStar();
      // Clicking the already-focused body only does something when the camera
      // has drifted far enough away that flying back in is meaningful.
      const isSame = next === focus;
      if (isSame && camera.position.distanceTo(controls.target) < minDistanceFor(next) * REFOCUS_FACTOR) return;
      transition = {
        from: focus,
        t: 0,
        distTo: opts.zoomTo
          ? (next.parent ? Math.max(next.radius * (next.focusRadii ?? MIN_DISTANCE_RADII * 1.5), MIN_CLOSE_DISTANCE * 1.5) : wideViewDistance(next) * 1.1)
          : null,
        startOffset: camera.position.clone().sub(worldPos(focus, tmpA)),
        seconds: FOCUS_TRANSITION_SECONDS,
      };
      if (transition.distTo !== null) {
        // Longer flights take longer, but only logarithmically.
        const startDist = camera.position.distanceTo(worldPos(next, tmpB));
        const decades = Math.max(0, Math.log10(startDist / transition.distTo));
        transition.seconds = FOCUS_TRANSITION_SECONDS + FOCUS_SECONDS_PER_DECADE * decades;
      }
      focus = next;
    };
    let reportedFocusName: string | null | undefined;
    // The focused body's name is held back until the user first interacts
    // (scroll or drag), so the page doesn't open with "Earth" over the globe.
    let hasInteracted = false;
    const reportFocus = (dist: number) => {
      const nameLimit = focus.parent
        ? minDistanceFor(focus) * NAME_VISIBLE_FACTOR
        : wideViewDistance(focus) * 1.1 * ROOT_NAME_VISIBLE_FACTOR;
      const name = hasInteracted && dist <= nameLimit ? focus.name : null;
      if (name !== reportedFocusName) {
        reportedFocusName = name;
        onFocusChange?.(name);
      }
    };

    // Screen-space picking: a body is hit if the pointer is within its on-screen
    // radius (or a minimum pixel tolerance, so tiny bodies stay clickable).
    const pickBody = (clientX: number, clientY: number): Body | null => {
      const rect = renderer.domElement.getBoundingClientRect();
      const px = clientX - rect.left;
      const py = clientY - rect.top;
      // Tolerance scales with drawn size so small bodies are forgiving and big
      // ones are exact. When several qualify, the smallest on screen wins, so a
      // moon can be picked while it sits inside its planet's outline.
      // Occlusion: a body whose centre is behind another body's on-screen disc
      // (at the click point) is not pickable, so a moon behind its planet can't
      // be clicked through it.
      const tanHalfFov = Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2));
      const projected = bodies.map((b) => {
        worldPos(b, tmpA);
        const camDist = tmpA.distanceTo(camera.position);
        tmpB.copy(tmpA).project(camera);
        const sx = ((tmpB.x + 1) / 2) * rect.width;
        const sy = ((1 - tmpB.y) / 2) * rect.height;
        const screenRadius = ((b.radius * b.scale) / (camDist * tanHalfFov)) * (rect.height / 2);
        return { b, camDist, behindCamera: tmpB.z > 1, sx, sy, screenRadius, d: Math.hypot(sx - px, sy - py) };
      });
      const occluded = (c: (typeof projected)[number]) =>
        projected.some((o) => o !== c && !o.behindCamera && o.b.visual.visible && o.d <= o.screenRadius && o.camDist < c.camDist);

      let best: Body | null = null;
      let bestRadius = Infinity;
      for (const c of projected) {
        if (c.behindCamera) continue;
        if (!c.b.visual.visible) continue; // hidden (e.g. a moon too small to draw)
        const tolerance = c.screenRadius >= PICK_CAP_PX
          ? c.screenRadius
          : Math.max(PICK_MIN_PX, c.screenRadius * PICK_RADIUS_MULTIPLE);
        if (c.d <= tolerance && c.screenRadius < bestRadius && !occluded(c)) {
          best = c.b;
          bestRadius = c.screenRadius;
        }
      }
      return best;
    };

    // Orbit rings: hidden by default, shown with the `orbits` command.
    let ringsShown = usePageStore.getState().orbitsHighlighted;
    const setOrbitStyle = (on: boolean) => { ringsShown = on; };
    setOrbitStyleRef.current = setOrbitStyle;

    controls.target.copy(earthPosition);
    // Start on the -z side: the pole leans toward -z, so from here it tilts
    // toward the viewer like a desk globe.
    camera.position.copy(earthPosition).add(new THREE.Vector3(0, 0, -DEFAULT_CAMERA_DISTANCE));
    controls.update();
    reportFocus(DEFAULT_CAMERA_DISTANCE);

    // User interaction handlers
    const onControlsStart = () => {
      hasInteracted = true;
      clearPinnedStar(); // a drag or zoom releases the star label
      renderer.domElement.style.cursor = 'grabbing';
    };
    // 'change' fires only when the camera actually moves (a drag or zoom),
    // not on a plain click, so a click never stops the spin.
    const onControlsChange = () => {
      if (isPointerDownRef.current) autoRotateRef.current = false;
    };
    const onControlsEnd = () => {
      renderer.domElement.style.cursor = 'grab';
      autoRotateRef.current = true;
    };
    const onPointerDown = (e: PointerEvent) => {
      isPointerDownRef.current = true;
      pointerDownPosRef.current = { x: e.clientX, y: e.clientY };
    };
    const onPointerUp = () => { isPointerDownRef.current = false; };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && focus.parent) setFocus(focus.parent);
    };

    const onMouseMove = (event: MouseEvent) => {
      if (!camera || !globeGroup) return;

      const rect = renderer.domElement.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1
      );

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);

      const intersects = raycaster.intersectObjects(
        apolloGroupRef.current?.visible ? [...dotsRef.current, ...moonDotsRef.current] : dotsRef.current,
        false,
      );

      if (intersects.length > 0 && intersects[0].object.userData.dot) {
        const dot = intersects[0].object.userData.dot as PersonaDot;
        if (hoveredDotRef.current?.id !== dot.id) {
          hoveredDotRef.current = dot;
          onDotHover?.(dot);
        }
        hoverPausedRef.current = true; // a dot is on Earth
        if (hoveredStarRef.current !== null) {
          hoveredStarRef.current = null;
          onStarHover?.(null);
        }
        renderer.domElement.style.cursor = 'pointer';
      } else {
        if (hoveredDotRef.current !== null) {
          hoveredDotRef.current = null;
          onDotHover?.(null);
        }
        const body = pickBody(event.clientX, event.clientY);
        hoverPausedRef.current = body === earthBody;
        const farFromFocus = camera.position.distanceTo(controls.target) >= minDistanceFor(focus) * REFOCUS_FACTOR;
        const name = body && (body !== focus || farFromFocus) ? body.name : null;
        if (hoveredBodyRef.current !== name) {
          hoveredBodyRef.current = name;
          onBodyHover?.(name);
        }
        // Stars (not focusable): label only, and only when nothing nearer is hovered.
        const picked = body ? null : pickStar(event.clientX, event.clientY);
        const shown: StarInfo | null = picked
          ? { name: picked.name, lightYears: picked.lightYears, spectral: picked.spectral, fact: picked.fact }
          : body ? null : pinnedStar; // nothing under the pointer: keep the pinned star
        const starName = shown ? shown.name : null;
        if (hoveredStarRef.current !== starName) {
          hoveredStarRef.current = starName;
          onStarHover?.(shown);
        }
        renderer.domElement.style.cursor = name || picked ? 'pointer' : (autoRotateRef.current ? 'grab' : 'grabbing');
      }
    };

    const onMouseClick = (event: MouseEvent) => {
      if (!camera || !globeGroup) return;

      // A click that moved the pointer is a drag; ignore it.
      const down = pointerDownPosRef.current;
      if (down && Math.hypot(event.clientX - down.x, event.clientY - down.y) > DRAG_THRESHOLD_PX) return;

      // 1. Location dots take priority.
      const rect = renderer.domElement.getBoundingClientRect();
      const mouse = new THREE.Vector2();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(globeGroup.children, true);
      for (const intersect of intersects) {
        if (intersect.object.userData && intersect.object.userData.dot && intersect.object.userData.dot.info) {
          onDotClick?.(intersect.object.userData.dot);
          return;
        }
      }

      // 2. A body: make it the reference frame and zoom to it.
      //    Clicking empty space does nothing.
      const body = pickBody(event.clientX, event.clientY);
      if (body) { setFocus(body, { zoomTo: true, fromClick: true }); return; }

      // 3. A star: turn toward it, same as the terminal.
      const picked = pickStar(event.clientX, event.clientY);
      if (picked) {
        const star = starSprites.find((s) => s.name === picked.name);
        if (star) aimAtStarRef.current?.(star);
      }
    };

    controls.addEventListener('start', onControlsStart);
    controls.addEventListener('change', onControlsChange);
    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('keydown', onKeyDown);
    controls.addEventListener('end', onControlsEnd);
    const onMouseLeave = () => { hoverPausedRef.current = false; };
    renderer.domElement.addEventListener('mousemove', onMouseMove);
    renderer.domElement.addEventListener('mouseleave', onMouseLeave);
    renderer.domElement.addEventListener('click', onMouseClick);

    // ---- Mission tracking ----
    // A trajectory is one or more segments of [jd, x, y, z] in AU (ecliptic J2000;
    // x = equinox, y = longitude 90, z = north). Scene axes: x, y = z_h, z = -y_h.
    // Each segment is drawn in the frame of its centre (Sun, Earth or Moon), so a
    // lunar orbit stays a clean loop around the moving Moon. The line is drawn up to
    // the simulated date, with a marker at the tip that is itself a focusable body.
    type SegmentCenter = 'Sun' | 'Earth' | 'Moon';
    type Segment = { center: SegmentCenter; points: number[][]; line: THREE.Line; positions: Float32Array; pristine: Float32Array; lastTipIndex: number; group: THREE.Group };
    type Mission = { spec: (typeof MISSIONS)[number]; segments: Segment[]; active: number; marker: THREE.Mesh; body: Body; arrived: boolean };
    let mission: Mission | null = null;
    const toScene = (x: number, y: number, z: number, out: THREE.Vector3) => out.set(x * orbitScale, z * orbitScale, -y * orbitScale);
    const frameFor = (center: SegmentCenter) => (center === 'Earth' ? earthSystem : center === 'Moon' ? moonFrame : scene);
    const clearMission = () => {
      if (!mission) return;
      for (const seg of mission.segments) {
        seg.group.parent?.remove(seg.group);
        seg.line.geometry.dispose();
        (seg.line.material as THREE.Material).dispose();
      }
      mission.marker.parent?.remove(mission.marker);
      mission.marker.geometry.dispose();
      (mission.marker.material as THREE.Material).dispose();
      const i = bodies.indexOf(mission.body);
      if (i >= 0) bodies.splice(i, 1);
      if (focus === mission.body) { focus = earthBody; transition = null; }
      mission = null;
    };
    const loadMission = async (id: string | null) => {
      clearMission();
      if (!id) return;
      const spec = MISSIONS.find((m) => m.id === id);
      if (!spec) return;
      const res = await fetch(spec.file);
      if (!res.ok) return;
      const data = await res.json();
      const raw: { center: SegmentCenter; points: number[][] }[] = data.segments ?? [{ center: spec.center, points: data.points }];
      const v = new THREE.Vector3();
      const segments: Segment[] = raw.map((r) => {
        const group = new THREE.Group();
        frameFor(r.center).add(group);
        const positions = new Float32Array((r.points.length + 1) * 3); // +1: a slot for the interpolated tip
        r.points.forEach((p, i) => { toScene(p[1], p[2], p[3], v); positions.set([v.x, v.y, v.z], i * 3); });
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setDrawRange(0, 0);
        const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: 0x66ccff, transparent: true, opacity: 0.95 }));
        group.add(line);
        return { center: r.center, points: r.points, line, positions, pristine: positions.slice(), lastTipIndex: -1, group };
      });
      const markerRadius = EARTH_RADIUS * 0.02; // tiny; the pixel floor keeps it visible as a dot
      const marker = new THREE.Mesh(new THREE.SphereGeometry(markerRadius, 8, 8), new THREE.MeshBasicMaterial({ color: 0x66ccff }));
      segments[0].group.add(marker);
      const body: Body = { name: spec.name, object: marker, visual: marker, radius: markerRadius, parent: spec.center === 'Earth' ? earthBody : sunBody, systemRadius: 0, scale: 1 };
      bodies.push(body);
      mission = { spec, segments, active: 0, marker, body, arrived: false };
      // Start the clock at the first sample. Focus the craft itself (a cut, not a
      // flight), then ease the camera to the mission's preset: far out and above the
      // ecliptic, keeping the current azimuth. The camera then follows the craft for
      // the whole journey. Without a preset, just pull back.
      const startJD = segments[0].points[0][0];
      dateRequestRef.current = startJD;
      updateMission(startJD); // place the marker before focusing it
      focus = body;
      transition = null;
      aim = null;
      clearPinnedStar();
      worldPos(body, focusPoint);
      const off = camera.position.clone().sub(controls.target);
      off.setLength(Math.max(off.length(), minDistanceFor(body)));
      controls.target.copy(focusPoint);
      camera.position.copy(focusPoint).add(off);
      const d = camera.position.distanceTo(controls.target);
      if (spec.view) {
        const from = camera.position.clone().sub(controls.target).normalize();
        const azimuth = Math.atan2(-from.z, from.x); // current direction around the ecliptic
        const el = THREE.MathUtils.degToRad(spec.view.elevationDeg);
        const to = new THREE.Vector3(Math.cos(el) * Math.cos(azimuth), Math.sin(el), -Math.cos(el) * Math.sin(azimuth));
        aim = { from, to, t: 0, distFrom: d, distTo: spec.view.distanceAU * orbitScale };
      } else {
        const distTo = Math.max(d, focus.radius * LAUNCH_MIN_RADII);
        if (distTo > d) zoomEase = { t: 0, distFrom: d, distTo };
      }
    };
    trackRef.current = (id) => { loadMission(id); };
    // Restores the sample slot a segment's tip last overwrote.
    const restoreTip = (seg: Segment) => {
      if (seg.lastTipIndex >= 0 && seg.lastTipIndex < seg.points.length) {
        const k = seg.lastTipIndex * 3;
        seg.positions.set(seg.pristine.subarray(k, k + 3), k);
        (seg.line.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
      }
      seg.lastTipIndex = -1;
    };
    // Advances the drawn portion of the trajectory to the current date.
    const updateMission = (jd: number) => {
      if (!mission) return;
      // Arrival footage etc.: pushed to the terminal once, when the clock first reaches the date.
      if (mission.spec.arrival && !mission.arrived && jd >= mission.spec.arrival.jd) {
        mission.arrived = true;
        usePageStore.getState().pushTerminalLines(mission.spec.arrival.lines);
      }
      // The active segment is the last one that has started; earlier ones are drawn
      // in full, later ones not at all.
      let active = 0;
      for (let i = 1; i < mission.segments.length; i++) if (mission.segments[i].points[0][0] <= jd) active = i;
      mission.segments.forEach((seg, i) => {
        if (i === active) return;
        restoreTip(seg);
        seg.line.geometry.setDrawRange(0, i < active ? seg.points.length : 0);
      });
      const seg = mission.segments[active];
      if (active !== mission.active) { seg.group.add(mission.marker); mission.active = active; }
      const pts = seg.points;
      // Binary search for the last sample at or before jd.
      let lo = 0, hi = pts.length - 1;
      if (jd <= pts[0][0]) hi = 0;
      else if (jd >= pts[hi][0]) lo = hi;
      else { while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (pts[mid][0] <= jd) lo = mid; else hi = mid; } hi = lo + 1; }
      const a = pts[lo], b = pts[Math.min(hi, pts.length - 1)];
      const f = b[0] === a[0] ? 0 : THREE.MathUtils.clamp((jd - a[0]) / (b[0] - a[0]), 0, 1);
      toScene(a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f, mission.marker.position);
      // Draw all samples up to `lo`, plus a final segment to the interpolated tip.
      // The tip temporarily overwrites the next sample's slot; restore the slot we
      // used last frame so the buffer stays exact once the tip moves on.
      const n = lo + 1; // <= pts.length, the spare slot
      if (seg.lastTipIndex !== n) restoreTip(seg);
      seg.lastTipIndex = n;
      seg.positions.set([mission.marker.position.x, mission.marker.position.y, mission.marker.position.z], n * 3);
      (seg.line.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
      seg.line.geometry.setDrawRange(0, n + 1);
    };
    const pendingTrack = usePageStore.getState().trackRequest;
    if (pendingTrack && pendingTrack.seq !== handledTrackSeqRef.current) {
      handledTrackSeqRef.current = pendingTrack.seq;
      loadMission(pendingTrack.id);
    }


    // Animation loop
    let lastTime = performance.now();
    let lastViewSaveAt = 0;
    let lastViewSaved = '';
    let earthSpinBank = 0;
    let lastEarthSpinBase = THREE.MathUtils.degToRad(gmstDeg(simJD) - 180);
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate);
      const now = performance.now();
      const delta = (now - lastTime) / 1000; // seconds
      lastTime = now;

      // The clock. A `date` request jumps it; otherwise it runs at the set rate.
      const jump = dateRequestRef.current;
      if (jump !== null) { simJD = jump; dateRequestRef.current = null; }
      const before = simJD;
      simJD += delta / secondsPerDay;
      // A tracked mission freezes the clock at its last sample (a `date` past it runs on).
      if (mission) {
        const last = mission.segments[mission.segments.length - 1].points;
        const endJD = last[last.length - 1][0];
        if (before < endJD && simJD > endJD) simJD = endJD;
        else if (before === endJD && jump === null) simJD = endJD;
      }
      simJDRef.current = simJD;

      // Persist the view (focused body + camera offset) when it has settled and changed.
      if (now - lastViewSaveAt > 1000 && !transition && !aim && !zoomEase && !(mission && focus === mission.body)) {
        lastViewSaveAt = now;
        const dir = camera.position.clone().sub(controls.target).normalize();
        const snapshot = JSON.stringify({ name: focus.name, dir: dir.toArray().map((x) => Math.round(x * 1e4) / 1e4), radii: Math.round(camera.position.distanceTo(controls.target) / focus.radius * 100) / 100 });
        if (snapshot !== lastViewSaved) {
          lastViewSaved = snapshot;
          try { localStorage.setItem(VIEW_KEY, snapshot); } catch { /* storage unavailable */ }
        }
      }
      // Orbital motion and spins, all from the date.
      updateOrbiters(simJD);
      updateMoon(simJD);
      updateMission(simJD);
      sun.rotation.y = (2 * Math.PI * (simJD - J2000)) / SUN_ROTATION_DAYS;
      // Earth: Greenwich sidereal time puts lon 0 (local -x on the globe) at the
      // right direction. A hover or drag pauses the spin; the skipped angle is
      // banked so it resumes without a jump (the day/night side then lags by it).
      if (globeRef.current) {
        const base = THREE.MathUtils.degToRad(gmstDeg(simJD) - 180); // increases with time: prograde
        if (!(autoRotateRef.current && !hoverPausedRef.current)) {
          earthSpinBank += base - lastEarthSpinBase; // hold still: bank what the clock advanced
        }
        lastEarthSpinBase = base;
        globeRef.current.rotation.y = base - earthSpinBank;
      }

      // Camera focus: the target follows the focused body (easing from the
      // previous one during a transition). The camera moves with the target so
      // the user's orbit direction and zoom are kept.
      const offset = camera.position.clone().sub(controls.target);
      let dist = offset.length();
      worldPos(focus, focusPoint);
      if (transition) {
        transition.t = Math.min(1, transition.t + delta / transition.seconds);
        const k = THREE.MathUtils.smoothstep(transition.t, 0, 1);
        const newBodyPos = tmpB.copy(focusPoint);
        worldPos(transition.from, tmpA);
        if (transition.distTo !== null) {
          // Straight flight from (old body + start offset) toward the new body,
          // with the distance to it shrinking by a constant RATIO per unit time
          // (log-space easing), so the body grows at a steady visual rate instead
          // of inflating in the last few frames. The target slides in step.
          const startPos = tmpA.add(transition.startOffset);
          const toStart = startPos.clone().sub(newBodyPos);
          const startDist = Math.max(toStart.length(), 1e-6);
          const endDist = transition.distTo;
          const d = startDist * Math.pow(endDist / startDist, k);
          camera.position.copy(newBodyPos).addScaledVector(toStart.normalize(), d);
          const travelled = startDist === endDist ? 1 : (startDist - d) / (startDist - endDist);
          worldPos(transition.from, tmpA);
          focusPoint.copy(tmpA).lerp(newBodyPos, THREE.MathUtils.clamp(travelled, 0, 1));
          offset.copy(camera.position).sub(focusPoint);
          dist = offset.length();
        } else {
          focusPoint.copy(tmpA).lerp(newBodyPos, k);
        }
        if (transition.t >= 1) transition = null;
      }
      if (zoomEase) {
        zoomEase.t = Math.min(1, zoomEase.t + delta / AIM_SECONDS);
        const k = THREE.MathUtils.smoothstep(zoomEase.t, 0, 1);
        dist = THREE.MathUtils.lerp(zoomEase.distFrom, zoomEase.distTo, k);
        offset.setLength(dist);
        if (zoomEase.t >= 1) zoomEase = null;
      }
      if (aim) {
        aim.t = Math.min(1, aim.t + delta / AIM_SECONDS);
        const k = THREE.MathUtils.smoothstep(aim.t, 0, 1);
        // Spherical interpolation of the offset direction via a quaternion.
        const q = new THREE.Quaternion().setFromUnitVectors(aim.from, aim.to);
        const step = new THREE.Quaternion().slerp(q, k); // identity -> q
        // Geometric interpolation of distance: a steady visual zoom rate, which
        // matters when a launch preset pulls back by orders of magnitude.
        dist = aim.distFrom * Math.pow(aim.distTo / aim.distFrom, k); // unchanged if already there
        offset.copy(aim.from).applyQuaternion(step).setLength(dist);
        if (aim.t >= 1) aim = null;
      }
      controls.target.copy(focusPoint);
      camera.position.copy(focusPoint).add(offset);

      // Zoom limits. Focus never changes on its own: every body can be zoomed
      // out to the full system view while staying centered. Only a click (or
      // Escape) moves the frame.
      // (Limits are relaxed mid-transition so the eased distance isn't clamped.)
      const systemMax = Math.max(MAX_CAMERA_DISTANCE, fitDistance(outermostOrbit + sunBody.radius) * 1.5);
      controls.minDistance = transition ? 0.1 : minDistanceFor(focus);
      controls.maxDistance = transition ? systemMax * 10 : systemMax;
      controls.update();

      reportFocus(dist);

      // A body's own orbit ring passes through its centre; hide it while the
      // camera is close to that body so it doesn't cut across the close-up.
      {
        const ownRing = ringByObject.get(focus.object);
        for (const ring of orbitRings) ring.visible = ringsShown;
        if (ownRing) ownRing.visible = ringsShown && dist > minDistanceFor(focus) * REFOCUS_FACTOR;
      }

      // Keep the star sphere centred on the camera: pure direction, no parallax.
      starField.position.copy(camera.position);

      // Enforce a minimum on-screen size so distant bodies stay visible.
      {
        const halfHeightPx = renderer.domElement.clientHeight / 2;
        const tanHalfFov = Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2));
        const screenPx = new Map<Body, number>(); // true (unscaled) on-screen radius
        for (const b of bodies) {
          worldPos(b, tmpA);
          const camDist = tmpA.distanceTo(camera.position);
          screenPx.set(b, (b.radius / (camDist * tanHalfFov)) * halfHeightPx);
        }
        for (const b of bodies) {
          const px = screenPx.get(b)!;
          let targetPx = Math.max(px, MIN_BODY_PX);
          const hasParent = b.parent !== null;
          if (hasParent) {
            // Inflation is capped at a fraction of the (possibly floored) parent.
            // The cap only limits inflation; a body is never drawn below its true size
            // (e.g. Earth up close must not shrink because the Sun is far away).
            const parentPx = Math.max(screenPx.get(b.parent!)!, MIN_BODY_PX);
            const isMoon = b.parent !== sunBody;
            const fraction = isMoon
              ? Math.min(CHILD_MAX_PARENT_FRACTION, MOON_RATIO_TOLERANCE * (b.radius / b.parent!.radius))
              : CHILD_MAX_PARENT_FRACTION;
            let capped = Math.min(targetPx, parentPx * fraction);
            if (isMoon && parentPx >= DOT_MOON_PARENT_PX) capped = Math.max(capped, MIN_BODY_PX);
            targetPx = Math.max(px, capped);
          }
          const visible = !hasParent || targetPx >= CHILD_HIDE_PX;
          b.visual.visible = visible;
          b.scale = visible ? targetPx / px : 0;
          b.visual.scale.setScalar(visible ? b.scale : 1);
        }
        // The Sun's glow inflates with its disc, so it never shrinks to nothing far out.
        sunGlow.scale.setScalar(SUN_RADIUS * 2 * SUN_GLOW_SCALE * sunBody.scale);
      }

      renderer.render(scene, camera);
      if (now - lastDatePublish > 500) {
        lastDatePublish = now;
        usePageStore.getState().setSimJD(simJD);
      }
    };
    let lastDatePublish = 0;
    animate();

    // Keep the canvas sized to its container (only when no fixed size is given).
    let resizeObserver: ResizeObserver | null = null;
    if (size === undefined && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => {
        const w = mount.clientWidth;
        const h = mount.clientHeight;
        if (!w || !h) return;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        updateStarSizes();
      });
      resizeObserver.observe(mount);
    }

    // Expose focus-by-name for the terminal's `fly` command, and apply any
    // request that arrived before the scene existed (e.g. from another view).
    // A star: don't travel, turn. The star field is centred on the camera, so a
    // sprite's local position is its direction. Put the camera on the far side
    // of the focus from that direction, so the star sits beside the focused body.
    // Turn toward a sky direction (unit vector in scene space) and pin a label for it.
    const aimAtDirection = (dir: THREE.Vector3, label: StarInfo) => {
      hasInteracted = true;
      const from = camera.position.clone().sub(controls.target).normalize();
      // Camera opposite the star would put the star dead behind the body. Tilt
      // that direction by the body's angular radius plus a margin, about an axis
      // perpendicular to the star direction, so the star clears the disc.
      const d = camera.position.distanceTo(controls.target);
      const distTo = Math.max(d, focus.radius * AIM_MIN_RADII); // no change if already far enough
      const angularRadius = Math.asin(Math.min(1, focus.radius / Math.max(distTo, focus.radius)));
      const tilt = angularRadius + AIM_MARGIN_RAD;
      let axis = new THREE.Vector3().crossVectors(dir, camera.up).normalize();
      if (axis.lengthSq() < 1e-6) axis = new THREE.Vector3(1, 0, 0);
      const to = dir.clone().negate().applyAxisAngle(axis, -tilt); // negative: star lands above the body
      aim = { from, to, t: 0, distFrom: d, distTo };
      // Engage the label right away, as if hovered. Mouse hover, a drag or a
      // focus change replaces it as usual.
      pinnedStar = label;
      hoveredStarRef.current = label.name;
      onStarHover?.(pinnedStar);
    };
    const aimAtStar = (star: (typeof starSprites)[number]) =>
      aimAtDirection(star.sprite.position.clone().normalize(), { name: star.name, lightYears: star.lightYears, spectral: star.spectral, fact: star.fact });

    // Equatorial (RA/Dec, degrees) -> scene direction, same frame as the star field.
    const skyDirection = (raDeg: number, decDeg: number) => {
      const e = THREE.MathUtils.degToRad(OBLIQUITY_DEG);
      const ra = THREE.MathUtils.degToRad(raDeg);
      const dec = THREE.MathUtils.degToRad(decDeg);
      return new THREE.Vector3()
        .addScaledVector(new THREE.Vector3(1, 0, 0), Math.cos(dec) * Math.cos(ra))
        .addScaledVector(new THREE.Vector3(0, -Math.sin(e), -Math.cos(e)), Math.cos(dec) * Math.sin(ra))
        .addScaledVector(new THREE.Vector3(0, Math.cos(e), -Math.sin(e)), Math.sin(dec))
        .normalize();
    };
    // Sagittarius A*, the galactic centre: RA 266.4, Dec -29.0 (J2000), beside the Teapot's spout.
    const GALACTIC_CORE = { name: 'Galactic core', lightYears: 26000, fact: 'This is the direction of the galactic core.' };
    const GALACTIC_CORE_DIR = skyDirection(266.417, -29.008);
    focusByNameRef.current = (name: string) => {
      const body = bodies.find((b) => b.name.toLowerCase() === name.toLowerCase());
      if (body) { setFocus(body, { zoomTo: true }); return; }
      const star = starSprites.find((s) => s.name.toLowerCase() === name.toLowerCase());
      if (star) { aimAtStar(star); return; }
      if (name.toLowerCase() === 'galactic core') aimAtDirection(GALACTIC_CORE_DIR, GALACTIC_CORE);
    };
    aimAtStarRef.current = aimAtStar;

    // Restore the view saved by a previous scene (scale switch), else the one
    // persisted from a previous visit (once per page load).
    let saved = savedViewRef.current;
    if (!saved && !restoredStoredViewRef.current) {
      restoredStoredViewRef.current = true;
      try {
        const stored = JSON.parse(localStorage.getItem(VIEW_KEY) ?? 'null');
        if (stored && typeof stored.name === 'string' && Array.isArray(stored.dir) && typeof stored.radii === 'number') {
          saved = { name: stored.name, dir: new THREE.Vector3().fromArray(stored.dir).normalize(), radii: stored.radii };
        }
      } catch { /* no storage, or nothing usable */ }
    }
    if (saved) {
      savedViewRef.current = null;
      const body = bodies.find((b) => b.name === saved.name);
      if (body) {
        focus = body;
        transition = null;
        hasInteracted = true; // the user had already been exploring
        worldPos(body, focusPoint);
        const d = Math.max(saved.radii * body.radius, minDistanceFor(body));
        controls.target.copy(focusPoint);
        camera.position.copy(focusPoint).addScaledVector(saved.dir, d);
        controls.update();
        reportFocus(d);
      }
    }
    const pending = usePageStore.getState().focusRequest;
    if (pending && pending.seq !== handledFocusSeqRef.current) {
      handledFocusSeqRef.current = pending.seq;
      focusByNameRef.current(pending.name);
    }

    initializedRef.current = true;

    // Cleanup function
    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
      resizeObserver?.disconnect();
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('keydown', onKeyDown);
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      if (controlsRef.current) {
        controlsRef.current.removeEventListener('start', onControlsStart);
        controlsRef.current.removeEventListener('change', onControlsChange);
        controlsRef.current.removeEventListener('end', onControlsEnd);
        controlsRef.current.dispose();
      }
      if (renderer.domElement) {
        renderer.domElement.removeEventListener('mousemove', onMouseMove);
        renderer.domElement.removeEventListener('mouseleave', onMouseLeave);
        renderer.domElement.removeEventListener('click', onMouseClick);
      }
      if (mountRef.current && renderer.domElement && mountRef.current.contains(renderer.domElement)) {
        mountRef.current.removeChild(renderer.domElement);
      }
      dotsRef.current.forEach(dot => {
        dot.geometry.dispose();
        (dot.material as THREE.Material).dispose();
      });
      moonGeometry.dispose();
      moonMaterial.dispose();
      moonRingGeometry.dispose();
      (moonRing.material as THREE.Material).dispose();
      apolloDisposables.forEach((d) => d.dispose());
      moonDotsRef.current = [];
      apolloGroupRef.current = null;
      moonTexture.dispose();
      moonMaterialRef.current = null;
      earthSystemRef.current = null;
      sunGeometry.dispose();
      sunMaterial.dispose();
      sunGlowMaterial.dispose();
      glowTexture.dispose();
      sunMaterialRef.current = null;
      sunGlowMaterialRef.current = null;
      planetDisposables.forEach(({ geometry, material }) => { geometry.dispose(); material.dispose(); });
      clearMission();
      trackRef.current = null;
      starSprites.forEach(({ sprite }) => sprite.material.dispose());
      starTexture.dispose();
      textures.forEach((t) => t.dispose());
      orbitRings.forEach((ring) => { ring.geometry.dispose(); (ring.material as THREE.Material).dispose(); });
      renderer.dispose();
      savedViewRef.current = {
        name: focus.name,
        dir: camera.position.clone().sub(controls.target).normalize(),
        radii: camera.position.distanceTo(controls.target) / focus.radius,
      };
      initializedRef.current = false;
    };
  }, [size, color, speed, scaleMode]); // scaleMode: the whole scene is rebuilt on switch

  // Orbit ring highlight (terminal `orbits` command).
  useEffect(() => {
    setOrbitStyleRef.current?.(orbitsHighlighted);
  }, [orbitsHighlighted]);

  // Trace a mission (terminal `track` command). If the scene isn't built yet
  // (e.g. a scale switch is rebuilding it), init picks the request up.
  useEffect(() => {
    if (!trackRequest || trackRequest.seq === handledTrackSeqRef.current) return;
    if (!trackRef.current) return;
    handledTrackSeqRef.current = trackRequest.seq;
    trackRef.current(trackRequest.id);
  }, [trackRequest]);

  // Jump the clock (terminal `date` command).
  useEffect(() => {
    if (!dateRequest || dateRequest.seq === handledDateSeqRef.current) return;
    handledDateSeqRef.current = dateRequest.seq;
    dateRequestRef.current = dateRequest.jd;
  }, [dateRequest]);

  // Apollo landing sites on/off (terminal `apollo` command).
  useEffect(() => {
    if (apolloGroupRef.current) apolloGroupRef.current.visible = apolloVisible;
  }, [apolloVisible]);

  // Show/hide the stars (terminal `stars` command).
  useEffect(() => {
    if (starFieldRef.current) starFieldRef.current.visible = starsVisible;
  }, [starsVisible]);

  // Fly to a body requested from the terminal.
  useEffect(() => {
    if (!focusRequest || focusRequest.seq === handledFocusSeqRef.current) return;
    if (!focusByNameRef.current) return; // scene not built yet; init will pick it up
    handledFocusSeqRef.current = focusRequest.seq;
    focusByNameRef.current(focusRequest.name);
  }, [focusRequest]);

  // Separate effect for updating dots only
  useEffect(() => {
    if (!sceneRef.current || !globeRef.current) return;

    const globeRadius = EARTH_RADIUS;

    // Clean up existing dots
    dotsRef.current.forEach(dot => {
      globeRef.current!.remove(dot);
      dot.geometry.dispose();
      (dot.material as THREE.Material).dispose();
    });
    dotsRef.current = [];

    // Create new dots
    dots.forEach(dot => {
      const position = latLonToVector3(dot.lat, dot.lon, globeRadius + 0.02);
      const dotSize = 0.02 * dotSizeMultiplier * dot.size;
      const dotGeometry = new THREE.SphereGeometry(dotSize, 8, 8);
      const dotMaterial = new THREE.MeshBasicMaterial({
        color: dot.color,
        transparent: true,
        opacity: dot.opacity ?? 0.8
      });
      const dotMesh = new THREE.Mesh(dotGeometry, dotMaterial);
      dotMesh.position.copy(position);
      globeRef.current!.add(dotMesh);

      const hitboxGeometry = new THREE.SphereGeometry(dotSize * 4, 8, 8);
      const hitboxMaterial = new THREE.MeshBasicMaterial({ visible: false });
      const hitboxMesh = new THREE.Mesh(hitboxGeometry, hitboxMaterial);
      hitboxMesh.position.copy(position);
      hitboxMesh.userData = { dot: dot };
      globeRef.current!.add(hitboxMesh);
      dotsRef.current.push(hitboxMesh);
    });
  }, [dotsString, dotSizeMultiplier]); // Use stringified dots for comparison

  return (
    <div 
      className={className}
      style={{ 
        width: size ?? '100%', 
        height: size ?? '100%',
        position: 'relative',
        cursor: 'grab'
      }}
    >
      <div
        ref={mountRef}
        style={{
          width: '100%',
          height: '100%',
          position: 'absolute',
          top: 0,
          left: 0
        }}
      />
    </div>
  );
}

export default SolarSystem;