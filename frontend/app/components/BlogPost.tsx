"use client";

import { usePageStore } from "../store/pageStore";
import { getPost } from "../blog";
import styles from "./BlogPost.module.css";

export default function BlogPost() {
  const slug = usePageStore((s) => s.blogPost);
  const post = getPost(slug);

  if (!post) return <div className={styles.blog}>Post not found.</div>;

  return (
    <div className={styles.blog}>
      <div className={styles.title}>{post.title}</div>
      <div className={styles.date}>{post.date}</div>
      <div className={styles.content}>{post.content}</div>
    </div>
  );
}
