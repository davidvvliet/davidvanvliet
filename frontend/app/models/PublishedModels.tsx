"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Viewer } from "./ModelsDashboard";
import styles from "./models.module.css";

// /models on the live site: the published models in the dashboard's 3D view (explode, hover for
// part sizes, click to focus). Locally /models is the build dashboard instead.
export default function PublishedModels({ models }: { models: { probe: string; title: string }[] }) {
  const asked = useSearchParams().get("probe");
  const probe = models.find((m) => m.probe === asked)?.probe ?? models[0]?.probe;
  if (!probe) return <div className={styles.page}><div className={styles.empty}>No published models yet.</div></div>;
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link href="/" className={styles.dim}>← back</Link>
        {models.map((m) => (
          <Link key={m.probe} href={`/models?probe=${m.probe}`} className={m.probe === probe ? undefined : styles.dim}>
            {m.title}
          </Link>
        ))}
      </header>
      <div className={styles.viewCell} style={{ flex: 1, borderRight: "none" }}>
        <Viewer probe={probe} url={`/models/${probe}.glb`} breakdown={null} stale={false} />
      </div>
    </div>
  );
}
