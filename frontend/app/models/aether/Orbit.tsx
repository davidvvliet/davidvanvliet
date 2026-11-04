import type { OrbitInset } from "./launchScene";
import styles from "./aether.module.css";

// The orbit, small, in a corner: the Moon, the orbit the craft is on (its low point lifting during the
// burn), the target orbit, and the craft. Orbit frame, in Mm: the low point down, the high point up.
export function Orbit({ o }: { o: OrbitInset }) {
  const Mm = 1e6;
  const ellipse = (rp: number) => {
    const a = (rp + o.ra) / 2, b = Math.sqrt(rp * o.ra);
    return { cy: -(o.ra - rp) / 2 / Mm, rx: b / Mm, ry: a / Mm };   // SVG y runs down: the high point is up
  };
  const now = ellipse(o.rp), goal = ellipse(o.target);
  return (
    <svg className={styles.orbit} viewBox="-2.7 -2.7 5.4 5.4">
      <ellipse cx={0} cy={goal.cy} rx={goal.rx} ry={goal.ry} fill="none" stroke="#ffb347" strokeOpacity={0.6} strokeWidth={0.025} strokeDasharray="0.1 0.08" />
      <ellipse cx={0} cy={now.cy} rx={now.rx} ry={now.ry} fill="none" stroke="#e8e8e8" strokeOpacity={0.7} strokeWidth={0.025} />
      <circle cx={0} cy={0} r={o.moon / Mm} fill="#2a2a2a" stroke="#888" strokeWidth={0.015} />
      <circle cx={o.x / Mm} cy={-o.y / Mm} r={0.08} fill="#00ff00" />
    </svg>
  );
}
