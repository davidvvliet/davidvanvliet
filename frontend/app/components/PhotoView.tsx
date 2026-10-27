"use client";

import Link from "next/link";
import { PHOTOS, getPhoto } from "../photos";
import styles from "./PhotoView.module.css";

export default function PhotoView({ n }: { n: number }) {
  const photo = getPhoto(n);
  if (!photo) return null;
  const prev = n > 1 ? n - 1 : PHOTOS.length;
  const next = n < PHOTOS.length ? n + 1 : 1;
  return (
    <div className={styles.view}>
      <div className={styles.frame}>
        {photo.video ? (
          <video key={photo.video} src={photo.video} poster={photo.src} className={styles.media} autoPlay muted loop playsInline />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img key={photo.src} src={photo.src} alt="" className={styles.media} />
        )}
      </div>
      <div className={styles.nav}>
        <Link href={`/photos/${prev}`} className={styles.arrow} aria-label="Previous photo">‹</Link>
        <span className={styles.count}>{n} / {PHOTOS.length}</span>
        <Link href={`/photos/${next}`} className={styles.arrow} aria-label="Next photo">›</Link>
      </div>
    </div>
  );
}
