import { register } from "../registry";

const responses: Record<string, { description: string; output: string[]; hidden?: boolean }> = {
  about: {
    description: "About this site",
    output: ["David van Vliet's personal site."],
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
