import { register } from "../registry";

const responses: Record<string, { description: string; output: string[]; hidden?: boolean }> = {
  about: {
    description: "About this site",
    output: [
      "This is my personal website, where you can find many of my interests displayed.", 
      "I'm Based in Palo Alto, building Radar Corp.",
      "We make software for private and public market investors to facilitate optimal capital flow.",
    ],
  },
  test: {
    description: "Test command",
    output: ["Hi!"],
    hidden: true,
  },
};

for (const [name, { description, output, hidden }] of Object.entries(responses)) {
  register({
    name,
    description,
    hidden,
    execute: () => output,
  });
}
