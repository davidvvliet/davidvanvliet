"use client";

import Link from "next/link";
import styles from "./ViewPanel.module.css";

// A non-explore view in the left (or top, on phones) panel, with a way back.
export default function ViewPanel({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.panel}>
      <Link href="/" className={styles.back}>← explore</Link>
      <div className={styles.body}>{children}</div>
    </div>
  );
}
