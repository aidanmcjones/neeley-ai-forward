import type { Config } from "tailwindcss";

// Every color is a CSS variable (RGB channels) defined in src/index.css,
// so light/dark themes swap at runtime and Tailwind opacity modifiers work.
const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const tokens = [
  "purple", "purple-deep", "purple-bright", "frog-grey",
  "teal", "teal-soft", "good", "warn", "bad",
  "bg", "fg", "muted", "line", "surface", "surface-2", "chip",
] as const;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["variant", [
    "@media (prefers-color-scheme: dark) { :root:not([data-theme=\"light\"]) & }",
    ":root[data-theme=\"dark\"] &",
  ]],
  theme: {
    extend: {
      colors: Object.fromEntries(tokens.map((t) => [t, v(t)])),
      fontFamily: {
        display: ["\"Bebas Neue\"", "Impact", "sans-serif"],
        body: ["Montserrat", "system-ui", "sans-serif"],
        mono: ["\"JetBrains Mono\"", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgb(var(--fg) / 0.06), 0 1px 1px rgb(var(--fg) / 0.04)",
        drawer: "-8px 0 24px rgb(var(--fg) / 0.18)",
      },
    },
  },
  plugins: [],
} satisfies Config;
