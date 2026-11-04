import Link from "next/link";
import styles from "./models.module.css";

// Links on the left, the name centred in the home page's title style (/models, /circuits, /thinkers).
// Its own file so pages without the 3D viewer can use it without loading three.js.
export default function Header({ children }: { children: React.ReactNode }) {
  return (
    <header className={styles.siteHeader}>
      <nav className={styles.siteLinks}>{children}</nav>
      <Link href="/" className={styles.siteName}>David van Vliet</Link>
    </header>
  );
}
