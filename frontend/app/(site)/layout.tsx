import SiteShell from "../components/SiteShell";

// The home grid (scene, terminal, links, chess) stays mounted across these
// routes; the URL picks what the left panel shows.
export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return <SiteShell>{children}</SiteShell>;
}
