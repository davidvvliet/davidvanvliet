import { Metadata } from "next";
import Link from "next/link";
import { getAllPosts } from "./index";
import styles from "./blog.module.css";

export const metadata: Metadata = {
  title: "Blog",
  description: "Writing by David van Vliet.",
};

export default function BlogPage() {
  const posts = getAllPosts();
  const maxTitle = posts.length ? Math.max(...posts.map((p) => p.title.length)) : 0;

  return (
    <main className={styles.page}>
      <Link href="/" className={styles.back}>← davidvvliet.com</Link>
      <div className={styles.title}>Blog</div>
      {posts.length === 0 ? (
        <div>No blog posts yet.</div>
      ) : (
        posts.map((post) => (
          <Link key={post.slug} href={`/blog/${post.slug}`} className={styles.postLink}>
            {post.title.padEnd(maxTitle)}{"    "}<span className={styles.postDate}>{post.date}</span>
          </Link>
        ))
      )}
    </main>
  );
}
