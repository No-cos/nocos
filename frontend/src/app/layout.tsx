// layout.tsx
// Root layout for the Nocos Next.js application.
// Loads Google Fonts via the <head> and applies base CSS.
// Dark mode class is toggled on <html> by the useDarkMode hook — this is why
// all color values are CSS variables rather than Tailwind tokens.

import type { Metadata } from "next";
import "@/styles/globals.css";
import { ErrorBoundary } from "@/components/error-boundary";

export const metadata: Metadata = {
  title: "Nocos — Discover and Contribute to Open Source",
  description:
    "Non-code contributors can now discover and contribute to open source without technical hassle. Find design, documentation, research, and community tasks.",
  keywords: [
    "open source",
    "non-technical",
    "design",
    "documentation",
    "contribution",
    "GitHub",
  ],
  openGraph: {
    title: "Nocos — Discover and Contribute to Open Source",
    description:
      "Find curated non-code open source tasks. Built for designers, writers, researchers, and community managers.",
    url: "https://nocos.cc",
    siteName: "Nocos",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        {/* Google Fonts — preconnect for performance, then load fonts.
            Plus Jakarta Sans for headers, Inter for body/UI. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        {/* ErrorBoundary catches unexpected React render errors on any page
            and shows a friendly fallback instead of a blank screen. */}
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
