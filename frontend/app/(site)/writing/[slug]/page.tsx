import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPost, getAllPosts } from "../../../writing";
import BlogPost from "../../../components/BlogPost";

type Props = { params: Promise<{ slug: string }> };

export async function generateStaticParams() {
  return getAllPosts().map((post) => ({ slug: post.slug }));
}

// A search and share preview of up to 160 characters that ends on a whole sentence, or on a
// whole word with an ellipsis when the first sentence is longer.
function preview(text: string, max = 160) {
  const flat = text.replace(/\s+/g, " ").trim();
  if (flat.length <= max) return flat;
  const cut = flat.slice(0, max);
  const end = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("? "), cut.lastIndexOf("! "));
  if (end > 40) return cut.slice(0, end + 1);
  return cut.slice(0, cut.lastIndexOf(" ")).replace(/[,;:]$/, "") + "…";
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return {};
  return {
    title: post.title,
    description: preview(post.content),
    alternates: { canonical: `/writing/${post.slug}` },
  };
}

export default async function WritingPostPage({ params }: Props) {
  const { slug } = await params;
  if (!getPost(slug)) notFound();
  return <BlogPost slug={slug} />;
}
