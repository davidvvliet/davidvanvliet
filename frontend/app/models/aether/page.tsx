import { Metadata } from "next";
import AetherLaunch from "./AetherLaunch";

export const metadata: Metadata = {
  title: "Altair Aether",
  robots: { index: false, follow: false },
};

// Altair Aether's launch, unlisted: the mass-driver shot, the coast, the insertion burn and the
// wings unfolding. The numbers are the spec's (scripts/blender/specs/aether.json).
export default function Page() {
  return <AetherLaunch />;
}
