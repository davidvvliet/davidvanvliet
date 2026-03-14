import { register } from "../registry";

const projects: Record<string, { description: string; url: string }> = {
  radar: {
    description: "Open Radar",
    url: "https://tryradar.ai",
  },
  intrinsic: {
    description: "Open Intrinsic",
    url: "https://runintrinsic.com",
  },
};

for (const [name, { description, url }] of Object.entries(projects)) {
  register({
    name,
    description,
    execute: () => {
      window.open(url, "_blank");
      return [`Opening ${name}...`];
    },
  });
}
