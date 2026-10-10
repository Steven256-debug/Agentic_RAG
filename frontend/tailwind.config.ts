import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: {
          DEFAULT: "#0B3D2E", // Deep green
          light: "#125a44",
        },
        accent: {
          DEFAULT: "#F5B700", // Gold
          hover: "#d9a100",
        },
        sidebar: "var(--sidebar-bg)",
        card: "var(--card-bg)",
        border: "var(--border-color)",
      },
    },
  },
  plugins: [
    typography,
  ],
};
export default config;
