// The photo grid (the small cell under the links) and /photos/<n>.
// Order is this list; n is the position (1-based). Files in public/photos are
// named by a hash of their contents, so reordering or removing a photo never
// gives an old name to a different picture (browsers cache by name).
// src: up to 1600px WebP, no metadata (a clip's poster); thumb: 320px square;
// video: the clip; thumbVideo: 160px square loop for the grid.
export interface Photo {
  n: number;
  src: string;
  thumb: string;
  video?: string;
  thumbVideo?: string;
}

const FILES: Omit<Photo, "n">[] = [
  { src: "/photos/191ef86c16.webp", thumb: "/photos/c4ad512808-thumb.webp" },
  { src: "/photos/15a876cb12.webp", thumb: "/photos/8eba32ed75-thumb.webp" },
  { src: "/photos/972afd02ab.webp", thumb: "/photos/afd2f54a82-thumb.webp" },
  { src: "/photos/70b87cc5cd.webp", thumb: "/photos/d47d9d2dfa-thumb.webp" },
  { src: "/photos/81970a185b.webp", thumb: "/photos/a3268b4e0c-thumb.webp" },
  { src: "/photos/51142308d1.webp", thumb: "/photos/85fa733d25-thumb.webp" },
  { src: "/photos/2f729e00b3.webp", thumb: "/photos/406539905e-thumb.webp" },
  { src: "/photos/e3d5f16745.webp", thumb: "/photos/a44576f638-thumb.webp" },
  { src: "/photos/5a166849b8.webp", thumb: "/photos/24bc65f12c-thumb.webp" },
  { src: "/photos/53d876a4dd.webp", thumb: "/photos/7b8fb24c97-thumb.webp" },
  { src: "/photos/c839ef29f1.webp", thumb: "/photos/16bee2ac31-thumb.webp" },
  { src: "/photos/b45546acac.webp", thumb: "/photos/8d27060b46-thumb.webp" },
  { src: "/photos/9805dac472.webp", thumb: "/photos/4108d9cb7a-thumb.webp" },
  { src: "/photos/0343a7ce01.webp", thumb: "/photos/65b62e238b-thumb.webp" },
  { src: "/photos/859d88a4b3.webp", thumb: "/photos/1f5ebedf42-thumb.webp" },
  { src: "/photos/7c233b0ec9.webp", thumb: "/photos/e1c8d69fe3-thumb.webp", video: "/photos/0a8a9d0b85.webm", thumbVideo: "/photos/026ffa1e4e-thumb.webm" },
];

export const PHOTOS: Photo[] = FILES.map((f, i) => ({ n: i + 1, ...f }));

export function getPhoto(n: number): Photo | undefined {
  return Number.isInteger(n) ? PHOTOS[n - 1] : undefined;
}
