// One entry from public/photos (see photos.ts). n is its 1-based position; slug is
// its URL (/photos/<slug>): the short name from photoCaptions.json, or n if it has none.
export interface Photo {
  n: number;
  slug: string;
  title?: string;
  caption?: string;
  image?: string;
  video?: string;
}
