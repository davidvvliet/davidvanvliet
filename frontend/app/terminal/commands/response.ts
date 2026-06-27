import { register } from "../registry";

const responses: Record<string, { description: string; output: string[]; hidden?: boolean }> = {
  about: {
    description: "About this site",
    output: [
      "This is my personal website, where you can find many of my interests displayed.", 
      "I'm based in NYC, building yAI.",
      "We build general agents that automate repetitive workflows in financial institutions.",
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
