// next.config.js
// Next.js configuration for Nocos frontend.
// Enables strict mode for catching potential issues early and
// configures image domains for GitHub avatars.

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  images: {
    // Allow GitHub avatar images to be served via Next.js Image component.
    // This enables automatic optimisation and lazy loading for project avatars.
    remotePatterns: [
      {
        protocol: "https",
        hostname: "avatars.githubusercontent.com",
      },
      {
        protocol: "https",
        hostname: "github.com",
      },
    ],
  },
};

module.exports = nextConfig;
