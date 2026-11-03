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
  metadataBase: new URL("https://www.davidvvliet.com"),
  title: {
    default: "David van Vliet",
    template: "%s | David van Vliet",
  },
  description:
    "David van Vliet's personal website",
  keywords: [
    "David van Vliet",
    "David van Vliet New York",
    "David van Vliet Radar",
    "David van Vliet yAI",
    "davidv.nl",
    "davidvvliet.com",
  ],
  authors: [{ name: "David van Vliet", url: "https://www.davidvvliet.com" }],
  creator: "David van Vliet",
  alternates: {
    canonical: "https://www.davidvvliet.com",
  },
  openGraph: {
    type: "website",
    url: "https://www.davidvvliet.com",
    title: "David van Vliet",
    description:
      "David van Vliet's personal website",
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
      "David van Vliet's personal website",
    images: ["/og-image.png"],
  },
  icons: {
    icon: "/voyager1plate.png",
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
  url: "https://www.davidvvliet.com",
  sameAs: [
    "https://davidv.nl",
    "https://github.com/davidvvliet",
    "https://www.linkedin.com/in/davidvvliet/",
    "https://x.com/deepfieldnorth",
  ],
  address: {
    "@type": "PostalAddress",
    addressLocality: "New York",
    addressRegion: "NY",
    addressCountry: "US",
  },
  email: "axeldvvliet@gmail.com",
  description:
    "David van Vliet is based in New York City. He built Radar and yAI.",
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
