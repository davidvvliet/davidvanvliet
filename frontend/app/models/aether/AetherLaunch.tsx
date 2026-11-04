"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Site, type TerrainMeta } from "./ground";
import { aetherLaunch, type AetherLaunch as Launch, type LaunchUi, type PartLabel } from "./launchScene";
import { Orbit } from "./Orbit";
import styles from "./aether.module.css";

// The launch happens inside the site's own solar-system scene (true scale), on the launch date:
// its Sun, Earth, Moon and stars. launchScene.ts adds the ground, the craft and the shots.
const SolarSystem = dynamic(() => import("../../components/SolarSystem").then((m) => m.SolarSystem), { ssr: false });

export default function AetherLaunch() {
  const [launch, setLaunch] = useState<Launch | null>(null);
  const [running, setRunning] = useState(false);
  const [ui, setUi] = useState<LaunchUi>({ phase: "", caption: "", readout: "" });
  const [part, setPart] = useState<PartLabel>(null);
  const [star, setStar] = useState<{ name: string; lightYears: number; spectral?: string; fact?: string } | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all([
      fetch("/models/aether-launch/terrain.json").then((r) => r.json() as Promise<TerrainMeta>),
      fetch("/models/aether-launch/terrain.bin").then((r) => r.arrayBuffer()),
    ]).then(([meta, bin]) => {
      if (live) setLaunch(aetherLaunch(new Site(meta), bin, { ui: setUi, done: () => setRunning(false), part: setPart }));
    });
    return () => { live = false; };
  }, []);
  return (
    <div className={styles.page}>
      {launch && <SolarSystem className={styles.canvas} extension={launch} scale="true" onStarHover={setStar} />}
      {part || ui.note ? (
        <div className={styles.star}>
          <div className={styles.starRow}>
            <span className={styles.starName}>{part ? part.name : ui.note}</span>
            {part && <span className={styles.starDim}>{part.size}</span>}
          </div>
        </div>
      ) : star && (
        <div className={styles.star}>
          <div className={styles.starRow}>
            <span className={styles.starName}>{star.name}</span>
            <span className={styles.starDim}>{star.lightYears.toLocaleString()} light-years</span>
            {star.spectral && <span className={styles.starType}>Type {star.spectral}</span>}
          </div>
          {star.fact && <div className={styles.starFact}>{star.fact}</div>}
        </div>
      )}
      <div className={styles.title}>Altair Aether</div>
      {ui.phase && (
        <div className={styles.phase}>
          <div className={styles.phaseName}>{ui.phase}</div>
          <div className={styles.caption}>{ui.caption}</div>
          <div className={styles.readout}>{ui.readout}</div>
        </div>
      )}
      {ui.orbit && <Orbit o={ui.orbit} />}
      <button className={styles.launch} disabled={running || !launch}
        onClick={() => { launch?.start(); setRunning(true); }}>
        Launch
      </button>
    </div>
  );
}
