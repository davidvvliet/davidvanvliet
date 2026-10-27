"use client";

import { Component, ReactNode, Suspense, useEffect, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { Environment, Lightformer, OrbitControls, useGLTF } from "@react-three/drei";
import styles from "./models.module.css";

type Check = { name: string; ok: boolean; measured: number | null; expected: number; unit: string; detail?: string; source?: string | null };
type Build = {
  started: number; ok?: boolean; error?: string; seconds?: number; checks?: Check[];
  sheet?: string; glb?: string; grid_m?: Record<string, number>; size_m?: number[];
  history?: string[]; baseline?: { diff: number; changed: boolean } | null; approved?: number;
};
type Probe = {
  name: string; title: string; fixture: boolean; note: string | null;
  sources: { title?: string; url?: string }[]; referenceModel: { url?: string; note?: string } | null;
  refs: string[]; build: Build | null;
};
type Current = { probe: string; step: string; state: string; message: string | null; session: string; at: number };
type Status = { updated: number | null; current: Current | null; probes: Probe[] };

const STEPS = ["spec", "model", "checks", "render", "export", "done"];
const SELECTED_KEY = "models-dashboard-probe";
const file = (rel: string, v?: number) => `/api/models/file/${rel}${v ? `?v=${v}` : ""}`;

function ago(t: number, now: number) {
  const s = Math.max(0, Math.round(now / 1000 - t));
  return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)}m ago` : `${Math.round(s / 3600)}h ago`;
}

// Frames the model once it loads: camera on a fixed three-quarter line, far enough
// that its bounding sphere fits the view, orbiting its centre.
function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const controls = useThree((s) => s.controls) as unknown as { target: THREE.Vector3; update: () => void } | null;
  useEffect(() => {
    const sphere = new THREE.Box3().setFromObject(scene).getBoundingSphere(new THREE.Sphere());
    const fov = THREE.MathUtils.degToRad(camera.fov) * Math.min(1, camera.aspect);
    const dist = (sphere.radius * 1.15) / Math.sin(fov / 2);
    camera.position.copy(sphere.center).addScaledVector(new THREE.Vector3(0.6, 0.45, 0.66).normalize(), dist);
    camera.near = dist / 100;
    camera.far = dist * 10;
    camera.updateProjectionMatrix();
    if (controls) { controls.target.copy(sphere.center); controls.update(); }
    else camera.lookAt(sphere.center);
  }, [scene, camera, controls]);
  return <primitive object={scene} />;
}

class ViewerBoundary extends Component<{ children: ReactNode; resetKey: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidUpdate(prev: { resetKey: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false });
  }
  render() { return this.state.failed ? <div className={styles.empty}>Could not load the model.</div> : this.props.children; }
}

function Viewer({ url }: { url: string }) {
  return (
    <ViewerBoundary resetKey={url}>
      <Canvas camera={{ fov: 35, position: [6, 4, 8] }} dpr={[1, 2]}>
        <color attach="background" args={["#090909"]} />
        <ambientLight intensity={0.25} />
        <directionalLight position={[5, 7, 6]} intensity={3} />
        <directionalLight position={[-6, -1, -3]} intensity={0.6} />
        {/* Local studio reflections so foil and metal read as metal (no HDR download). */}
        <Environment resolution={64}>
          <Lightformer form="rect" intensity={2} position={[0, 5, 0]} scale={[10, 10, 1]} rotation-x={Math.PI / 2} />
          <Lightformer form="rect" intensity={0.8} position={[-5, 1, 3]} scale={[6, 4, 1]} rotation-y={Math.PI / 3} />
          <Lightformer form="rect" intensity={0.4} position={[5, -1, -3]} scale={[6, 4, 1]} rotation-y={-Math.PI / 1.5} />
        </Environment>
        <Suspense fallback={null}><Model key={url} url={url} /></Suspense>
        <OrbitControls makeDefault />
      </Canvas>
    </ViewerBoundary>
  );
}

function fmt(v: number | null, unit: string) {
  if (v === null) return "—";
  if (unit === "bytes") return `${(v / 1e6).toFixed(2)} MB`;
  if (unit === "tris") return v.toLocaleString();
  return `${v} ${unit}`;
}

export default function ModelsDashboard() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [sheetOverride, setSheetOverride] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    try { setSelected(localStorage.getItem(SELECTED_KEY)); } catch { /* storage unavailable */ }
    let alive = true;
    const poll = async () => {
      try {
        const res = await fetch("/api/models/status", { cache: "no-store" });
        if (!res.ok) throw new Error();
        const next: Status = await res.json();
        if (alive) { setStatus(next); setError(false); }
      } catch { if (alive) setError(true); }
      if (alive) setNow(Date.now());
    };
    poll();
    const id = setInterval(poll, 1000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // Follow the probe being built, so the page shows whatever is happening now.
  const currentProbe = status?.current?.probe;
  const currentAt = status?.current?.at;
  useEffect(() => {
    if (currentProbe) { setSelected(currentProbe); setSheetOverride(null); }
  }, [currentProbe, currentAt]);

  const choose = (name: string) => {
    setSelected(name);
    setSheetOverride(null);
    try { localStorage.setItem(SELECTED_KEY, name); } catch { /* storage unavailable */ }
  };

  if (!status) return <main className={styles.page}><div className={styles.empty}>{error ? "Cannot reach /api/models/status." : "Loading…"}</div></main>;

  const probe = status.probes.find((p) => p.name === selected) ?? status.probes[0];
  const cur = status.current;
  const running = cur?.state === "running";
  const b = probe?.build;
  const sheetUrl = sheetOverride ?? (b?.sheet ? file(`out/${probe.name}/sheet.png`, b.started) : null);
  const glbUrl = b?.glb ? file(`out/${probe.name}/${probe.name}.glb`, b.started) : null;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div className={styles.title}>Probe models <span className={styles.dim}>· dev</span></div>
        {cur ? (
          <div className={styles.current}>
            <span className={`${styles.dot} ${running ? styles.running : cur.state === "done" ? styles.ok : styles.bad}`} />
            <b>{cur.probe}</b>
            <span className={styles.steps}>
              {STEPS.map((s) => {
                const i = STEPS.indexOf(s), at = STEPS.indexOf(cur.step);
                const cls = cur.step === "error" ? (s === "done" ? styles.stepBad : "") : i < at || (i === at && !running) ? styles.stepDone : i === at ? styles.stepNow : "";
                return <span key={s} className={cls}>{s}</span>;
              })}
            </span>
            <span className={styles.dim}>{cur.message ?? ""} · {cur.session} · {ago(cur.at, now)}</span>
          </div>
        ) : <div className={styles.dim}>No builds yet. Run: npm run model &lt;probe&gt;</div>}
        {error && <div className={styles.bad}>Lost contact with the dev server.</div>}
      </header>

      <nav className={styles.tabs}>
        {status.probes.map((p) => (
          <button key={p.name} onClick={() => choose(p.name)} className={`${styles.tab} ${p.name === probe?.name ? styles.tabActive : ""}`}>
            <span className={`${styles.dot} ${!p.build ? "" : p.build.ok ? styles.ok : styles.bad}`} />
            {p.title}{p.fixture && <span className={styles.dim}> (fixture)</span>}
          </button>
        ))}
      </nav>

      {probe && (
        <>
          {probe.note && <p className={styles.note}>{probe.note}</p>}
          <section className={styles.grid}>
            <div className={styles.panel}>
              <div className={styles.panelHead}>3D <span className={styles.dim}>drag to orbit · scroll to zoom</span></div>
              <div className={styles.viewer}>{glbUrl ? <Viewer url={glbUrl} /> : <div className={styles.empty}>No export yet.</div>}</div>
            </div>
            <div className={styles.panel}>
              <div className={styles.panelHead}>
                Contact sheet <span className={styles.dim}>front · ¾ / side · top
                  {b?.grid_m && ` · grid ${Object.entries(b.grid_m).map(([v, m]) => `${v} ${m} m`).join(", ")}`}</span>
              </div>
              {sheetUrl ? <img className={styles.sheet} src={sheetUrl} alt={`${probe.title} contact sheet`} /> : <div className={styles.empty}>No render yet.</div>}
              {sheetOverride && <button className={styles.link} onClick={() => setSheetOverride(null)}>← back to latest</button>}
            </div>
          </section>

          {probe.refs.length > 0 && (
            <section className={styles.panel}>
              <div className={styles.panelHead}>Reference</div>
              <div className={styles.refs}>
                {probe.refs.map((r) => <a key={r} href={file(`refs/${probe.name}/${r}`)} target="_blank" rel="noreferrer"><img src={file(`refs/${probe.name}/${r}`)} alt={r} /></a>)}
              </div>
            </section>
          )}

          <section className={styles.panel}>
            <div className={styles.panelHead}>
              Checks {b && <span className={b.ok ? styles.ok : styles.bad}>{b.ok ? "all pass" : "failing"}</span>}
              {b?.seconds !== undefined && <span className={styles.dim}> · built in {b.seconds}s, {ago(b.started, now)}</span>}
              {b?.approved && <span className={styles.dim}> · approved {ago(b.approved, now)}</span>}
            </div>
            {b?.error && <pre className={styles.error}>{b.error}</pre>}
            {b?.checks && (
              <table className={styles.table}>
                <thead><tr><th /><th>check</th><th>measured</th><th>spec</th><th /><th>source</th></tr></thead>
                <tbody>
                  {b.checks.map((c) => (
                    <tr key={c.name}>
                      <td className={c.ok ? styles.ok : styles.bad}>{c.ok ? "✓" : "✗"}</td>
                      <td>{c.name}</td>
                      <td>{fmt(c.measured, c.unit)}</td>
                      <td>{fmt(c.expected, c.unit)}</td>
                      <td className={styles.dim}>{c.detail}</td>
                      <td className={styles.dim}>{c.source?.startsWith("http") ? <a href={c.source} target="_blank" rel="noreferrer">link</a> : c.source}</td>
                    </tr>
                  ))}
                  {b.baseline && (
                    <tr>
                      <td className={b.baseline.changed ? styles.bad : styles.ok}>{b.baseline.changed ? "✗" : "✓"}</td>
                      <td>baseline</td><td colSpan={2}>{b.baseline.changed ? "sheet changed" : "unchanged"}</td>
                      <td className={styles.dim}>diff {b.baseline.diff}</td><td />
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </section>

          {b?.history && b.history.length > 1 && (
            <section className={styles.panel}>
              <div className={styles.panelHead}>History <span className={styles.dim}>click to compare</span></div>
              <div className={styles.history}>
                {[...b.history].reverse().map((h) => {
                  const url = file(`out/${probe.name}/history/${h}`);
                  return (
                    <button key={h} onClick={() => setSheetOverride(url)} className={sheetOverride === url ? styles.historyActive : ""}>
                      <img src={url} alt={h} />
                      <span>{h.replace(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})\.png$/, "$4:$5:$6")}</span>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {(probe.sources.some((s) => s.url) || probe.referenceModel?.url) && (
            <section className={styles.panel}>
              <div className={styles.panelHead}>Sources</div>
              <ul className={styles.sources}>
                {probe.referenceModel?.url && <li><a href={probe.referenceModel.url} target="_blank" rel="noreferrer">Reference model</a> <span className={styles.dim}>{probe.referenceModel.note}</span></li>}
                {probe.sources.filter((s) => s.url).map((s) => <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title || s.url}</a></li>)}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
