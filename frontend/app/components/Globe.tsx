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

// Distances/sizes are compressed (real ratios are far too extreme to render), but
// keep the ordering. Orbit radius = ORBIT_SCALE * sqrt(AU) so the table below can
// grow to more planets and stay consistent.
const ORBIT_SCALE = 90;                // Earth (1 AU) orbits at this radius
const orbitRadiusForAU = (au: number) => ORBIT_SCALE * Math.sqrt(au);
const EARTH_ORBIT_AU = 1;
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
const SUN_COLOR = 0xffe2a0;
const SUN_GLOW_SCALE = 3.2;            // Glow sprite size as a multiple of the sun's diameter

// "Fit" distance: how far back the camera must be for an extent to fit the
// canvas width. Used for per-body zoom limits.
const FIT_MARGIN = 1.15;               // Extra room for perspective

// Focus / picking
const MIN_DISTANCE_RADII = DEFAULT_CAMERA_DISTANCE / EARTH_RADIUS; // closest zoom, in body radii
const MAX_DISTANCE_FIT_FACTOR = 1.6;   // max zoom = (distance where the body's system fits) * this
const LEAF_MAX_DISTANCE_RADII = 40;    // max zoom for bodies with no satellites
const FOCUS_TRANSITION_SECONDS = 0.9;
const PICK_MIN_PX = 12;                // click tolerance around tiny bodies
const DRAG_THRESHOLD_PX = 5;           // pointer movement beyond this is a drag, not a click

type Body = {
  name: string;
  object: THREE.Object3D;   // world position is read from this each frame
  radius: number;
  parent: Body | null;
  systemRadius: number;     // radius of its satellites' orbits (0 = none)
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
  const earthOrbitAngleRef = useRef<number>(0);
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
    const camera = new THREE.PerspectiveCamera(CAMERA_FOV, initialWidth / initialHeight, 0.1, 1000);
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true 
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
    gradient.addColorStop(0, 'rgba(255, 226, 160, 1)');
    gradient.addColorStop(0.25, 'rgba(255, 226, 160, 0.55)');
    gradient.addColorStop(0.6, 'rgba(255, 200, 120, 0.12)');
    gradient.addColorStop(1, 'rgba(255, 200, 120, 0)');
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

    // Place Earth on its orbit.
    const earthOrbitRadius = orbitRadiusForAU(EARTH_ORBIT_AU);
    const earthPosition = new THREE.Vector3();
    const updateEarthPosition = () => {
      const a = earthOrbitAngleRef.current;
      earthPosition.set(earthOrbitRadius * Math.cos(a), 0, -earthOrbitRadius * Math.sin(a));
      earthSystem.position.copy(earthPosition);
    };
    updateEarthPosition();

    // Bodies that can be focused (clicked). Adding a planet = one entry here.
    const sunBody: Body = { name: 'Sun', object: sun, radius: SUN_RADIUS, parent: null, systemRadius: earthOrbitRadius };
    const earthBody: Body = { name: 'Earth', object: earthSystem, radius: EARTH_RADIUS, parent: sunBody, systemRadius: MOON_ORBIT_RADIUS };
    const moonBody: Body = { name: 'Moon', object: moon, radius: MOON_RADIUS, parent: earthBody, systemRadius: 0 };
    const bodies: Body[] = [sunBody, earthBody, moonBody];
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
        const screenRadius = (b.radius / (camDist * Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2)))) * (rect.height / 2);
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
      earthOrbitAngleRef.current += angularSpeed(EARTH_YEAR_DAYS) * delta;
      updateEarthPosition();
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