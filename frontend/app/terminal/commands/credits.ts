import { Command } from "../types";
import { register } from "../registry";
// Written by `npm run model:approve`: the credit lines of each published model's sources.
import modelCredits from "./model-credits.json";

const credits: Command = {
  name: "credits",
  description: "The shoulders of the giants I stand on",
  execute: () => [
    "__SMALL__JPL Horizons, spacecraft and planet ephemerides: https://ssd.jpl.nasa.gov/horizons/",
    "__SMALL__VSOP87 (Bretagnon & Francou), the position of Mars",
    "__SMALL__Allen, Astrophysical Quantities, via SolarSoft (D. Alexander), solar limb darkening",
    "__SMALL__NASA, JPL and USGS, mission and surface imagery; NASA/JPL-Caltech, Perseverance landing video; NASA, Apollo 11 landing loop",
    "__SMALL__Apollo Image Archive (ASU), Apollo 17 orbit state vectors: https://apollo.sese.asu.edu/",
    "__SMALL__NASA mission reports MSC-00171, MSC-02680 and JSC-07904, Apollo 11, 13 and 17 burn and entry conditions",
    "__SMALL__Apollo Flight Journal and Apollo Lunar Surface Journal, transcripts: https://www.apollojournals.org/",
    "__SMALL__John D. Anderson (JPL), Mariner 2 trajectory reconstruction, via Horizons",
    "__SMALL__JPL Technical Report 32-740, Mariner 4 injection and encounter conditions",
    "__SMALL__Hibberd, Hein and Eubanks (2020) and Hibberd, Hein, Eubanks and Kennedy (2022), Project Lyra mission designs: https://arxiv.org/abs/1902.04935 and https://arxiv.org/abs/2201.04240",
    "__SMALL__Solar System Scope, Earth day map (CC BY 4.0), the Earth on the Aether launch page: https://www.solarsystemscope.com/textures/",
    "__SMALL__NASA/Goddard Space Flight Center Scientific Visualization Studio, clouds of the Earth on the Aether launch page: https://svs.gsfc.nasa.gov/3615/",
    "__SMALL__NASA's Scientific Visualization Studio, CGI Moon Kit (LRO LROC colour, LOLA elevation), the Moon on the Aether launch page: https://svs.gsfc.nasa.gov/4720/",
    "__SMALL__Solar System Scope, planet and ring textures: https://www.solarsystemscope.com/textures/",
    "__SMALL__Björn Jónsson, planetary maps: https://bjj.mmedia.is/data/planetary_maps.html",
    "__SMALL__Thewritestuff92, Polaroid's 1960-1991 logo (CC BY-SA 4.0, letters filled light), on the models page: https://commons.wikimedia.org/wiki/File:Polaroid-1960.svg",
    ...[...new Set(Object.values(modelCredits as Record<string, string[]>).flat())].map((c) => `__SMALL__${c}`),
  ],
};

register(credits);
