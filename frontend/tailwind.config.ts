// tailwind.config.ts
// Tailwind CSS configuration for Nocos.
// Extends default theme with project-specific fonts.
// All colors come from CSS variables in globals.css — not from Tailwind tokens —
// so dark mode works without needing Tailwind's dark: variant.

import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Plus Jakarta Sans for headers and brand elements
        jakarta: ['"Plus Jakarta Sans"', "sans-serif"],
        // Inter for body text, labels, buttons, inputs
        inter: ["Inter", "sans-serif"],
      },
      maxWidth: {
        // Content max-width from design system
        content: "1280px",
        // Detail page max-width
        detail: "720px",
      },
    },
  },
  plugins: [],
};

export default config;
