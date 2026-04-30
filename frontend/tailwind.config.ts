import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "bg-base": "#0A0A0F",
        "bg-surface": "#111118",
        "bg-elevated": "#1A1A24",
        "bg-subtle": "#22222E",
        border: "#2A2A38",
        "border-strong": "#3A3A50",
        "text-primary": "#F0F0FF",
        "text-secondary": "#8888AA",
        "text-muted": "#55556A",
        "accent-blue": "#4F8EF7",
        "accent-blue-dim": "#1A3A6A",
        "accent-green": "#34D399",
        "accent-green-dim": "#0D3D2A",
        "accent-amber": "#FBBF24",
        "accent-amber-dim": "#3D2E0A",
        "accent-red": "#F87171",
        "accent-red-dim": "#3D1010",
        "accent-purple": "#A78BFA",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
