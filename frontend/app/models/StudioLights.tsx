"use client";

import { Environment, Lightformer } from "@react-three/drei";

// Lights and local studio reflections for the model viewers (no HDR download), so foil and
// metal read as metal. The ring of soft panels around the horizon gives tall, vertical metal
// (Starship's steel) something to reflect; with only the overhead panel it went black.
const RING = [0, 1, 2, 3].map((k) => {
  const a = (k * Math.PI) / 2 + Math.PI / 4;
  return [Math.cos(a) * 8, 0, Math.sin(a) * 8] as [number, number, number];
});

export default function StudioLights() {
  return (
    <>
      <ambientLight intensity={0.25} />
      <directionalLight position={[5, 7, 6]} intensity={3} />
      <directionalLight position={[-6, -1, -3]} intensity={0.6} />
      <Environment resolution={64}>
        <Lightformer form="rect" intensity={2} position={[0, 5, 0]} scale={[10, 10, 1]} rotation-x={Math.PI / 2} />
        <Lightformer form="rect" intensity={0.8} position={[-5, 1, 3]} scale={[6, 4, 1]} rotation-y={Math.PI / 3} />
        <Lightformer form="rect" intensity={0.4} position={[5, -1, -3]} scale={[6, 4, 1]} rotation-y={-Math.PI / 1.5} />
        {RING.map((p, i) => (
          <Lightformer key={i} form="rect" intensity={0.6} position={p} scale={[4, 12, 1]} />
        ))}
      </Environment>
    </>
  );
}
