"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Site, type TerrainMeta } from "./ground";
import { aetherLaunch, type AetherLaunch as Launch, type LaunchUi } from "./launchScene";
import styles from "./aether.module.css";

// The launch happens inside the site's own solar-system scene (true scale), on the launch date:
// its Sun, Earth, Moon and stars. launchScene.ts adds the ground, the craft and the shots.
const SolarSystem = dynamic(() => import("../../components/SolarSystem").then((m) => m.SolarSystem), { ssr: false });

export default function AetherLaunch() {
  const [launch, setLaunch] = useState<Launch | null>(null);
  const [running, setRunning] = useState(false);
  const [ui, setUi] = useState<LaunchUi>({ phase: "", caption: "", readout: "" });
  useEffect(() => {
    let live = true;
    Promise.all([
      fetch("/models/aether-launch/terrain.json").then((r) => r.json() as Promise<TerrainMeta>),
      fetch("/models/aether-launch/terrain.bin").then((r) => r.arrayBuffer()),
    ]).then(([meta, bin]) => {
      if (live) setLaunch(aetherLaunch(new Site(meta), bin, { ui: setUi, done: () => setRunning(false) }));
    });
    return () => { live = false; };
  }, []);
  return (
    <div className={styles.page}>
      {launch && <SolarSystem className={styles.canvas} extension={launch} scale="true" />}
      <div className={styles.title}>Altair Aether</div>
      {ui.phase && (
        <div className={styles.phase}>
          <div className={styles.phaseName}>{ui.phase}</div>
          <div className={styles.caption}>{ui.caption}</div>
          <div className={styles.readout}>{ui.readout}</div>
        </div>
      )}
      <button className={styles.launch} disabled={running || !launch}
        onClick={() => { launch?.start(); setRunning(true); }}>
        Launch
      </button>
    </div>
  );
}
