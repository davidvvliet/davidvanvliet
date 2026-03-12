import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: "https://davidvvliet.com/sitemap.xml",
    host: "https://davidvvliet.com",
  };
}
