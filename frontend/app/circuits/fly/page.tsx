import fs from "fs";
import path from "path";
import { Metadata } from "next";
import Fly from "./Fly";
import { rocketFrom, type Spec } from "./rocket";

export const metadata: Metadata = {
  title: "Fly the rocket",
  robots: { index: false, follow: false },
};

// /circuits/fly: the rocket-recorder board flying the fin-steered rocket. The rocket's numbers come
// from its spec (scripts/blender/specs/finrocket.json) and the motor's thrust curve beside it.
export default function FlyPage() {
  const dir = path.join(process.cwd(), "scripts", "blender");
  const spec = JSON.parse(fs.readFileSync(path.join(dir, "specs", "finrocket.json"), "utf8")) as Spec;
  const eng = fs.readFileSync(path.join(dir, "refs", "finrocket", "sources", "Estes_F15.eng"), "utf8");
  return <Fly {...rocketFrom(spec, eng)} />;
}
