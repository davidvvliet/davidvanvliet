"use client";

import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { usePageStore } from '../store/pageStore';
import { PLANETS, MOONS, STARS, SPECTRAL_COLORS } from './solarSystemData';

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
  onStarHover?: (star: { name: string; lightYears: number } | null) => void;
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
const ORBIT_SCALE = 260;               // Earth (1 AU) orbits at this radius
const orbitRadiusForAU = (au: number) => ORBIT_SCALE * au;
const EARTH_ORBIT_AU = 1;
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
const ORBIT_RING_OPACITY = 0.12;

// One clock for all motion, so every period keeps its real ratio.
// Change SECONDS_PER_DAY to speed everything up or down together.
const SECONDS_PER_DAY = 10;            // Real seconds per simulated Earth day
const EARTH_DAY_DAYS = 0.99727;        // Sidereal rotation period, in days
const MOON_ORBIT_DAYS = 27.32;         // Sidereal month
const EARTH_YEAR_DAYS = 365.25;
const angularSpeed = (periodDays: number) => (2 * Math.PI) / (periodDays * SECONDS_PER_DAY); // rad/s

const MOON_ORBIT_RADIUS = EARTH_RADIUS * 60.3; // True ratio: 384,400 km is 60.3 Earth radii
const MOON_RADIUS = EARTH_RADIUS * 0.273; // True ratio: Moon diameter is 27.3% of Earth's
const MOON_INCLINATION_DEG = 5.14;     // Real inclination of the Moon's orbit
const MOON_TEXTURE = '/moon.jpg';      // Equirectangular map

const SUN_RADIUS = 20;                 // ~15x Earth's radius; bigger than Jupiter, far short of the real 109x
const SUN_COLOR = 0xfff4e8;            // G2V: near-white, faintly warm (the yellow is atmospheric)
const SUN_GLOW_SCALE = 3.2;            // Glow sprite size as a multiple of the sun's diameter

// Stars: one sprite each on a sphere that is re-centred on the camera every
// frame (no parallax, which is physically right at this scale). Directions are
// true; the sphere radius just has to sit inside the far plane. The sprite is a
// telescope-style star: saturated core, tinted halo, diffraction spikes. Size
// follows brightness, so only the bright ones show spikes.
const STAR_SPHERE_RADIUS = 50000;
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
  halo.addColorStop(0, 'rgba(255,255,255,0.9)');
  halo.addColorStop(0.15, 'rgba(255,255,255,0.45)');
  halo.addColorStop(0.5, 'rgba(255,255,255,0.08)');
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
const NAME_VISIBLE_FACTOR = 7.5 / MIN_DISTANCE_RADII;  // ~2.2x close-up: focused body's name shows within this
const ROOT_NAME_VISIBLE_FACTOR = 1.15;                 // for the Sun, relative to its wide-view fly-in distance
const REFOCUS_FACTOR = 20 / MIN_DISTANCE_RADII;        // ~5.8x close-up: beyond this, clicking the focused body zooms back in
const FOCUS_TRANSITION_SECONDS = 0.9;
const PICK_MIN_PX = 12;                // click tolerance floor, in pixels
const PICK_RADIUS_MULTIPLE = 4;        // tolerance = drawn radius * this (capped: big bodies use their outline)
const PICK_CAP_PX = 60;                // above this drawn radius, the outline itself is the hitbox
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
  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster());
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2());
  const initializedRef = useRef<boolean>(false);
  const hoveredDotRef = useRef<PersonaDot | null>(null);
  const moonPivotRef = useRef<THREE.Group | null>(null);
  const earthSystemRef = useRef<THREE.Group | null>(null);
  const hoveredBodyRef = useRef<string | null>(null);
  const hoveredStarRef = useRef<string | null>(null);
  const pointerDownPosRef = useRef<{ x: number; y: number } | null>(null);
  const focusByNameRef = useRef<((name: string) => void) | null>(null);
  const focusRequest = usePageStore((s) => s.focusRequest);
  const starsVisible = usePageStore((s) => s.starsVisible);
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
    const camera = new THREE.PerspectiveCamera(CAMERA_FOV, initialWidth / initialHeight, 0.1, 100000);
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true,
      logarithmicDepthBuffer: true, // near 0.1 to far 100000 without z-fighting
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
    globeGroup.rotation.x = Math.PI * (23.5 / 180); // Convert degrees to radians

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

    // Moon: its own pivot under the Earth system (sibling of the globe group).
    const moonPivot = new THREE.Group();
    moonPivot.rotation.x = THREE.MathUtils.degToRad(MOON_INCLINATION_DEG);
    earthSystem.add(moonPivot);
    moonPivotRef.current = moonPivot;

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
    moon.position.x = MOON_ORBIT_RADIUS;
    // SphereGeometry puts the map's centre (lon 0, the near side) on +x, which
    // points away from Earth here; turn it so the near side faces Earth.
    moon.rotation.y = Math.PI;
    moonPivot.add(moon);

    // Sun: a solid sphere at the origin plus a soft additive glow sprite that
    // always faces the camera.
    const sunGeometry = new THREE.SphereGeometry(SUN_RADIUS, 24, 24);
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
    gradient.addColorStop(0.25, 'rgba(255, 244, 232, 0.55)');
    gradient.addColorStop(0.6, 'rgba(255, 236, 214, 0.12)');
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
    const starSprites: { sprite: THREE.Sprite; px: number; name: string; lightYears: number }[] = [];
    // Anything on the sky that gets a hover label.
    const skyPickables: { object: THREE.Object3D; px: number; name: string; lightYears: number }[] = [];
    {
      const e = THREE.MathUtils.degToRad(OBLIQUITY_DEG);
      const e1 = new THREE.Vector3(1, 0, 0);
      const e2 = new THREE.Vector3(0, Math.sin(e), -Math.cos(e));
      const e3 = new THREE.Vector3(0, Math.cos(e), Math.sin(e));
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
        starSprites.push({ sprite, px, name: star.name, lightYears: star.lightYears });
        skyPickables.push({ object: sprite, px, name: star.name, lightYears: star.lightYears });
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
    controls.zoomSpeed = 0.6;
    controls.enablePan = false;
    controls.minDistance = DEFAULT_CAMERA_DISTANCE; // can't zoom in past the default view
    controls.maxDistance = MAX_CAMERA_DISTANCE;
    controlsRef.current = controls;

    // Orbiters: anything that goes around the Sun. Each sits in an inclined
    // pivot; its position is computed from an angle each frame (not by rotating
    // the pivot), so axial tilts stay fixed in space.
    type Orbiter = { object: THREE.Object3D; orbitRadius: number; periodDays: number; angle: number; spin?: THREE.Object3D; rotationDays?: number; tidallyLocked?: boolean; faceOffset?: number };
    const orbiters: Orbiter[] = [];
    const orbitRings: THREE.LineLoop[] = [];
    const addOrbiter = (object: THREE.Object3D, orbitRadius: number, periodDays: number, inclinationDeg: number, phaseDeg: number, spin?: THREE.Object3D, rotationDays?: number, parent: THREE.Object3D = scene, tidallyLocked = false, faceOffsetDeg = 0) => {
      const pivot = new THREE.Group();
      pivot.rotation.x = THREE.MathUtils.degToRad(inclinationDeg);
      pivot.add(object);
      parent.add(pivot);
      // Faint orbit ring
      const ringPoints: THREE.Vector3[] = [];
      for (let i = 0; i < 128; i++) {
        const a = (i / 128) * Math.PI * 2;
        ringPoints.push(new THREE.Vector3(orbitRadius * Math.cos(a), 0, -orbitRadius * Math.sin(a)));
      }
      const ring = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(ringPoints),
        new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: ORBIT_RING_OPACITY })
      );
      pivot.add(ring);
      orbitRings.push(ring);
      orbiters.push({ object, orbitRadius, periodDays, angle: THREE.MathUtils.degToRad(phaseDeg), spin, rotationDays, tidallyLocked, faceOffset: THREE.MathUtils.degToRad(faceOffsetDeg) });
    };
    const updateOrbiters = (delta: number) => {
      for (const o of orbiters) {
        o.angle += angularSpeed(o.periodDays) * delta;
        o.object.position.set(o.orbitRadius * Math.cos(o.angle), 0, -o.orbitRadius * Math.sin(o.angle));
        if (o.spin && o.rotationDays) o.spin.rotation.y += angularSpeed(o.rotationDays) * delta;
        // Tidal lock: one rotation per orbit, with the map's centre (+x on the
        // sphere) always pointing back at the parent.
        if (o.tidallyLocked) o.object.rotation.y = o.angle + Math.PI + (o.faceOffset ?? 0);
      }
    };

    // Earth (its spin is driven separately, gated by auto-rotate).
    const earthOrbitRadius = orbitRadiusForAU(EARTH_ORBIT_AU);
    scene.remove(earthSystem);
    addOrbiter(earthSystem, earthOrbitRadius, EARTH_YEAR_DAYS, 0, 0);

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
      tilted.rotation.z = THREE.MathUtils.degToRad(spec.axialTiltDeg ?? 0);
      // The visual group (planet mesh + rings) is what the size floor scales.
      // It's a sibling of the moon pivots, so inflating a distant planet never
      // inflates its moons or their orbits along with it.
      const visual = new THREE.Group();
      mesh.rotation.y = THREE.MathUtils.degToRad(spec.spinPhaseDeg ?? 0);
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
      addOrbiter(holder, orbitRadius, spec.periodDays, spec.inclinationDeg, spec.phaseDeg, mesh, spec.rotationDays);
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
      addOrbiter(mesh, orbitRadius, spec.periodDays, spec.inclinationDeg, spec.phaseDeg, undefined, undefined, tiltedByPlanet.get(spec.planet) ?? planetBody.object, true, spec.faceOffsetDeg);
      bodies.push({ name: spec.name, object: mesh, visual: mesh, radius, parent: planetBody, systemRadius: 0, scale: 1 });
      planetBody.systemRadius = Math.max(planetBody.systemRadius, orbitRadius);
    }
    updateOrbiters(0);
    const earthPosition = new THREE.Vector3();
    earthSystem.getWorldPosition(earthPosition);
    const worldPos = (b: Body, out: THREE.Vector3) => b.object.getWorldPosition(out);

    // Focus state: the camera target follows `focus`. A transition eases the
    // target (and optionally the distance) from the previous body.
    let focus: Body = earthBody;
    // For zoomTo transitions, `startOffset` is the camera's offset from the old
    // body at the start; the camera then flies straight toward the new body
    // along the line of sight, so it never passes through the parent.
    let transition: { from: Body; t: number; distTo: number | null; startOffset: THREE.Vector3 } | null = null;
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

    const setFocus = (next: Body, opts: { zoomTo?: boolean } = {}) => {
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
      };
      focus = next;
    };
    let reportedFocusName: string | null | undefined;
    const reportFocus = (dist: number) => {
      const nameLimit = focus.parent
        ? minDistanceFor(focus) * NAME_VISIBLE_FACTOR
        : wideViewDistance(focus) * 1.1 * ROOT_NAME_VISIBLE_FACTOR;
      const name = dist <= nameLimit ? focus.name : null;
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

    controls.target.copy(earthPosition);
    camera.position.copy(earthPosition).add(new THREE.Vector3(0, 0, DEFAULT_CAMERA_DISTANCE));
    controls.update();
    reportFocus(DEFAULT_CAMERA_DISTANCE);

    // User interaction handlers
    const onControlsStart = () => {
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

      const intersects = raycaster.intersectObjects(dotsRef.current, false);

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
        const star = body ? null : pickStar(event.clientX, event.clientY);
        const starName = star ? star.name : null;
        if (hoveredStarRef.current !== starName) {
          hoveredStarRef.current = starName;
          onStarHover?.(star ? { name: star.name, lightYears: star.lightYears } : null);
        }
        renderer.domElement.style.cursor = name ? 'pointer' : (autoRotateRef.current ? 'grab' : 'grabbing');
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
      if (body) setFocus(body, { zoomTo: true });
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

    // Animation loop
    let lastTime = performance.now();
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate);
      const now = performance.now();
      const delta = (now - lastTime) / 1000; // seconds
      lastTime = now;

      // Orbital motion
      updateOrbiters(delta);
      if (globeRef.current && autoRotateRef.current && !hoverPausedRef.current) {
        globeRef.current.rotation.y += angularSpeed(EARTH_DAY_DAYS) * delta;
      }
      if (moonPivotRef.current) {
        moonPivotRef.current.rotation.y += angularSpeed(MOON_ORBIT_DAYS) * delta;
      }

      // Camera focus: the target follows the focused body (easing from the
      // previous one during a transition). The camera moves with the target so
      // the user's orbit direction and zoom are kept.
      const offset = camera.position.clone().sub(controls.target);
      let dist = offset.length();
      worldPos(focus, focusPoint);
      if (transition) {
        transition.t = Math.min(1, transition.t + delta / FOCUS_TRANSITION_SECONDS);
        const k = THREE.MathUtils.smoothstep(transition.t, 0, 1);
        const newBodyPos = tmpB.copy(focusPoint);
        worldPos(transition.from, tmpA);
        focusPoint.copy(tmpA).lerp(newBodyPos, k);
        if (transition.distTo !== null) {
          // Straight flight: from (old body + start offset) toward the new body,
          // ending at distTo on the near side of it.
          const startPos = tmpA.add(transition.startOffset);
          const endPos = startPos.clone().sub(newBodyPos).setLength(transition.distTo).add(newBodyPos);
          camera.position.copy(startPos).lerp(endPos, k);
          offset.copy(camera.position).sub(focusPoint);
          dist = offset.length();
        }
        if (transition.t >= 1) transition = null;
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
      }

      renderer.render(scene, camera);
    };
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
    focusByNameRef.current = (name: string) => {
      const body = bodies.find((b) => b.name.toLowerCase() === name.toLowerCase());
      if (body) setFocus(body, { zoomTo: true });
    };
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
      moonTexture.dispose();
      moonPivotRef.current = null;
      moonMaterialRef.current = null;
      earthSystemRef.current = null;
      sunGeometry.dispose();
      sunMaterial.dispose();
      sunGlowMaterial.dispose();
      glowTexture.dispose();
      sunMaterialRef.current = null;
      sunGlowMaterialRef.current = null;
      planetDisposables.forEach(({ geometry, material }) => { geometry.dispose(); material.dispose(); });
      starSprites.forEach(({ sprite }) => sprite.material.dispose());
      starTexture.dispose();
      textures.forEach((t) => t.dispose());
      orbitRings.forEach((ring) => { ring.geometry.dispose(); (ring.material as THREE.Material).dispose(); });
      renderer.dispose();
      initializedRef.current = false;
    };
  }, [size, color, speed]); // Removed dots and onDotClick from dependencies

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