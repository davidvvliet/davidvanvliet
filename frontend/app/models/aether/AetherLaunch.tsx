"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Site, type TerrainMeta } from "./ground";
import { aetherLaunch, type AetherLaunch as Launch, type LaunchUi, type OrbitInset } from "./launchScene";
import styles from "./aether.module.css";

// The launch happens inside the site's own solar-system scene (true scale), on the launch date:
// its Sun, Earth, Moon and stars. launchScene.ts adds the ground, the craft and the shots.
const SolarSystem = dynamic(() => import("../../components/SolarSystem").then((m) => m.SolarSystem), { ssr: false });

// The orbit, small, in a corner: the Moon, the orbit the craft is on (its low point lifting during the
// burn), the target orbit, and the craft. Orbit frame, in Mm: the low point down, the high point up.
function Orbit({ o }: { o: OrbitInset }) {
  const Mm = 1e6;
  const ellipse = (rp: number) => {
    const a = (rp + o.ra) / 2, b = Math.sqrt(rp * o.ra);
    return { cy: -(o.ra - rp) / 2 / Mm, rx: b / Mm, ry: a / Mm };   // SVG y runs down: the high point is up
  };
  const now = ellipse(o.rp), goal = ellipse(o.target);
  return (
    <svg className={styles.orbit} viewBox="-2.2 -2.2 4.4 4.4">
      <ellipse cx={0} cy={goal.cy} rx={goal.rx} ry={goal.ry} fill="none" stroke="#ffb347" strokeOpacity={0.6} strokeWidth={0.025} strokeDasharray="0.1 0.08" />
      <ellipse cx={0} cy={now.cy} rx={now.rx} ry={now.ry} fill="none" stroke="#e8e8e8" strokeOpacity={0.7} strokeWidth={0.025} />
      <circle cx={0} cy={0} r={o.moon / Mm} fill="#2a2a2a" stroke="#888" strokeWidth={0.015} />
      <circle cx={o.x / Mm} cy={-o.y / Mm} r={0.08} fill="#00ff00" />
    </svg>
  );
}

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
      {ui.orbit && <Orbit o={ui.orbit} />}
      <button className={styles.launch} disabled={running || !launch}
        onClick={() => { launch?.start(); setRunning(true); }}>
        Launch
      </button>
    </div>
  );
}
