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
      { slug: "pillars-of-creation", title: "Pillars of Creation", url: "https://esahubble.org/images/opo9544a/",
        credit: "Jeff Hester and Paul Scowen (Arizona State University), and NASA/ESA" },
      { slug: "sombrero-galaxy", title: "Sombrero Galaxy", url: "https://esahubble.org/images/opo0328a/",
        credit: "NASA/ESA and The Hubble Heritage Team (STScI/AURA)" },
      { slug: "ultra-deep-field", title: "Hubble Ultra Deep Field", url: "https://esahubble.org/images/heic0406a/",
        credit: "NASA, ESA, and S. Beckwith (STScI) and the HUDF Team" },
      { slug: "crab-nebula", title: "Crab Nebula", url: "https://esahubble.org/images/heic0515a/",
        credit: "NASA, ESA and Allison Loll/Jeff Hester (Arizona State University). Acknowledgement: Davide De Martin (ESA/Hubble)" },
      { slug: "extreme-deep-field", title: "Hubble eXtreme Deep Field", url: "https://esahubble.org/images/heic1214a/",
        credit: "NASA, ESA, G. Illingworth, D. Magee, and P. Oesch (University of California, Santa Cruz), R. Bouwens (Leiden University), and the HUDF09 Team" },
    ],
  },
};
