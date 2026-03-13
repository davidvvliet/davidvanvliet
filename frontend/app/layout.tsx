import type { Metadata } from "next";
import { Roboto_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const robotoMono = Roboto_Mono({
  variable: "--font-roboto-mono",
  subsets: ["latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://davidvvliet.com"),
  title: {
    default: "David van Vliet",
    template: "%s | David van Vliet",
  },
  description:
    "David van Vliet. Building Radar Corp, products for private and public market investors.",
  keywords: [
    "David van Vliet",
    "David van Vliet founder",
    "David van Vliet Palo Alto",
    "David van Vliet Radar Corp",
    "davidv.nl",
    "davidvvliet.com",
  ],
  authors: [{ name: "David van Vliet", url: "https://davidvvliet.com" }],
  creator: "David van Vliet",
  alternates: {
    canonical: "https://davidvvliet.com",
    languages: {
      "en-US": "https://davidvvliet.com",
      "nl-NL": "https://davidv.nl",
    },
  },
  openGraph: {
    type: "website",
    url: "https://davidvvliet.com",
    title: "David van Vliet",
    description:
      "David van Vliet, founder based in Palo Alto, California. Building Radar Corp, products for private and public market investors.",
    siteName: "David van Vliet",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "David van Vliet",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "David van Vliet",
    description:
      "David van Vliet, founder based in Palo Alto, California. Building Radar Corp.",
    images: ["/og-image.png"],
  },
  icons: {
    icon: "/voyager1large.png",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "Person",
  name: "David van Vliet",
  url: "https://davidvvliet.com",
  sameAs: [
    "https://davidv.nl",
    "https://github.com/davidvvliet",
    "https://www.linkedin.com/in/davidvvliet/",
    "https://x.com/deepfieldnorth",
  ],
  jobTitle: "Founder",
  worksFor: {
    "@type": "Organization",
    name: "Radar Corp",
    url: "https://theradarcorp.com",
  },
  address: {
    "@type": "PostalAddress",
    addressLocality: "Palo Alto",
    addressRegion: "CA",
    addressCountry: "US",
  },
  email: "david@theradarcorp.com",
  description:
    "David van Vliet is a 21-year-old founder based in Palo Alto, California, building Radar Corp, products for private and public market investors.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={`${robotoMono.variable} antialiased`}>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
