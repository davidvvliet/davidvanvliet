"use client";

import Image from "next/image";
import Link from "next/link";
import type { Photo } from "../photoTypes";
import styles from "./PhotoView.module.css";

export default function PhotoView({ photo, count }: { photo: Photo; count: number }) {
  const n = photo.n;
  const prev = n > 1 ? n - 1 : count;
  const next = n < count ? n + 1 : 1;
  return (
    <div className={styles.view}>
      <div className={styles.frame}>
        {photo.video ? (
          <video key={photo.video} src={photo.video} poster={photo.image} className={styles.video} autoPlay muted loop playsInline />
        ) : (
          <Image key={photo.image} src={photo.image!} alt="" fill sizes="(max-width: 768px) 100vw, 62vw" className={styles.image} />
        )}
      </div>
      <div className={styles.nav}>
        <Link href={`/photos/${prev}`} className={styles.arrow} aria-label="Previous photo">‹</Link>
        <span className={styles.count}>{n} / {count}</span>
        <Link href={`/photos/${next}`} className={styles.arrow} aria-label="Next photo">›</Link>
      </div>
    </div>
  );
}
