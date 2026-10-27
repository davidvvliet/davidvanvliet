"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { PHOTOS } from "../photos";
import styles from "./PhotoGrid.module.css";

const GAP_PX = 2;

// Square thumbnails filling the cell: picks the column count that gives the
// biggest tiles for the cell's current size. A click opens /photos/<n>.
export default function PhotoGrid() {
  const ref = useRef<HTMLDivElement>(null);
  const [layout, setLayout] = useState({ cols: 5, size: 0 });
  const pathname = usePathname();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const fit = () => {
      const { width, height } = el.getBoundingClientRect();
      let best = { cols: 1, size: 0 };
      for (let cols = 1; cols <= PHOTOS.length; cols++) {
        const rows = Math.ceil(PHOTOS.length / cols);
        const size = Math.floor(Math.min((width - GAP_PX * (cols - 1)) / cols, (height - GAP_PX * (rows - 1)) / rows));
        if (size > best.size) best = { cols, size };
      }
      setLayout(best);
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={ref} className={styles.wrap}>
      {layout.size > 0 && (
        <div
          className={styles.grid}
          style={{ gridTemplateColumns: `repeat(${layout.cols}, ${layout.size}px)`, gridAutoRows: `${layout.size}px`, gap: GAP_PX }}
        >
          {PHOTOS.map((p) => (
            <Link
              key={p.n}
              href={`/photos/${p.n}`}
              className={`${styles.tile} ${pathname === `/photos/${p.n}` ? styles.active : ""}`}
              aria-label={`Photo ${p.n}`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={p.thumb} alt="" loading="lazy" decoding="async" />
              {p.video && <span className={styles.play}>▶</span>}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
