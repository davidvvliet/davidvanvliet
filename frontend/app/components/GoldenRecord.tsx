"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Lightformer, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { useRouter } from "next/navigation";

// The golden record cover from our Voyager model (public/golden-record.glb: 30.7 cm across,
// 1.3 cm thick, engravings as colour + normal maps), turning about its vertical axis like a spun coin.
const URL = "/golden-record.glb";
const TURN_SECONDS = 8;
const MODEL_PAGE = "/models"; // a click (not a drag) opens the models grid
const CLICK_PX = 5;
const DRAG_RADIANS_PER_PX = 0.012;
const MAX_PITCH = 1.2; // radians: tilting stops short of edge-on from above or below
const RETURN_RATE = 4; // per second: how fast a released disc settles back
// Radians the lights are turned toward the camera, so the upright disc's face mirrors the bright
// panel that sits overhead in the dashboard (where the view is from above) instead of the dark horizon.
const LIGHT_TILT = 0.7;

// Pointer drag, in radians: yaw (sideways) and pitch (tilt). Read every frame, so it lives in a ref.
type Drag = { active: boolean; hover: boolean; yaw: number; pitch: number };

function Record({ spin, drag }: { spin: boolean; drag: React.RefObject<Drag> }) {
  const { scene } = useGLTF(URL);
  const held = useRef<THREE.Group>(null);
  const turn = useRef<THREE.Group>(null);
  // Centre the disc at the origin whatever the export's origin is.
  const centred = useMemo(() => {
    const c = new THREE.Box3().setFromObject(scene).getCenter(new THREE.Vector3());
    scene.position.sub(c);
    return scene;
  }, [scene]);
  useFrame((_, dt) => {
    const d = drag.current;
    if (!held.current || !turn.current) return;
    // The spin pauses while hovered or held; on release the drag eases back to zero and the spin carries on.
    if (spin && !d.active && !d.hover) turn.current.rotation.y += (dt * 2 * Math.PI) / TURN_SECONDS;
    if (!d.active) {
      const k = Math.exp(-dt * RETURN_RATE);
      d.yaw *= k;
      d.pitch *= k;
    }
    held.current.rotation.set(d.pitch, d.yaw, 0);
  });
  return (
    <group ref={held}>
      <group ref={turn} rotation={[0, spin ? 0 : -0.5, 0]}>
        <primitive object={centred} />
      </group>
    </group>
  );
}

export default function GoldenRecord() {
  const [spin, setSpin] = useState(true);
  useEffect(() => {
    const q = window.matchMedia("(prefers-reduced-motion: reduce)");
    const set = () => setSpin(!q.matches);
    set();
    q.addEventListener("change", set);
    return () => q.removeEventListener("change", set);
  }, []);
  const drag = useRef<Drag>({ active: false, hover: false, yaw: 0, pitch: 0 });
  const last = useRef<{ x: number; y: number } | null>(null);
  const travel = useRef(0); // pointer distance since the press, px: a click barely moves
  const [grabbing, setGrabbing] = useState(false);
  const router = useRouter();
  const release = () => {
    drag.current.active = false;
    last.current = null;
    setGrabbing(false);
  };
  const down = (e: React.PointerEvent) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    last.current = { x: e.clientX, y: e.clientY };
    travel.current = 0;
    drag.current.active = true;
    setGrabbing(true);
  };
  const move = (e: React.PointerEvent) => {
    if (!drag.current.active || !last.current) return;
    if (e.buttons === 0) return release(); // the release was missed (e.g. outside the window)
    const d = drag.current;
    const dx = e.clientX - last.current.x, dy = e.clientY - last.current.y;
    travel.current += Math.hypot(dx, dy);
    d.yaw += dx * DRAG_RADIANS_PER_PX;
    d.pitch = Math.max(-MAX_PITCH, Math.min(MAX_PITCH, d.pitch + dy * DRAG_RADIANS_PER_PX));
    last.current = { x: e.clientX, y: e.clientY };
  };
  const up = () => {
    const click = drag.current.active && travel.current < CLICK_PX;
    release();
    if (click) router.push(MODEL_PAGE);
  };
  return (
    <div onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={release}
      onLostPointerCapture={release}
      onPointerEnter={() => (drag.current.hover = true)} onPointerLeave={() => (drag.current.hover = false)} role="link" aria-label="Models"
      style={{ width: "100%", height: "100%", touchAction: "none", cursor: grabbing ? "grabbing" : "pointer" }}>
    <Canvas camera={{ fov: 30, position: [0, 0, 0.66], near: 0.05, far: 5 }} dpr={[1, 2]}
      gl={{ alpha: true, antialias: true }} aria-label="Voyager golden record cover">
      {/* The models dashboard's lighting (app/models/ModelsDashboard.tsx), which shows the gold best. */}
      <ambientLight intensity={0.25} />
      <directionalLight position={[5, 7, 6]} intensity={3} />
      <directionalLight position={[-6, -1, -3]} intensity={0.6} />
      <Environment resolution={64} environmentRotation={[LIGHT_TILT, 0, 0]}>
        <Lightformer form="rect" intensity={2} position={[0, 5, 0]} scale={[10, 10, 1]} rotation-x={Math.PI / 2} />
        <Lightformer form="rect" intensity={0.8} position={[-5, 1, 3]} scale={[6, 4, 1]} rotation-y={Math.PI / 3} />
        <Lightformer form="rect" intensity={0.4} position={[5, -1, -3]} scale={[6, 4, 1]} rotation-y={-Math.PI / 1.5} />
      </Environment>
      <Suspense fallback={null}>
        <Record spin={spin} drag={drag} />
      </Suspense>
    </Canvas>
    </div>
  );
}

useGLTF.preload(URL);
