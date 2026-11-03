import fs from "fs";
import path from "path";
import { Suspense } from "react";
import { Metadata } from "next";
import Circuits from "./Circuits";
import type { Board } from "../models/PublishedModels";
import { rocketFrom, type Spec } from "./finrocket/rocket";

export const metadata: Metadata = {
  title: "Circuits",
  robots: { index: false, follow: false },
};

// The boards: public/circuits/<board>.glb and .board.json, written by scripts/circuit/build.py --publish.
function boards(): Board[] {
  const dir = path.join(process.cwd(), "public", "circuits");
  try {
    return fs.readdirSync(dir).filter((f) => f.endsWith(".board.json")).sort()
      .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as Board)
      .map((b) => (b.drives === "finrocket" ? { ...b, finrocket: finrocket() } : b));
  } catch {
    return [];
  }
}

// The fin rocket a board drives ("drives": "finrocket"): from its spec and its motor's thrust curve.
function finrocket() {
  const dir = path.join(process.cwd(), "scripts", "blender");
  const spec = JSON.parse(fs.readFileSync(path.join(dir, "specs", "finrocket.json"), "utf8")) as Spec;
  const eng = fs.readFileSync(path.join(dir, "refs", "finrocket", "sources", "Estes_F15.eng"), "utf8");
  const { rocket, gains, rho } = rocketFrom(spec, eng);
  return { rocket, gains, rho };
}

export default function CircuitsPage() {
  return <Suspense><Circuits boards={boards()} /></Suspense>;
}
