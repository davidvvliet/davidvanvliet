import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPost, getAllPosts } from "../../../writing";
import BlogPost from "../../../components/BlogPost";

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
    alternates: { canonical: `/writing/${post.slug}` },
  };
}

export default async function WritingPostPage({ params }: Props) {
  const { slug } = await params;
  if (!getPost(slug)) notFound();
  return <BlogPost slug={slug} />;
}
