import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The blog became "writing"; keep old links working.
  async redirects() {
    return [
      { source: "/blog", destination: "/writing", permanent: true },
      { source: "/blog/:slug", destination: "/writing/:slug", permanent: true },
    ];
  },
  turbopack: {
    resolveAlias: {
      canvas: "./empty-module.ts",
    },
  },
};

export default nextConfig;
