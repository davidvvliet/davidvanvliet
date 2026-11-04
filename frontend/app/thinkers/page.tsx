import fs from "fs";
import path from "path";
import { Metadata } from "next";
import styles from "./thinkers.module.css";

export const metadata: Metadata = { title: "Thinkers" };

// Portraits as plain text, made by scripts/ascii/portrait.py (commands at the top of that file).
const THINKERS = [
  { name: "Isaac Newton", file: "newton.txt" },
  { name: "Charles Darwin", file: "darwin.txt" },
];

function art(file: string) {
  return fs.readFileSync(path.join(process.cwd(), "app", "thinkers", file), "utf8");
}

export default function ThinkersPage() {
  return (
    <main className={styles.page}>
      {THINKERS.map((t) => (
        <figure key={t.file} className={styles.thinker}>
          <pre className={styles.art} aria-label={`${t.name}, in ASCII`}>{art(t.file)}</pre>
          <figcaption className={styles.name}>{t.name}</figcaption>
        </figure>
      ))}
    </main>
  );
}
