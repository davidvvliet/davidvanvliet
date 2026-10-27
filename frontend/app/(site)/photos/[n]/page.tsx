import { Metadata } from "next";
import { notFound } from "next/navigation";
import { PHOTOS, getPhoto } from "../../../photos";
import PhotoView from "../../../components/PhotoView";

type Props = { params: Promise<{ n: string }> };

export const dynamicParams = false;

export async function generateStaticParams() {
  return PHOTOS.map((p) => ({ n: String(p.n) }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { n } = await params;
  return { title: `Photo ${n}`, alternates: { canonical: `/photos/${n}` } };
}

export default async function PhotoPage({ params }: Props) {
  const { n } = await params;
  const num = Number(n);
  if (!getPhoto(num)) notFound();
  return <PhotoView n={num} />;
}
