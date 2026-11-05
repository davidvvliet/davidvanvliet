import Link from "next/link";
import Header from "./models/Header";
import models from "./models/models.module.css";

// Every missing page, including an unknown /writing post: the site header, then just "404".
export default function NotFound() {
  return (
    <div className={models.page}>
      <Header>
        <Link href="/" className={models.dim}>← explore</Link>
      </Header>
      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1rem" }}>
        404
      </main>
    </div>
  );
}
