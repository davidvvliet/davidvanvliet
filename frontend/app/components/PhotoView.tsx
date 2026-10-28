"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import type { Photo } from "../photoTypes";
import styles from "./PhotoView.module.css";

export default function PhotoView({ photo, count, prevSlug, nextSlug }: { photo: Photo; count: number; prevSlug: string; nextSlug: string }) {
  const router = useRouter();

  // ← / → step through the photos. Left alone while a text field holds text, so
  // the arrows still move the caret there; an empty terminal prompt lets them through.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      const el = e.target as HTMLElement;
      if ((el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) && el.value) return;
      if (el.isContentEditable) return;
      e.preventDefault();
      router.push(`/photos/${e.key === "ArrowLeft" ? prevSlug : nextSlug}`);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router, prevSlug, nextSlug]);

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
