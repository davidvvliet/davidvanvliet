"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import type { Photo } from "../photoTypes";
import styles from "./PhotoGrid.module.css";

const GAP_PX = 2;

// Thumbnails filling the whole cell: picks the column count whose tiles come out
// closest to square, then stretches the grid to the cell's edges (no side margins).
// A click opens /photos/<n>.
export default function PhotoGrid({ photos }: { photos: Photo[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const [layout, setLayout] = useState({ cols: 0, rows: 0 });
  const pathname = usePathname();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const fit = () => {
      const style = getComputedStyle(el);
      const width = el.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
      const height = el.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
      if (width <= 0 || height <= 0 || photos.length === 0) return;
      let best = { cols: 1, rows: photos.length, skew: Infinity };
      for (let cols = 1; cols <= photos.length; cols++) {
        const rows = Math.ceil(photos.length / cols);
        const w = (width - GAP_PX * (cols - 1)) / cols;
        const h = (height - GAP_PX * (rows - 1)) / rows;
        const skew = Math.abs(Math.log(w / h)); // 0 = square
        if (skew < best.skew) best = { cols, rows, skew };
      }
      setLayout({ cols: best.cols, rows: best.rows });
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [photos.length]);

  return (
    <div ref={ref} className={styles.wrap}>
      {layout.cols > 0 && (
        <div
          className={styles.grid}
          style={{ gridTemplateColumns: `repeat(${layout.cols}, 1fr)`, gridTemplateRows: `repeat(${layout.rows}, 1fr)`, gap: GAP_PX }}
        >
          {photos.map((p) => (
            <Link
              key={p.n}
              href={`/photos/${p.n}`}
              className={`${styles.tile} ${pathname === `/photos/${p.n}` ? styles.active : ""}`}
              aria-label={`Photo ${p.n}`}
            >
              {p.video ? (
                // A clip plays in its tile like a GIF: muted, looping, inline.
                <video src={p.video} poster={p.image} autoPlay muted loop playsInline />
              ) : (
                <Image src={p.image!} alt="" fill sizes="96px" />
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
