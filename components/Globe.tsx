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
}

interface ThreeJSGlobeWithDotsProps {
  className?: string;
  size?: number;
  color?: string;
  speed?: number;
  dots?: PersonaDot[];
  onDotClick?: (dot: PersonaDot) => void;
  dotSizeMultiplier?: number;
}

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
  fillColor = "#888",
  fillOpacity = 0.22,
  outlineOpacity = 0.85
) => {
  geoJson.features.forEach((feature: any) => {
    const geometry = feature.geometry;
    if (!geometry) return;
    const coordsList = geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.coordinates;

    coordsList.forEach((polygon: any) => {
      polygon.forEach((ring: any, ringIndex: number) => {
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

        if (ringIndex === 0) {
          const shape2d = new THREE.Shape(
            ring.map(([lon, lat]: [number, number]) => {
              return new THREE.Vector2(
                (-lon + 180) / 360 * 2 * Math.PI, // Fixed: negate longitude to match outline fix
                (90 - lat) / 180 * Math.PI
              );
            })
          );
          const geometry2d = new THREE.ShapeGeometry(shape2d);
          const positionArray = geometry2d.attributes.position.array as Float32Array;
          for (let index = 0; index < positionArray.length; index += 3) {
            const lambda = positionArray[index];
            const phi = positionArray[index + 1];
            const r = radius - 0.01;
            positionArray[index]     = r * Math.sin(phi) * Math.cos(lambda);
            positionArray[index + 1] = r * Math.cos(phi);
            positionArray[index + 2] = r * Math.sin(phi) * Math.sin(lambda);
          }
          const mesh = new THREE.Mesh(
            geometry2d,
            new THREE.MeshBasicMaterial({
              color: fillColor,
              transparent: true,
              opacity: fillOpacity,
              depthWrite: false,
              side: THREE.DoubleSide,
            })
          );
          group.add(mesh);
        }
      });
    });
  });
};

export function ThreeJSGlobeWithDots({ 
  className, 
  size = 800, 
  color = "#333333",
  speed = 0.003,
  dots = [],
  onDotClick,
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
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
    camera.position.z = 3.5;
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true 
    });
    renderer.setSize(size, size);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(new THREE.Color(0x000000), 0);
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.outline = 'none';
    renderer.domElement.style.userSelect = 'none';
    rendererRef.current = renderer;
    mountRef.current.appendChild(renderer.domElement);

    // Globe group
    const globeGroup = new THREE.Group();
    globeRef.current = globeGroup;
    scene.add(globeGroup);

    // Add Earth's realistic tilt (23.5 degrees)
    globeGroup.rotation.x = Math.PI * (23.5 / 180); // Convert degrees to radians

    // Create wireframe sphere
    const globeRadius = 1.3;
    const sphereGeometry = new THREE.SphereGeometry(globeRadius, 32, 32);
    const wireframeMaterial = new THREE.MeshBasicMaterial({
      color: color,
      wireframe: true,
      transparent: true,
      opacity: 0.4
    });
    const wireframeSphere = new THREE.Mesh(sphereGeometry, wireframeMaterial);
    globeGroup.add(wireframeSphere);

    // Create latitude and longitude lines
    const createLatitudeLines = () => {
      const latitudes = [];
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
      const longitudes = [];
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
          drawGeoJsonContoursAndFill(geoJson, globeGroup, globeRadius + 0.002, "#ffffff", "#0a0a0a", 0.9, 0.85);
        }
      });

    // Ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.1);
    scene.add(ambientLight);

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enableZoom = false;
    controls.enablePan = false;
    controls.minDistance = 3.5;
    controls.maxDistance = 3.5;
    controlsRef.current = controls;

    // User interaction handlers
    const onControlsStart = () => {
      autoRotateRef.current = false;
      renderer.domElement.style.cursor = 'grabbing';
    };
    const onControlsEnd = () => {
      renderer.domElement.style.cursor = 'grab';
      setTimeout(() => {
        autoRotateRef.current = true;
      }, 3000);
    };

    const onMouseMove = (event: MouseEvent) => {
      renderer.domElement.style.cursor = autoRotateRef.current ? 'grab' : 'grabbing';
    };

    const onMouseClick = (event: MouseEvent) => {
      if (!onDotClick || !camera || !globeGroup) return;

      const rect = renderer.domElement.getBoundingClientRect();
      const mouse = new THREE.Vector2();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);

      const intersects = raycaster.intersectObjects(globeGroup.children, true);
      
      for (let intersect of intersects) {
        if (intersect.object.userData && intersect.object.userData.dot && intersect.object.userData.dot.info) {
          onDotClick(intersect.object.userData.dot);
          break;
        }
      }
    };

    controls.addEventListener('start', onControlsStart);
    controls.addEventListener('end', onControlsEnd);
    renderer.domElement.addEventListener('mousemove', onMouseMove);
    renderer.domElement.addEventListener('click', onMouseClick);

    // Animation loop
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate);
      controls.update();
      if (globeRef.current && autoRotateRef.current) {
        globeRef.current.rotation.y += speed;
      }
      renderer.render(scene, camera);
    };
    animate();

    initializedRef.current = true;

    // Cleanup function
    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
      if (controlsRef.current) {
        controlsRef.current.removeEventListener('start', onControlsStart);
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
      renderer.dispose();
      initializedRef.current = false;
    };
  }, [size, color, speed]); // Removed dots and onDotClick from dependencies

  // Separate effect for updating dots only
  useEffect(() => {
    if (!sceneRef.current || !globeRef.current) return;

    const globeRadius = 1.3;

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
      dotMesh.userData = { dot: dot };
      globeRef.current!.add(dotMesh);
      dotsRef.current.push(dotMesh);
    });
  }, [dotsString, dotSizeMultiplier]); // Use stringified dots for comparison

  return (
    <div 
      className={className}
      style={{ 
        width: size, 
        height: size,
        position: 'relative',
        cursor: 'grab'
      }}
    >
      <div 
        ref={mountRef} 
        style={{ 
          width: size, 
          height: size,
          position: 'absolute',
          top: 0,
          left: 0
        }}
      />
    </div>
  );
}

export default ThreeJSGlobeWithDots;