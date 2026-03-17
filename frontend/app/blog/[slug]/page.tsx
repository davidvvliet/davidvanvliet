import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getPost, getAllPosts } from "../index";
import styles from "../blog.module.css";

type Props = { params: Promise<{ slug: string }> };

export async function generateStaticParams() {
  return getAllPosts().map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.content.slice(0, 160).replace(/\n/g, " "),
  };
}

export default async function BlogPostPage({ params }: Props) {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) notFound();

  return (
    <main className={styles.page}>
      <Link href="/blog" className={styles.back}>← blog</Link>
      <div className={styles.title}>{post.title}</div>
      <div className={styles.date}>{post.date}</div>
      <p className={styles.content}>{post.content}</p>
    </main>
  );
}
