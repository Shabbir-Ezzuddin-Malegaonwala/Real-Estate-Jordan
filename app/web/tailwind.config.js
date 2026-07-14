/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Palette is CSS-variable driven so a single [data-theme] swap re-themes
        // the whole UI. Channels are space-separated RGB (see index.css) so
        // Tailwind's opacity modifiers (bg-accent/10, border-pos/40) keep working.
        base: "rgb(var(--c-base) / <alpha-value>)",
        surface: "rgb(var(--c-surface) / <alpha-value>)",
        panel: "rgb(var(--c-panel) / <alpha-value>)",
        raised: "rgb(var(--c-raised) / <alpha-value>)",
        line: "rgb(var(--c-line) / <alpha-value>)",
        "line-soft": "rgb(var(--c-line-soft) / <alpha-value>)",
        ink: "rgb(var(--c-ink) / <alpha-value>)",
        "ink-dim": "rgb(var(--c-ink-dim) / <alpha-value>)",
        "ink-mute": "rgb(var(--c-ink-mute) / <alpha-value>)",
        "ink-faint": "rgb(var(--c-ink-faint) / <alpha-value>)",
        accent: "rgb(var(--c-accent) / <alpha-value>)",
        "accent-dim": "rgb(var(--c-accent-dim) / <alpha-value>)",
        cyan: "rgb(var(--c-cyan) / <alpha-value>)",
        "cyan-dim": "rgb(var(--c-cyan-dim) / <alpha-value>)",
        pos: "rgb(var(--c-pos) / <alpha-value>)",
        neg: "rgb(var(--c-neg) / <alpha-value>)",
        warn: "rgb(var(--c-warn) / <alpha-value>)",
        // Stitch design-system tokens (white+blue, ≤2 accents) for the new
        // ui/ + ui/charts/ primitives — Demo-G visual reference. Namespaced
        // under `stitch` so it can't collide with the CSS-variable tokens
        // above (ink/line/warn already exist for the dark terminal theme).
        stitch: {
          brand: "#0072B2",
          "brand-dark": "#00598c",
          warn: "#D55E00",
          green: "#009E73",
          ink: "#1a1d1f",
          muted: "#5b636b",
          line: "#e7eaee",
          bg: "#eef1f5",
          card: "#ffffff",
          soft: "#f3f6f9",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
    },
  },
  plugins: [],
};
