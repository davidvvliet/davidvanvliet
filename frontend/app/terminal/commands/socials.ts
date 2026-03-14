import { Command } from "../types";
import { register } from "../registry";

const links: Record<string, string> = {
  github: "https://github.com/davidvvliet",
  linkedin: "https://www.linkedin.com/in/davidvvliet/",
  X: "https://x.com/deepfieldnorth",
};

const socials: Command = {
  name: "socials",
  description: "Open my socials (github, linkedin, X)",
  execute: (args) => {
    const input = args[0]?.toLowerCase();

    if (!input) {
      return [
        "Usage: socials <platform>",
        `Available: ${Object.keys(links).join(", ")}`,
      ];
    }

    const key = Object.keys(links).find((k) => k.toLowerCase() === input);
    if (!key) {
      return [`Unknown platform: ${input}. Available: ${Object.keys(links).join(", ")}`];
    }

    window.open(links[key], "_blank");
    return [`Opening ${key}...`];
  },
};

register(socials);
