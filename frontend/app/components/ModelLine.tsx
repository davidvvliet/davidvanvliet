"use client";

import { useEffect, useRef, useState } from "react";
import { Viewer } from "../models/ModelsDashboard";
import styles from "./Terminal.module.css";

// A terminal line with one of our published models (`__MODEL__<probe>`), in the /models viewer:
// drag to turn, Explode, hover a part for its size, click to focus it. "open ↗" opens the full
// viewer in a new tab, so a running mission carries on. The thumbnail shows at once; the model
// (several MB) loads once the line is on screen. Restored from a previous visit, and on touch
// screens, the thumbnail stays until it is clicked.
export default function ModelLine({ probe, restored, onSized }: { probe: string; restored?: boolean; onSized: () => void }) {
  const box = useRef<HTMLSpanElement>(null);
  const [wanted, setWanted] = useState(false); // clicked, or eligible to load by itself
  const [seen, setSeen] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!restored && !window.matchMedia("(pointer: coarse)").matches) setWanted(true);
  }, [restored]);
  useEffect(() => {
    const el = box.current;
    if (!el || !wanted) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } });
    io.observe(el);
    return () => io.disconnect();
  }, [wanted]);
  const live = wanted && seen;
  return (
    <span ref={box} className={styles.modelWrap}>
      {live && (
        <Viewer probe={probe} url={`/models/${probe}.glb`} breakdown={null} stale={false} compact onReady={() => setReady(true)} />
      )}
      {!ready && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={`/models/${probe}.webp`} alt="" className={styles.modelThumb} onLoad={onSized}
          onClick={() => setWanted(true)} style={{ cursor: live ? "progress" : "pointer" }} />
      )}
      <a href={`/models?probe=${probe}`} target="_blank" rel="noopener noreferrer" className={styles.modelOpen}>open ↗</a>
    </span>
  );
}
