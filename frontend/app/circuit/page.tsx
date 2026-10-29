import fs from "fs";
import path from "path";
import { Suspense } from "react";
import { Metadata } from "next";
import Circuit, { Board } from "./Circuit";

export const metadata: Metadata = {
  title: "Circuit",
  robots: { index: false, follow: false },
};

// The boards: public/circuit/<board>.json and .glb, written by scripts/circuit/build.py.
function boards(): Board[] {
  const dir = path.join(process.cwd(), "public", "circuit");
  try {
    return fs.readdirSync(dir).filter((f) => f.endsWith(".json")).sort()
      .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as Board);
  } catch {
    return [];
  }
}

export default function CircuitPage() {
  return <Suspense><Circuit boards={boards()} /></Suspense>;
}
