// One entry from public/photos (see photos.ts). n is its 1-based position; slug is
// its URL (/photos/<slug>): the short name from photoCaptions.json, or n if it has none.
// width/height are the image's (a clip's still), when its format can be read;
// loc is where it was taken, [lat, lon] in degrees, from photoCaptions.json.
export interface Photo {
  n: number;
  slug: string;
  title?: string;
  caption?: string;
  image?: string;
  video?: string;
  width?: number;
  height?: number;
  loc?: [number, number];
}

// The location globe beside a photo (photoGlobe.ts): SVG path data in a
// -50..50 viewBox, the sphere's wireframe and the continent outlines.
export interface GlobePaths {
  grid: string;
  land: string;
}
