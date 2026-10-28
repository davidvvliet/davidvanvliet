"use client";

import Image from "next/image";
import Link from "next/link";
import type { Photo } from "../photoTypes";
import styles from "./PhotoView.module.css";

export default function PhotoView({ photo, count, prevSlug, nextSlug }: { photo: Photo; count: number; prevSlug: string; nextSlug: string }) {
  return (
    <div className={styles.view}>
      <div className={styles.frame}>
        {photo.video ? (
          <video key={photo.video} src={photo.video} poster={photo.image} className={styles.video} autoPlay muted loop playsInline />
        ) : (
          <Image key={photo.image} src={photo.image!} alt={photo.title ?? ""} fill sizes="(max-width: 768px) 100vw, 62vw" className={styles.image} />
        )}
      </div>
      {photo.title && (
        <div className={styles.text}>
          <p className={styles.title}>{photo.title}</p>
          {photo.caption && <p className={styles.caption}>{photo.caption}</p>}
        </div>
      )}
      <div className={styles.nav}>
        <Link href={`/photos/${prevSlug}`} className={styles.arrow} aria-label="Previous photo">‹</Link>
        <span className={styles.count}>{photo.n} / {count}</span>
        <Link href={`/photos/${nextSlug}`} className={styles.arrow} aria-label="Next photo">›</Link>
      </div>
    </div>
  );
}
