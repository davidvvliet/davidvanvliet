import { Metadata } from "next";
import { notFound } from "next/navigation";
import ModelsDashboard from "./ModelsDashboard";

export const metadata: Metadata = {
  title: "Probe models",
  robots: { index: false, follow: false },
};

// Dev-only: watches the Blender harness in scripts/blender (see its README).
export default function ModelsPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <ModelsDashboard />;
}
