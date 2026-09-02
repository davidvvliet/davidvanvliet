"use client";

import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

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

interface ThreeJSGlobeWithDotsProps {
  className?: string;
  size?: number;
  color?: string;
  speed?: number;
  dots?: PersonaDot[];
  onDotClick?: (dot: PersonaDot) => void;
  onDotHover?: (dot: PersonaDot | null) => void;
  onBodyHover?: (name: string | null) => void;
  onFocusChange?: (name: string | null) => void; // null when the camera is far from the focused body
  dotSizeMultiplier?: number;
}

// --- Scene layout ---
// The scene is heliocentric: the Sun sits at the origin and Earth orbits it.
// The *camera* is Earth-centric at close range (its target follows Earth) and
// blends toward the Sun as you zoom out, so it feels geocentric until it doesn't.
const EARTH_RADIUS = 1.3;              // Base unit; everything else is relative to this
const CAMERA_FOV = 50;
const DEFAULT_CAMERA_DISTANCE = 4.5;   // Initial view; also the closest allowed zoom
const MAX_CAMERA_DISTANCE = 180;       // How far out the user can scroll

// Planet orbits use TRUE distance ratios: orbit radius = ORBIT_SCALE * AU.
// Body sizes and the Moon's orbit stay compressed (at true ratio Earth would
// be 0.004 units across), and bodies are never drawn smaller than MIN_BODY_PX
// so the outer system still reads as a system rather than empty space.
const ORBIT_SCALE = 90;                // Earth (1 AU) orbits at this radius
const orbitRadiusForAU = (au: number) => ORBIT_SCALE * au;
const EARTH_ORBIT_AU = 1;
const MIN_BODY_PX = 3;                 // Minimum on-screen radius of any body, in pixels
const ORBIT_RING_OPACITY = 0.12;

type PlanetSpec = {
  name: string;
  au: number;              // semi-major axis
  radiusEarths: number;    // radius relative to Earth
  periodDays: number;      // orbital period
  rotationDays: number;    // sidereal rotation period
  inclinationDeg: number;  // orbit inclination to the ecliptic
  color: number;
  phaseDeg: number;        // starting position on the orbit
  solid?: boolean;         // solid sphere instead of wireframe (e.g. cloud-covered)
};

// Planets other than Earth (Earth is built separately: it has the continents,
// the location dots and the Moon). Adding a planet = one row.
const PLANETS: PlanetSpec[] = [
  { name: 'Mercury', au: 0.387, radiusEarths: 0.383, periodDays: 87.97, rotationDays: 58.65, inclinationDeg: 7.0, color: 0x8a847c, phaseDeg: 120 },
  // Venus rotates retrograde (negative period). Solid: it's a featureless cloud deck.
  { name: 'Venus', au: 0.723, radiusEarths: 0.949, periodDays: 224.7, rotationDays: -243.0, inclinationDeg: 3.39, color: 0xe8dcc0, phaseDeg: 230, solid: true },
];
// One clock for all motion, so every period keeps its real ratio.
// Change SECONDS_PER_DAY to speed everything up or down together.
const SECONDS_PER_DAY = 10;            // Real seconds per simulated Earth day
const EARTH_DAY_DAYS = 0.99727;        // Sidereal rotation period, in days
const MOON_ORBIT_DAYS = 27.32;         // Sidereal month
const EARTH_YEAR_DAYS = 365.25;
const angularSpeed = (periodDays: number) => (2 * Math.PI) / (periodDays * SECONDS_PER_DAY); // rad/s

const MOON_ORBIT_RADIUS = 6;           // Distance from Earth's centre (cinematic, not true scale)
const MOON_RADIUS = EARTH_RADIUS * 0.273; // True ratio: Moon diameter is 27.3% of Earth's
const MOON_INCLINATION_DEG = 5.14;     // Real inclination of the Moon's orbit
const MOON_COLOR = 0x8c8c8c;           // Wireframe color, brighter than Earth's so the wires read

const SUN_RADIUS = 7;                  // ~5x Earth's radius, ~20x the moon's
const SUN_COLOR = 0xfff4e8;            // G2V: near-white, faintly warm (the yellow is atmospheric)
const SUN_GLOW_SCALE = 3.2;            // Glow sprite size as a multiple of the sun's diameter

// "Fit" distance: how far back the camera must be for an extent to fit the
// canvas width. Used for per-body zoom limits.
const FIT_MARGIN = 1.15;               // Extra room for perspective

// Focus / picking
const MIN_DISTANCE_RADII = DEFAULT_CAMERA_DISTANCE / EARTH_RADIUS; // closest zoom, in body radii
const MAX_DISTANCE_FIT_FACTOR = 1.6;   // max zoom = (distance where the body's system fits) * this
const LEAF_MAX_DISTANCE_RADII = 40;    // max zoom for bodies with no satellites
const NAME_VISIBLE_RADII = 7.5;         // focused body's name shows only within this many radii
const FOCUS_TRANSITION_SECONDS = 0.9;
const PICK_MIN_PX = 12;                // click tolerance around tiny bodies
const DRAG_THRESHOLD_PX = 5;           // pointer movement beyond this is a drag, not a click

type Body = {
  name: string;
  object: THREE.Object3D;   // world position is read from this each frame
  visual: THREE.Object3D;   // what gets scaled up to enforce MIN_BODY_PX
  radius: number;
  parent: Body | null;
  systemRadius: number;     // radius of its satellites' orbits (0 = none)
  scale: number;            // current enforced scale (1 = true size)
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

export function ThreeJSGlobeWithDots({
  className,
  size,
  color = "#333333",
  speed = 0.003,
  dots = [],
  onDotClick,
  onDotHover,
  onBodyHover,
  onFocusChange,
  dotSizeMultiplier = 1
}: ThreeJSGlobeWithDotsProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const globeRef = useRef<THREE.Group | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const animationIdRef = useRef<number | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const autoRotateRef = useRef<boolean>(true);
  const dotsRef = useRef<THREE.Mesh[]>([]);
  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster());
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2());
  const initializedRef = useRef<boolean>(false);
  const hoveredDotRef = useRef<PersonaDot | null>(null);
  const moonPivotRef = useRef<THREE.Group | null>(null);
  const earthSystemRef = useRef<THREE.Group | null>(null);
  const hoveredBodyRef = useRef<string | null>(null);
  const pointerDownPosRef = useRef<{ x: number; y: number } | null>(null);
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
    const camera = new THREE.PerspectiveCamera(CAMERA_FOV, initialWidth / initialHeight, 0.1, 10000);
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true,
      logarithmicDepthBuffer: true, // near 0.1 to far 10000 without z-fighting
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

    const moonGeometry = new THREE.SphereGeometry(MOON_RADIUS, 16, 16);
    const moonMaterial = new THREE.MeshBasicMaterial({
      color: MOON_COLOR,
      wireframe: true,
      transparent: true,
      opacity: 1,
    });
    moonMaterialRef.current = moonMaterial;
    const moon = new THREE.Mesh(moonGeometry, moonMaterial);
    moon.position.x = MOON_ORBIT_RADIUS;
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
    type Orbiter = { object: THREE.Object3D; orbitRadius: number; periodDays: number; angle: number; spin?: THREE.Object3D; rotationDays?: number };
    const orbiters: Orbiter[] = [];
    const orbitRings: THREE.LineLoop[] = [];
    const addOrbiter = (object: THREE.Object3D, orbitRadius: number, periodDays: number, inclinationDeg: number, phaseDeg: number, spin?: THREE.Object3D, rotationDays?: number) => {
      const pivot = new THREE.Group();
      pivot.rotation.x = THREE.MathUtils.degToRad(inclinationDeg);
      pivot.add(object);
      scene.add(pivot);
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
      orbiters.push({ object, orbitRadius, periodDays, angle: THREE.MathUtils.degToRad(phaseDeg), spin, rotationDays });
    };
    const updateOrbiters = (delta: number) => {
      for (const o of orbiters) {
        o.angle += angularSpeed(o.periodDays) * delta;
        o.object.position.set(o.orbitRadius * Math.cos(o.angle), 0, -o.orbitRadius * Math.sin(o.angle));
        if (o.spin && o.rotationDays) o.spin.rotation.y += angularSpeed(o.rotationDays) * delta;
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
    for (const spec of PLANETS) {
      const radius = EARTH_RADIUS * spec.radiusEarths;
      const geometry = new THREE.SphereGeometry(radius, 16, 16);
      const material = new THREE.MeshBasicMaterial({ color: spec.color, wireframe: !spec.solid, transparent: true, opacity: spec.solid ? 1 : 0.8 });
      const mesh = new THREE.Mesh(geometry, material);
      planetDisposables.push({ geometry, material });
      const holder = new THREE.Group(); // position-only; the mesh spins inside it
      holder.add(mesh);
      const orbitRadius = orbitRadiusForAU(spec.au);
      addOrbiter(holder, orbitRadius, spec.periodDays, spec.inclinationDeg, spec.phaseDeg, mesh, spec.rotationDays);
      bodies.push({ name: spec.name, object: holder, visual: mesh, radius, parent: sunBody, systemRadius: 0, scale: 1 });
      sunBody.systemRadius = Math.max(sunBody.systemRadius, orbitRadius);
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
    const minDistanceFor = (b: Body) =>
      b.parent ? b.radius * MIN_DISTANCE_RADII : fitDistance(b.systemRadius + b.radius);
    const maxDistanceFor = (b: Body) =>
      b.systemRadius > 0
        ? fitDistance(b.systemRadius + b.radius) * MAX_DISTANCE_FIT_FACTOR
        : b.radius * LEAF_MAX_DISTANCE_RADII;

    const setFocus = (next: Body, opts: { zoomTo?: boolean } = {}) => {
      if (next === focus) return;
      transition = {
        from: focus,
        t: 0,
        distTo: opts.zoomTo
          ? (next.parent ? next.radius * MIN_DISTANCE_RADII * 1.5 : minDistanceFor(next) * 1.1)
          : null,
        startOffset: camera.position.clone().sub(worldPos(focus, tmpA)),
      };
      focus = next;
    };
    let reportedFocusName: string | null | undefined;
    const reportFocus = (dist: number) => {
      const name = dist <= focus.radius * NAME_VISIBLE_RADII ? focus.name : null;
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
      let best: Body | null = null;
      let bestDist = Infinity;
      for (const b of bodies) {
        worldPos(b, tmpA);
        const camDist = tmpA.distanceTo(camera.position);
        tmpB.copy(tmpA).project(camera);
        if (tmpB.z > 1) continue; // behind the camera
        const sx = ((tmpB.x + 1) / 2) * rect.width;
        const sy = ((1 - tmpB.y) / 2) * rect.height;
        const screenRadius = ((b.radius * b.scale) / (camDist * Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2)))) * (rect.height / 2);
        const tolerance = Math.max(screenRadius, PICK_MIN_PX);
        const d = Math.hypot(sx - px, sy - py);
        if (d <= tolerance && d < bestDist) {
          best = b;
          bestDist = d;
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
        renderer.domElement.style.cursor = 'pointer';
      } else {
        if (hoveredDotRef.current !== null) {
          hoveredDotRef.current = null;
          onDotHover?.(null);
        }
        const body = pickBody(event.clientX, event.clientY);
        const name = body && body !== focus ? body.name : null;
        if (hoveredBodyRef.current !== name) {
          hoveredBodyRef.current = name;
          onBodyHover?.(name);
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
      //    Clicking empty space does nothing; zoom out (or Escape) to go up.
      const body = pickBody(event.clientX, event.clientY);
      if (body) setFocus(body, { zoomTo: true });
    };

    controls.addEventListener('start', onControlsStart);
    controls.addEventListener('change', onControlsChange);
    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('keydown', onKeyDown);
    controls.addEventListener('end', onControlsEnd);
    renderer.domElement.addEventListener('mousemove', onMouseMove);
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
      if (globeRef.current && autoRotateRef.current) {
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

      // Per-body zoom limits. Zooming out past a moon's limit hands focus to
      // its planet (a short hop). Planets never hand off to the Sun: the camera
      // would have to fly across the whole orbit. Their range extends to the
      // full system distance instead, and the Sun frame is entered by clicking it.
      // (Limits are relaxed mid-transition so the eased distance isn't clamped.)
      const systemMax = Math.max(MAX_CAMERA_DISTANCE, minDistanceFor(sunBody) * 1.5);
      const handsOffToParent = focus.parent !== null && focus.parent !== sunBody;
      controls.minDistance = transition ? 0.1 : minDistanceFor(focus);
      controls.maxDistance = transition ? systemMax * 10 : (handsOffToParent ? maxDistanceFor(focus) : systemMax);
      if (!transition && handsOffToParent && dist >= controls.maxDistance * 0.995) {
        setFocus(focus.parent!);
      }
      controls.update();

      reportFocus(dist);

      // Enforce a minimum on-screen size so distant bodies stay visible.
      {
        const halfHeightPx = renderer.domElement.clientHeight / 2;
        const tanHalfFov = Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2));
        for (const b of bodies) {
          worldPos(b, tmpA);
          const camDist = tmpA.distanceTo(camera.position);
          const px = (b.radius / (camDist * tanHalfFov)) * halfHeightPx;
          b.scale = px < MIN_BODY_PX ? MIN_BODY_PX / px : 1;
          b.visual.scale.setScalar(b.scale);
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
      });
      resizeObserver.observe(mount);
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
      orbitRings.forEach((ring) => { ring.geometry.dispose(); (ring.material as THREE.Material).dispose(); });
      renderer.dispose();
      initializedRef.current = false;
    };
  }, [size, color, speed]); // Removed dots and onDotClick from dependencies

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

export default ThreeJSGlobeWithDots;