// Famous photos a vehicle took, shown in a column in the bottom left of its detailed view (the
// first at the bottom). Thumbnails are public/models/photos/<probe>/<slug>-thumb.jpg, square crops
// of each picture as first released (STScI's own release files, archived on the Wayback Machine;
// not later reprocessings). STScI's usage terms (hubblesite.org/copyright, 2006): "no claim to
// copyright is being asserted by STScI and it may be freely used as in the public domain in
// accordance with NASA's contract. However, it is requested that in any subsequent use of this work
// NASA and STScI be given appropriate acknowledgement." Each credit is the one on its release.
export type Photo = { slug: string; title: string; release: string; credit: string; url: string };

const W = "https://web.archive.org/web/";

export const PHOTOS: Record<string, Photo[]> = {
  hubble: [
    { slug: "deep-field", title: "Hubble Deep Field", release: "STScI-PRC96-01a, January 15, 1996",
      credit: "R. Williams and the HDF Team (ST ScI) and NASA", url: "https://esahubble.org/images/opo9601a/" },
    { slug: "pillars-of-creation", title: "Pillars of Creation (M16)", release: "STScI-PRC95-44a, November 2, 1995",
      credit: "Jeff Hester and Paul Scowen (Arizona State University), and NASA", url: `${W}19980223090710im_/http://oposite.stsci.edu/pubinfo/jpeg/M16Full.jpg` },
    { slug: "ultra-deep-field", title: "Hubble Ultra Deep Field", release: "STScI-PRC2004-07a, March 9, 2004",
      credit: "NASA, ESA, S. Beckwith (STScI) and the HUDF Team", url: `${W}2006im_/http://imgsrc.hubblesite.org/hu/db/2004/07/images/a/formats/large_web.jpg` },
    { slug: "sombrero-galaxy", title: "Sombrero Galaxy (M104)", release: "STScI-PRC2003-28a, October 2003",
      credit: "NASA and The Hubble Heritage Team (STScI/AURA)", url: `${W}2007im_/http://imgsrc.hubblesite.org/hu/db/2003/28/images/a/formats/large_web.jpg` },
    { slug: "crab-nebula", title: "Crab Nebula (M1)", release: "STScI-PRC2005-37a, December 1, 2005",
      credit: "NASA, ESA, J. Hester and A. Loll (Arizona State University)", url: `${W}2007im_/http://imgsrc.hubblesite.org/hu/db/2005/37/images/a/formats/large_web.jpg` },
    { slug: "extreme-deep-field", title: "Hubble eXtreme Deep Field", release: "STScI-PRC2012-37a, September 25, 2012",
      credit: "NASA, ESA, G. Illingworth, D. Magee, and P. Oesch (University of California, Santa Cruz), R. Bouwens (Leiden University), and the HUDF09 Team",
      url: `${W}2014im_/http://imgsrc.hubblesite.org/hu/db/images/hs-2012-37-a-full_jpg.jpg` },
    { slug: "mystic-mountain", title: "Mystic Mountain (Carina Nebula)", release: "STScI-PRC2010-13a, April 22, 2010",
      credit: "NASA, ESA, and M. Livio and the Hubble 20th Anniversary Team (STScI)", url: `${W}2014im_/http://imgsrc.hubblesite.org/hu/db/images/hs-2010-13-a-large_web.jpg` },
    { slug: "cats-eye-nebula", title: "Cat's Eye Nebula (NGC 6543)", release: "STScI-PRC2004-27a, September 9, 2004",
      credit: "NASA, ESA, HEIC, and The Hubble Heritage Team (STScI/AURA)", url: `${W}2007im_/http://imgsrc.hubblesite.org/hu/db/2004/27/images/a/formats/full_jpg.jpg` },
    { slug: "whirlpool-galaxy", title: "Whirlpool Galaxy (M51)", release: "STScI-PRC2005-12a, April 25, 2005",
      credit: "NASA, ESA, S. Beckwith (STScI), and The Hubble Heritage Team (STScI/AURA)", url: `${W}2008im_/http://imgsrc.hubblesite.org/hu/db/2005/12/images/a/formats/large_web.jpg` },
    { slug: "shoemaker-levy-9", title: "Comet Shoemaker-Levy 9 impact sites on Jupiter", release: "STScI-PRC94-33, July 21, 1994",
      credit: "H. Hammel, MIT and NASA", url: `${W}19990219081515im_/http://oposite.stsci.edu/pubinfo/comet/gif/HST_Gc.gif` },
    { slug: "first-light", title: "Hubble's first light", release: "STScI-PRC90-04, May 20, 1990",
      credit: "NASA", url: `${W}2007im_/http://imgsrc.hubblesite.org/hu/db/1990/04/images/a/formats/full_jpg.jpg` },
    { slug: "m100-mirror-fix", title: "M100 before and after the mirror fix", release: "STScI-PR94-01, January 13, 1994",
      credit: "NASA (no credit line on the release)", url: `${W}19981202094214im_/http://oposite.stsci.edu/pubinfo/gif/WFPCM100Comp2.gif` },
  ],
};
