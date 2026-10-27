import SiteShell from "../components/SiteShell";
import { getPhotos } from "../photos";

// The home grid (scene, terminal, links, chess) stays mounted across these
// routes; the URL picks what the left panel shows.
export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return <SiteShell photos={getPhotos()}>{children}</SiteShell>;
}
