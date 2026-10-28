import type { GlobePaths } from "../photoTypes";
import styles from "./PhotoView.module.css";

// The home page's Earth as a still (paths from photoGlobe.ts), with a blue dot
// where the photo was taken, at the centre. size is in CSS pixels.
export default function PhotoGlobe({ globe, size, className }: { globe: GlobePaths; size: number; className?: string }) {
  const px = 100 / size; // viewBox units per pixel, so the dot keeps its pixel size
  return (
    <svg viewBox="-50 -50 100 100" width={size} height={size} className={`${styles.globe} ${className ?? ""}`} aria-hidden="true">
      <path d={globe.grid} className={styles.globeGrid} />
      <path d={globe.land} className={styles.globeLand} />
      <circle r={px * 5} className={styles.globeGlow} />
      <circle r={px * 2.25} className={styles.globeDot} />
    </svg>
  );
}
