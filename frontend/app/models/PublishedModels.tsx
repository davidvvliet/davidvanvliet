"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { PerspectiveCamera, View, useGLTF } from "@react-three/drei";
import StudioLights from "./StudioLights";
import * as THREE from "three";
import ModelsDashboard, { Viewer, type Focusable } from "./ModelsDashboard";
import styles from "./models.module.css";

export type Published = {
  probe: string; title: string; thumb: boolean; logos: string[]; explore: boolean; focus: Focusable[];
  sources: { title: string; url: string; licence: string | null; cited: number }[];
};

// A circuit board's parts, grouped into blocks (scripts/circuit/build.py).
export type Board = {
  board: string; title: string; purpose: string;
  source: { title: string; url: string; author: string; licence: string };
  blocks: { name: string; parts: { ref: string; value: string; package: string }[] }[];
};

// The card camera; scripts/blender/thumbnail.py renders the thumbnail from the same view.
const FOV = 35;
const FIT = 1.15; // bounding-sphere margin
const VIEW_DIR = new THREE.Vector3(0.6, 0.45, 0.66).normalize(); // from the model's centre, y up
const TURN_SECONDS = 20;

// The logos in each card's top right corner (and the detailed view's), from the spec's "logos": who
// built the real vehicle first (the grid lists models in ORGS order, anyone else last), then who else
// built it, each centred under the first. NASA's and SpaceX's are from Wikimedia Commons (public domain);
// JPL's red letters too (public domain, trademarked). North American Aviation's (copyright Boeing) and
// Rocketdyne's 1959 logo are English Wikipedia's fair-use files, recoloured light for the dark cards.
const LOGOS = {
  nasa: { name: "NASA", logo: "/logos/nasa.svg", height: 30 },
  spacex: { name: "SpaceX", logo: "/logos/spacex.svg", height: 10 },
  jpl: { name: "Jet Propulsion Laboratory", logo: "/logos/jpl.svg", height: 11 },
  naa: { name: "North American Aviation", logo: "/logos/north-american.png", height: 30 },
  rocketdyne: { name: "Rocketdyne", logo: "/logos/rocketdyne.png", height: 24 },
};
const ORGS = ["nasa", "spacex"];
const logosOf = (m: Published) => m.logos.filter((k): k is keyof typeof LOGOS => k in LOGOS).map((k) => LOGOS[k]);
const orgRank = (m: Published) => { const i = ORGS.indexOf(m.logos[0]); return i < 0 ? ORGS.length : i; };

// /models on the live site. Without ?probe: a grid of the published models, each spinning in its
// card. All cards draw into one shared canvas (one WebGL context however many models there are),
// and each shows its thumbnail until its model has loaded, which starts once the card is on screen.
// With ?probe=<name>: that model in the dashboard's viewer (explode, part sizes, click to focus;
// a spec's "viewer": {"explore": false} leaves only orbiting, its moving parts and the parts
// listed in "viewer.focus").
// Locally (`dashboard`), /models?dashboard is the build dashboard.
export default function PublishedModels({ models, circuit, dashboard }: {
  models: Published[]; circuit: string | null; dashboard: boolean;
}) {
  const params = useSearchParams();
  if (dashboard && params.has("dashboard")) return <ModelsDashboard />;
  const asked = params.get("probe");
  const model = models.find((m) => m.probe === asked);
  if (model) {
    const probe = model.probe;
    return (
      <div className={styles.page}>
        <Header>
          <Link href="/models" className={styles.dim}>← models</Link>
          <span>{model.title}</span>
        </Header>
        <div className={styles.detail}>
          <div className={styles.viewCell}>
            <Viewer probe={probe} url={`/models/${probe}.glb`} breakdown={null} stale={false} explore={model.explore} focusable={model.focus} />
            <Logos model={model} />
          </div>
          <Sources sources={model.sources} />
        </div>
      </div>
    );
  }
  // The vehicles in ORGS order, then on a row of its own the way into /circuits, shown by one of its boards.
  const cards: CardItem[] = [...models].sort((a, b) => orgRank(a) - orgRank(b)).map((m) => ({
    key: m.probe, href: `/models?probe=${m.probe}`, url: `/models/${m.probe}.glb`, title: m.title,
    thumb: m.thumb ? `/models/${m.probe}.webp` : undefined, corner: <Logos model={m} />,
  }));
  const more: CardItem[] = circuit ? [{
    key: "circuits", href: "/circuits", url: `/circuits/${circuit}.glb`, title: "My circuit experiments",
    corner: <span className={styles.cardArrow}>↗</span>,
  }] : [];
  return (
    <Grid back={{ href: "/", label: "← explore" }} title="Models" rows={[cards, more]} empty="No published models yet.">
      These models were created using my Blender harness with Opus 5.5. Only primary sources, mostly
      NASA&apos;s own, were used for maximum accuracy. The sources for each model can be found in its detailed view.
    </Grid>
  );
}

// A circuit board: its blocks beside it (pick one, in the list or on the board, to focus it), then its source.
export function BoardDetail({ board }: { board: Board }) {
  const [focus, setFocus] = useState<string | null>(null);
  const block = board.blocks.find((b) => b.name === focus);
  return (
    <div className={styles.page}>
      <Header>
        <Link href="/circuits" className={styles.dim}>← circuits</Link>
        <span>{board.title}</span>
      </Header>
      <div className={styles.detail}>
        <div className={styles.viewCell}>
          <Viewer probe={board.board} url={`/circuits/${board.board}.glb`} breakdown={null} stale={false} focus={focus} onFocus={setFocus} />
        </div>
        <aside className={styles.sources}>
          <div className={styles.dim}>{board.purpose}</div>
          <ol className={styles.blocks}>
            {board.blocks.map((b) => (
              <li key={b.name}>
                <button onClick={() => setFocus(b.name === focus ? null : b.name)} className={b.name === focus ? styles.active : ""}>
                  {b.name}
                </button>
                <span className={styles.dim}>{b.parts.length}</span>
              </li>
            ))}
          </ol>
          {block && (
            <table className={styles.parts}>
              <tbody>
                {block.parts.map((p) => (
                  <tr key={p.ref}><td>{p.ref}</td><td>{p.value}</td><td className={styles.dim}>{p.package}</td></tr>
                ))}
              </tbody>
            </table>
          )}
          <div className={styles.dim}>
            Design: <a href={board.source.url} target="_blank" rel="noopener noreferrer">{board.source.title}</a> by {board.source.author}, {board.source.licence}.
            Parts are KiCad&apos;s 3D library models.
          </div>
        </aside>
      </div>
    </div>
  );
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
export function Header({ children }: { children: React.ReactNode }) {
  return (
    <header className={styles.siteHeader}>
      <nav className={styles.siteLinks}>{children}</nav>
      <Link href="/" className={styles.siteName}>David van Vliet</Link>
    </header>
  );
}

// A card in a grid: its model spinning (its thumbnail until then), a title, and a corner (logos or an arrow).
export type CardItem = { key: string; href: string; url: string; title: string; thumb?: string; corner?: React.ReactNode };

// A page of cards (/models, /circuits): the header, the intro in green, then the cards, each row of
// `rows` starting a new line of the grid.
export function Grid({ back, title, rows, empty, children }: {
  back: { href: string; label: string }; title: string; rows: CardItem[][]; empty: string; children: React.ReactNode;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [spin, setSpin] = useState(true);
  useEffect(() => {
    const q = window.matchMedia("(prefers-reduced-motion: reduce)");
    const set = () => setSpin(!q.matches);
    set();
    q.addEventListener("change", set);
    return () => q.removeEventListener("change", set);
  }, []);
  const groups = rows.filter((r) => r.length);
  return (
    <div className={styles.page}>
      <Header>
        <Link href={back.href} className={styles.dim}>{back.label}</Link>
        <span>{title}</span>
      </Header>
      <p className={styles.intro}><span>{children}</span></p>
      <div className={styles.gridArea}>
        <div ref={scroller} className={styles.cards}>
          {groups.length === 0 && <div className={styles.empty}>{empty}</div>}
          {groups.map((row, i) => [
            i > 0 && <div key={`break${i}`} className={styles.rowBreak} />,
            ...row.map((c) => <Card key={c.key} item={c} spin={spin} root={scroller} />),
          ])}
        </div>
        <Canvas style={{ position: "absolute", inset: 0, pointerEvents: "none" }} dpr={[1, 2]} gl={{ alpha: true, antialias: true }}>
          <View.Port />
        </Canvas>
      </div>
    </div>
  );
}

function Card({ item, spin, root }: { item: CardItem; spin: boolean; root: React.RefObject<HTMLDivElement | null> }) {
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
    <Link ref={card} href={item.href} className={styles.card}
      onPointerEnter={() => (hover.current = true)} onPointerLeave={() => (hover.current = false)}>
      {item.thumb && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={item.thumb} alt="" className={`${styles.thumb} ${ready ? styles.thumbGone : ""}`} />
      )}
      <View className={styles.cardView}>
        <PerspectiveCamera makeDefault fov={FOV} />
        <StudioLights />
        {seen && (
          <Suspense fallback={null}>
            <Spinning url={item.url} spin={spin} hover={hover} onReady={() => setReady(true)} />
          </Suspense>
        )}
      </View>
      <span className={styles.cardTitle}>{item.title}</span>
      {item.corner}
    </Link>
  );
}

// Who built it, as a column in the top right corner (cards and the detailed view).
function Logos({ model }: { model: Published }) {
  return (
    <span className={styles.cardLogos}>
      {logosOf(model).map((o) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={o.logo} src={o.logo} alt={o.name} title={o.name} style={{ height: o.height }} />
      ))}
    </span>
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
