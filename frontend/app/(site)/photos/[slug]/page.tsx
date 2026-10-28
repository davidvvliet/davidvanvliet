import { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { getPhotos } from "../../../photos";
import PhotoView from "../../../components/PhotoView";

type Props = { params: Promise<{ slug: string }> };

export const dynamicParams = false;

// Each photo lives at its slug. A titled photo's old number URL (/photos/3)
// is built too and redirects to the slug, so earlier links keep working.
export async function generateStaticParams() {
  return getPhotos().flatMap((p) => (p.slug === String(p.n) ? [p.slug] : [p.slug, String(p.n)]).map((slug) => ({ slug })));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const photo = getPhotos().find((p) => p.slug === slug);
  if (!photo) return {};
  return { title: photo.title ?? `Photo ${photo.n}`, alternates: { canonical: `/photos/${photo.slug}` } };
}

export default async function PhotoPage({ params }: Props) {
  const { slug } = await params;
  const photos = getPhotos();
  const i = photos.findIndex((p) => p.slug === slug);
  if (i < 0) {
    const byNumber = photos[Number(slug) - 1];
    if (/^\d+$/.test(slug) && byNumber) permanentRedirect(`/photos/${byNumber.slug}`);
    notFound();
  }
  const prev = photos[(i - 1 + photos.length) % photos.length];
  const next = photos[(i + 1) % photos.length];
  return <PhotoView photo={photos[i]} count={photos.length} prevSlug={prev.slug} nextSlug={next.slug} />;
}
