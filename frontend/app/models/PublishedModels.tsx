"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Environment, Lightformer, PerspectiveCamera, View, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import ModelsDashboard, { Viewer } from "./ModelsDashboard";
import styles from "./models.module.css";

export type Published = {
  probe: string; title: string; thumb: boolean;
  sources: { title: string; url: string; licence: string | null; cited: number }[];
};

// The card camera; scripts/blender/thumbnail.py renders the thumbnail from the same view.
const FOV = 35;
const FIT = 1.15; // bounding-sphere margin
const VIEW_DIR = new THREE.Vector3(0.6, 0.45, 0.66).normalize(); // from the model's centre, y up
const TURN_SECONDS = 20;

// /models on the live site. Without ?probe: a grid of the published models, each spinning in its
// card. All cards draw into one shared canvas (one WebGL context however many models there are),
// and each shows its thumbnail until its model has loaded, which starts once the card is on screen.
// With ?probe=<name>: that model in the dashboard's viewer (explode, part sizes, click to focus).
// Locally (`dashboard`), /models?dashboard is the build dashboard.
export default function PublishedModels({ models, dashboard }: { models: Published[]; dashboard: boolean }) {
  const params = useSearchParams();
  if (dashboard && params.has("dashboard")) return <ModelsDashboard />;
  const asked = params.get("probe");
  const probe = models.find((m) => m.probe === asked)?.probe;
  if (probe) {
    return (
      <div className={styles.page}>
        <Header>
          <Link href="/models" className={styles.dim}>← all models</Link>
          {models.map((m) => (
            <Link key={m.probe} href={`/models?probe=${m.probe}`} className={m.probe === probe ? undefined : styles.dim}>
              {m.title}
            </Link>
          ))}
        </Header>
        <div className={styles.detail}>
          <div className={styles.viewCell}>
            <Viewer probe={probe} url={`/models/${probe}.glb`} breakdown={null} stale={false} />
          </div>
          <Sources sources={models.find((m) => m.probe === probe)!.sources} />
        </div>
      </div>
    );
  }
  return <Grid models={models} />;
}

// The sources the model was built from (its spec's list), and how many of its values cite each.
function Sources({ sources }: { sources: Published["sources"] }) {
  return (
    <aside className={styles.sources}>
      <div className={styles.sourcesTitle}>Sources</div>
      {sources.length === 0 && <div className={styles.dim}>None listed.</div>}
      <ol>
        {sources.map((s) => (
          <li key={s.url}>
            <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a>
            <div className={styles.dim}>
              {s.licence ?? "licence not given"}{s.cited ? ` · ${s.cited} ${s.cited === 1 ? "value" : "values"}` : ""}
            </div>
          </li>
        ))}
      </ol>
    </aside>
  );
}

// Links on the left, the name centred in the home page's title style.
function Header({ children }: { children: React.ReactNode }) {
  return (
    <header className={styles.siteHeader}>
      <nav className={styles.siteLinks}>{children}</nav>
      <Link href="/" className={styles.siteName}>David van Vliet</Link>
    </header>
  );
}

function Grid({ models }: { models: Published[] }) {
  const scroller = useRef<HTMLDivElement>(null);
  const [spin, setSpin] = useState(true);
  useEffect(() => {
    const q = window.matchMedia("(prefers-reduced-motion: reduce)");
    const set = () => setSpin(!q.matches);
    set();
    q.addEventListener("change", set);
    return () => q.removeEventListener("change", set);
  }, []);
  return (
    <div className={styles.page}>
      <Header>
        <Link href="/" className={styles.dim}>← back</Link>
        <span>Models</span>
      </Header>
      <p className={styles.intro}>
        <span>
        These models were created step by step using my Blender x Opus 5.5 harness. Only the direct sources were
        used in the creation of each of these models for maximum accuracy. The sources for each model are listed next to it when you open it.
        </span>
      </p>
      <div className={styles.gridArea}>
        <div ref={scroller} className={styles.cards}>
          {models.length === 0 && <div className={styles.empty}>No published models yet.</div>}
          {models.map((m) => <Card key={m.probe} model={m} spin={spin} root={scroller} />)}
        </div>
        <Canvas style={{ position: "absolute", inset: 0, pointerEvents: "none" }} dpr={[1, 2]} gl={{ alpha: true, antialias: true }}>
          <View.Port />
        </Canvas>
      </div>
    </div>
  );
}

function Card({ model, spin, root }: { model: Published; spin: boolean; root: React.RefObject<HTMLDivElement | null> }) {
  const card = useRef<HTMLAnchorElement>(null);
  const [seen, setSeen] = useState(false); // on screen at least once: load the model
  const [ready, setReady] = useState(false);
  const hover = useRef(false);
  useEffect(() => {
    const el = card.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } },
      { root: root.current, rootMargin: "200px" });
    io.observe(el);
    return () => io.disconnect();
  }, [root]);
  return (
    <Link ref={card} href={`/models?probe=${model.probe}`} className={styles.card}
      onPointerEnter={() => (hover.current = true)} onPointerLeave={() => (hover.current = false)}>
      {model.thumb && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={`/models/${model.probe}.webp`} alt="" className={`${styles.thumb} ${ready ? styles.thumbGone : ""}`} />
      )}
      <View className={styles.cardView}>
        <PerspectiveCamera makeDefault fov={FOV} />
        <ambientLight intensity={0.25} />
        <directionalLight position={[5, 7, 6]} intensity={3} />
        <directionalLight position={[-6, -1, -3]} intensity={0.6} />
        <Environment resolution={64}>
          <Lightformer form="rect" intensity={2} position={[0, 5, 0]} scale={[10, 10, 1]} rotation-x={Math.PI / 2} />
          <Lightformer form="rect" intensity={0.8} position={[-5, 1, 3]} scale={[6, 4, 1]} rotation-y={Math.PI / 3} />
          <Lightformer form="rect" intensity={0.4} position={[5, -1, -3]} scale={[6, 4, 1]} rotation-y={-Math.PI / 1.5} />
        </Environment>
        {seen && (
          <Suspense fallback={null}>
            <Spinning url={`/models/${model.probe}.glb`} spin={spin} hover={hover} onReady={() => setReady(true)} />
          </Suspense>
        )}
      </View>
      <span className={styles.cardTitle}>{model.title}</span>
    </Link>
  );
}

// The model turning about its vertical axis, framed so its bounding sphere stays in the card.
// The spin pauses while the card is hovered.
function Spinning({ url, spin, hover, onReady }: {
  url: string; spin: boolean; hover: React.RefObject<boolean>; onReady: () => void;
}) {
  const gltf = useGLTF(url);
  const { scene, centre, radius } = useMemo(() => {
    const s = gltf.scene.clone(true); // the viewer gets its own copy of the cached scene too
    const sphere = new THREE.Box3().setFromObject(s).getBoundingSphere(new THREE.Sphere());
    return { scene: s, centre: sphere.center, radius: sphere.radius };
  }, [gltf.scene]);
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  useEffect(() => {
    const dist = (radius * FIT) / Math.sin(THREE.MathUtils.degToRad(FOV) / 2);
    camera.position.copy(centre).addScaledVector(VIEW_DIR, dist);
    camera.near = dist / 100;
    camera.far = dist * 10;
    camera.lookAt(centre);
    camera.updateProjectionMatrix();
  }, [camera, centre, radius]);
  useEffect(onReady, [onReady]);
  const turn = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    if (spin && !hover.current && turn.current) turn.current.rotation.y += (dt * 2 * Math.PI) / TURN_SECONDS;
  });
  return (
    <group position={centre} ref={turn}>
      <primitive object={scene} position={centre.clone().negate()} />
    </group>
  );
}
