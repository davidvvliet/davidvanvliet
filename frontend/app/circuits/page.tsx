import fs from "fs";
import path from "path";
import { Suspense } from "react";
import { Metadata } from "next";
import Circuits from "./Circuits";
import type { Board } from "../models/PublishedModels";

export const metadata: Metadata = {
  title: "Circuits",
  robots: { index: false, follow: false },
};

// The boards: public/circuits/<board>.glb and .board.json, written by scripts/circuit/build.py --publish.
function boards(): Board[] {
  const dir = path.join(process.cwd(), "public", "circuits");
  try {
    return fs.readdirSync(dir).filter((f) => f.endsWith(".board.json")).sort()
      .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as Board);
  } catch {
    return [];
  }
}

export default function CircuitsPage() {
  return <Suspense><Circuits boards={boards()} /></Suspense>;
}
