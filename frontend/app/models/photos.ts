// Famous photos a vehicle took, shown in a column in the bottom left of its detailed view
// (the first at the bottom). Files are public/models/photos/<probe>/<slug>.jpg and <slug>-thumb.jpg.
// ESA/Hubble's images are CC BY 4.0 (esahubble.org/copyright: "released under the Creative Commons
// Attribution 4.0 International license ... provided they are clearly and visibly credited");
// each credit is the one on its image page. The Deep Field is STScI's 1996 release (PRC96-01).
export type Photo = { slug: string; title: string; credit: string; url: string };

const CC_BY = "CC BY 4.0";

export const PHOTOS: Record<string, { licence: string; photos: Photo[] }> = {
  hubble: {
    licence: CC_BY,
    photos: [
      { slug: "deep-field", title: "Hubble Deep Field", url: "https://esahubble.org/images/opo9601a/",
        credit: "Robert Williams and the Hubble Deep Field Team (STScI) and NASA/ESA" },
    ],
  },
};
