// The photo grid (the small cell under the links) and /photos/<n>.
// Files live in public/photos: NN.webp (up to 1600px, no metadata), NN-thumb.webp
// (320px square), and NN.webm for a clip (NN.webp is then its poster).
export interface Photo {
  n: number;
  src: string;
  thumb: string;
  video?: string;
}

const CLIPS = new Set([16]);
const COUNT = 16;

export const PHOTOS: Photo[] = Array.from({ length: COUNT }, (_, i) => {
  const n = i + 1;
  const id = String(n).padStart(2, "0");
  return {
    n,
    src: `/photos/${id}.webp`,
    thumb: `/photos/${id}-thumb.webp`,
    ...(CLIPS.has(n) ? { video: `/photos/${id}.webm` } : {}),
  };
});

export function getPhoto(n: number): Photo | undefined {
  return PHOTOS[n - 1];
}
