import { useId } from "react";
import type { GlobePaths } from "../photoTypes";
import styles from "./PhotoView.module.css";

const DOT_COLOR = "#5b9bff";

// The home page's Earth as a still (paths from photoGlobe.ts), marked where the
// photo was taken with the scene's star sprite (makeStarTexture in
// SolarSystem.tsx) tinted blue: the same spikes, halo and core, added light
// on light. size and spritePx are in CSS pixels.
export default function PhotoGlobe({ globe, size, spritePx, className }: { globe: GlobePaths; size: number; spritePx: number; className?: string }) {
  const id = useId();
  // The texture is 256 px across; s maps its pixels to viewBox units.
  const s = (spritePx * (100 / size)) / 256;
  const spike = (angle: number, length: number, width: number, alpha: number) => (
    <g transform={`rotate(${angle})`}>
      <linearGradient id={`${id}s${angle}`} gradientUnits="userSpaceOnUse" x1={-length * s} x2={length * s} y1={0} y2={0}>
        <stop offset={0} stopColor={DOT_COLOR} stopOpacity={0} />
        <stop offset={0.5} stopColor={DOT_COLOR} stopOpacity={alpha} />
        <stop offset={1} stopColor={DOT_COLOR} stopOpacity={0} />
      </linearGradient>
      <rect x={-length * s} y={(-width / 2) * s} width={length * 2 * s} height={width * s} fill={`url(#${id}s${angle})`} className={styles.globeLight} />
    </g>
  );
  return (
    <svg viewBox="-50 -50 100 100" width={size} height={size} className={`${styles.globe} ${className ?? ""}`} aria-hidden="true">
      <path d={globe.grid} className={styles.globeGrid} />
      <path d={globe.land} className={styles.globeLand} />
      <radialGradient id={`${id}h`} gradientUnits="userSpaceOnUse" cx={0} cy={0} r={64 * s}>
        <stop offset={0} stopColor={DOT_COLOR} stopOpacity={1} />
        <stop offset={0.15} stopColor={DOT_COLOR} stopOpacity={0.65} />
        <stop offset={0.5} stopColor={DOT_COLOR} stopOpacity={0.15} />
        <stop offset={1} stopColor={DOT_COLOR} stopOpacity={0} />
      </radialGradient>
      <radialGradient id={`${id}c`} gradientUnits="userSpaceOnUse" cx={0} cy={0} r={11.52 * s}>
        <stop offset={0} stopColor={DOT_COLOR} stopOpacity={1} />
        <stop offset={0.6} stopColor={DOT_COLOR} stopOpacity={1} />
        <stop offset={1} stopColor={DOT_COLOR} stopOpacity={0} />
      </radialGradient>
      {spike(0, 128, 2.2, 0.9)}
      {spike(90, 128, 2.2, 0.9)}
      {spike(45, 70.4, 1.4, 0.35)}
      {spike(-45, 70.4, 1.4, 0.35)}
      <circle r={64 * s} fill={`url(#${id}h)`} className={styles.globeLight} />
      <circle r={11.52 * s} fill={`url(#${id}c)`} className={styles.globeLight} />
    </svg>
  );
}
