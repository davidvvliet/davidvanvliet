"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { GlobePaths, Photo } from "../photoTypes";
import PhotoGlobe from "./PhotoGlobe";
import { useIsMobile } from "./useIsMobile";
import styles from "./PhotoView.module.css";

const SIDE_GLOBE = 120; // beside a portrait photo, in the space next to it
const ROW_GLOBE = 64; // under a landscape photo, at its left edge
const GAP = 12; // least space kept on each side of the side globe
const MIN_FIT = 0.8; // a photo may shrink to this share of its full size to make room beside it

export default function PhotoView({ photo, count, prevSlug, nextSlug, globe: globePaths }: { photo: Photo; count: number; prevSlug: string; nextSlug: string; globe?: GlobePaths }) {
  const globe = useIsMobile() ? undefined : globePaths; // no location globe on phones
  const router = useRouter();
  const frameRef = useRef<HTMLDivElement>(null);
  const aspect = photo.width && photo.height ? photo.width / photo.height : undefined;
  const portrait = !!aspect && aspect <= 1; // square photos too: the pane is wider than tall, so there is room beside them

  // A portrait (or square) photo's globe sits left of it when the pane has room
  // beside the photo, shrinking the photo a little if needed; otherwise it goes
  // under the photo's left edge, as for landscape.
  const [roomBeside, setRoomBeside] = useState(true);
  useEffect(() => {
    const el = frameRef.current;
    if (!el || !portrait || !globe) return;
    const check = () => {
      const { width, height } = el.getBoundingClientRect();
      const full = Math.min(width, height * aspect!);
      setRoomBeside(width - 2 * (SIDE_GLOBE + 2 * GAP) >= MIN_FIT * full);
    };
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => ro.disconnect();
  }, [portrait, globe, aspect]);
  const sideGlobe = !!globe && portrait && roomBeside;
  const rowGlobe = !!globe && !sideGlobe;

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
      <div ref={frameRef} className={styles.frame}>
        {/* Sized to the photo itself (when its size is known), so the side globe can sit against its edge. */}
        <div
          className={!aspect ? styles.mediaFill : sideGlobe ? `${styles.media} ${styles.mediaBeside}` : styles.media}
          style={aspect ? ({ "--aspect": aspect, "--side": `${SIDE_GLOBE}px`, "--gap": `${GAP}px` } as CSSProperties) : undefined}
        >
          {photo.video ? (
            <video key={photo.video} src={photo.video} poster={photo.image} className={styles.video} autoPlay muted loop playsInline />
          ) : (
            <Image key={photo.image} src={photo.image!} alt={photo.title ?? ""} fill sizes="(max-width: 768px) 100vw, 62vw" className={styles.image} />
          )}
          {sideGlobe && <PhotoGlobe globe={globe} size={SIDE_GLOBE} spritePx={48} className={styles.sideGlobe} />}
          {rowGlobe && <PhotoGlobe globe={globe} size={ROW_GLOBE} spritePx={30} className={styles.underGlobe} />}
        </div>
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
