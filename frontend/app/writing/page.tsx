import { Metadata } from "next";
import Link from "next/link";
import { getAllPosts } from "./index";
import styles from "./writing.module.css";
import BackArrow from "../components/BackArrow";

export const metadata: Metadata = {
  title: "Writing",
  description: "Writing by David van Vliet.",
};

export default function WritingPage() {
  const posts = getAllPosts();
  const maxTitle = posts.length ? Math.max(...posts.map((p) => p.title.length)) : 0;

  return (
    <main className={styles.page}>
      <Link href="/" className={styles.back}><BackArrow />davidvvliet.com</Link>
      <div className={styles.title}>Writing</div>
      {posts.length === 0 ? (
        <div>Nothing here yet.</div>
      ) : (
        posts.map((post) => (
          <Link key={post.slug} href={`/writing/${post.slug}`} className={styles.postLink}>
            {post.title.padEnd(maxTitle)}{"    "}<span className={styles.postDate}>{post.date}</span>
          </Link>
        ))
      )}
    </main>
  );
}
