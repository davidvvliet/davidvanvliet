"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Site, type TerrainMeta } from "./ground";
import { aetherLaunch, type AetherLaunch as Launch, type LaunchUi } from "./launchScene";
import { Orbit } from "./Orbit";
import { usePageStore } from "../../store/pageStore";
import { run } from "../../terminal/run";
import styles from "./aether.module.css";

const SolarSystem = dynamic(() => import("../../components/SolarSystem").then((m) => m.SolarSystem), { ssr: false });

type Star = { name: string; lightYears: number; spectral?: string; fact?: string } | null;

// `launch aether` on the main page: the launch page's scene, run inside the main view's frame.
// It starts by itself once the scene has drawn a second of frames (textures in, camera set).
export default function AetherScene({ onStarHover }: { onStarHover?: (s: Star) => void }) {
  const [launch, setLaunch] = useState<Launch | null>(null);
  const [ui, setUi] = useState<LaunchUi>({ phase: "", caption: "", readout: "" });
  useEffect(() => {
    let live = true;
    Promise.all([
      fetch("/models/aether-launch/terrain.json").then((r) => r.json() as Promise<TerrainMeta>),
      fetch("/models/aether-launch/terrain.bin").then((r) => r.arrayBuffer()),
    ]).then(([meta, bin]) => {
      if (!live) return;
      const inner = aetherLaunch(new Site(meta), bin, {
        ui: setUi,
        done: () => usePageStore.getState().pushTerminalLines([`__GRAY__Aether is in orbit. Use "${run("launch off", "launch off")}" to go back.`]),
      });
      let seconds = 0, started = false;
      setLaunch({
        ...inner,
        frame(h, jd, dt) {
          if (!started && (seconds += dt) > 1) { started = true; inner.start(); }
          inner.frame(h, jd, dt);
        },
      });
    });
    return () => { live = false; };
  }, []);
  return (
    <div className={styles.inScene}>
      {launch && <SolarSystem className={styles.canvas} extension={launch} scale="true" onStarHover={onStarHover} />}
      {ui.phase && (
        <div className={styles.phase}>
          <div className={styles.phaseName}>{ui.phase}</div>
          <div className={styles.caption}>{ui.caption}</div>
          <div className={styles.readout}>{ui.readout}</div>
        </div>
      )}
      {ui.orbit && <Orbit o={ui.orbit} />}
    </div>
  );
}
