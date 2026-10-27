"use client";

import { Component, ReactNode, Suspense, useEffect, useRef, useState } from "react";
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
  const [showRef, setShowRef] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("probe");
    if (fromUrl) setSelected(fromUrl);
    else try { setSelected(localStorage.getItem(SELECTED_KEY)); } catch { /* storage unavailable */ }
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

  // Follow a probe when a build of it starts, so the page shows whatever is happening
  // now; the build that was already finished when the page loaded doesn't count.
  const currentProbe = status?.current?.probe;
  const currentAt = status?.current?.at;
  const seenAt = useRef<number | null | undefined>(undefined);
  useEffect(() => {
    if (currentAt === undefined) return;
    if (seenAt.current === undefined) { seenAt.current = currentAt; return; }
    if (currentAt !== seenAt.current && currentProbe) { setSelected(currentProbe); setShowRef(false); }
    seenAt.current = currentAt;
  }, [currentProbe, currentAt]);

  const choose = (name: string) => {
    setSelected(name);
    setShowRef(false);
    try { localStorage.setItem(SELECTED_KEY, name); } catch { /* storage unavailable */ }
  };

  const probe = status?.probes.find((p) => p.name === selected) ?? status?.probes[0];
  const cur = status?.current?.probe === probe?.name ? status?.current : null;
  const b = probe?.build;
  const hasRef = !!probe?.refs.includes("reference-sheet.png");
  // Until a probe has its own build, its reference sheet is all there is to show.
  const sheetUrl = probe && (hasRef && (showRef || !b?.sheet)
    ? file(`refs/${probe.name}/reference-sheet.png`)
    : b?.sheet ? file(`out/${probe.name}/sheet.png`, b.started) : null);
  const glbUrl = probe && b?.glb ? file(`out/${probe.name}/${probe.name}.glb`, b.started) : null;
  const state = !status ? (error ? "offline" : "") : cur?.state === "running" ? "building"
    : b?.error ? "error" : b ? (b.ok ? "pass" : "fail") : "not built";
  const dot = cur?.state === "running" ? styles.running : b?.ok ? styles.ok : b ? styles.bad : "";

  const live = status?.current?.probe === probe?.name ? status?.current ?? null : null; // telemetry follows the tab
  const running = live?.state === "running";
  const anyRunning = status?.current?.state === "running";
  const passed = b?.checks?.filter((c) => c.ok).length ?? 0;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <nav className={styles.tabs}>
          {status?.probes.map((p) => (
            <button key={p.name} onClick={() => choose(p.name)} className={p.name === probe?.name ? styles.active : ""}>
              <span className={`${styles.dot} ${live?.probe === p.name && running ? styles.running : !p.build ? "" : p.build.ok ? styles.ok : styles.bad}`} />
              {p.name}
            </button>
          ))}
        </nav>
        <div className={styles.telemetry}>
          {live && running ? (
            <span className={styles.stepNow}>building {Math.max(1, STEPS.indexOf(live.step) + 1)}/{STEPS.length}</span>
          ) : live?.step === "error" ? (
            <span className={styles.bad}>build error</span>
          ) : null}
          {b ? (
            <>
              {b.checks && <span className={passed === b.checks.length ? styles.ok : styles.bad}>{passed}/{b.checks.length} checks</span>}
              <span className={styles.dim}>
                {b.seconds !== undefined ? `${b.seconds}s build · ` : ""}{ago(b.started, now)}{live ? ` · ${live.session}` : ""}
              </span>
            </>
          ) : probe ? <span className={styles.dim}>not built yet{hasRef ? " · showing reference" : ""}</span> : null}
          {anyRunning && status?.current?.probe !== probe?.name && (
            <span className={styles.dim}>building {status?.current?.probe}</span>
          )}
          {error && <span className={styles.bad}>offline</span>}
        </div>
      </header>
      <div className={styles.grid}>
        <div className={styles.viewCell}>
          {glbUrl ? <Viewer url={glbUrl} /> : <div className={styles.empty}>{probe ? "no export" : ""}</div>}
        </div>
        <div className={styles.side}>
          <div className={styles.sheetCell}>
            {sheetUrl ? <img className={styles.sheet} src={sheetUrl} alt="" /> : <div className={styles.empty}>no sheet</div>}
            {hasRef && b?.sheet && (
              <button className={styles.toggle} onClick={() => setShowRef((v) => !v)}>{showRef ? "reference" : "build"}</button>
            )}
          </div>
          <div className={styles.statusCell}>
            <div className={styles.statusLine}>
              <span className={`${styles.dot} ${dot}`} />
              <span>{probe?.name ?? "—"}</span>
              <span className={styles.dim}>{state}{b && cur?.state !== "running" ? ` · ${ago(b.started, now)}` : ""}</span>
            </div>
            {b?.error && <pre className={styles.error}>{b.error.trim().split("\n").slice(-3).join("\n")}</pre>}
            {b?.checks && (
              <table className={styles.checks}>
                <tbody>
                  {b.checks.map((c) => (
                    <tr key={c.name} className={c.ok ? "" : styles.bad}>
                      <td>{c.ok ? "✓" : "✗"}</td><td>{c.name}</td><td>{fmt(c.measured, c.unit)}</td><td className={styles.dim}>{fmt(c.expected, c.unit)}</td>
                    </tr>
                  ))}
                  {b.baseline?.changed && <tr className={styles.bad}><td>✗</td><td>baseline</td><td colSpan={2}>changed</td></tr>}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
