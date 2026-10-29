"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { Viewer } from "../models/ModelsDashboard";
import styles from "../models/models.module.css";
import own from "./circuit.module.css";

export type Board = {
  board: string; title: string; purpose: string;
  source: { title: string; url: string; author: string; licence: string };
  blocks: { name: string; parts: { ref: string; value: string; package: string }[] }[];
};

// /circuit: a real circuit board in 3D, its parts grouped into the blocks its designer drew on the
// schematic. Pick a block (in the list or on the board) to focus it; Explode pulls the blocks apart.
export default function Circuit({ boards }: { boards: Board[] }) {
  const params = useSearchParams();
  const board = boards.find((b) => b.board === params.get("board")) ?? boards[0];
  const [focus, setFocus] = useState<string | null>(null);
  const block = board?.blocks.find((b) => b.name === focus);
  return (
    <div className={styles.page}>
      <header className={styles.siteHeader}>
        <nav className={styles.siteLinks}>
          <Link href="/" className={styles.dim}>← explore</Link>
          <span>Circuit</span>
          {boards.length > 1 && boards.map((b) => (
            <Link key={b.board} href={`/circuit?board=${b.board}`} className={b === board ? "" : styles.dim}>{b.title}</Link>
          ))}
        </nav>
        <Link href="/" className={styles.siteName}>David van Vliet</Link>
      </header>
      {!board ? <div className={styles.empty}>No boards yet.</div> : (
        <div className={styles.detail}>
          <div className={styles.viewCell}>
            <Viewer key={board.board} probe={board.board} url={`/circuit/${board.board}.glb`} breakdown={null} stale={false}
              focus={focus} onFocus={setFocus} />
          </div>
          <aside className={styles.sources}>
            <div>
              <div className={styles.sourcesTitle}>{board.title}</div>
              <div className={styles.dim}>{board.purpose}</div>
            </div>
            <ol className={own.blocks}>
              {board.blocks.map((b) => (
                <li key={b.name}>
                  <button onClick={() => setFocus(b.name === focus ? null : b.name)} className={b.name === focus ? own.active : ""}>
                    {b.name}
                  </button>
                  <span className={styles.dim}>{b.parts.length}</span>
                </li>
              ))}
            </ol>
            {block && (
              <table className={own.parts}>
                <tbody>
                  {block.parts.map((p) => (
                    <tr key={p.ref}><td>{p.ref}</td><td>{p.value}</td><td className={styles.dim}>{p.package}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className={styles.dim}>
              Design: <a href={board.source.url} target="_blank" rel="noopener noreferrer">{board.source.title}</a> by {board.source.author}, {board.source.licence}.
              Blocks are the sections of its schematic; parts are KiCad&apos;s 3D library models.
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
