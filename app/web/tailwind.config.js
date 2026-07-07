/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Terminal surface ramp (near-black slate)
        base: "#0a0d12",
        surface: "#0f141c",
        panel: "#121824",
        raised: "#182130",
        line: "#1f2937",
        "line-soft": "#161d28",
        // Text ramp
        ink: "#d6deea",
        "ink-dim": "#9aa7b8",
        "ink-mute": "#6b7688",
        "ink-faint": "#4a5568",
        // Accents — amber is the single brand accent; steel-cyan is secondary
        accent: "#e6a94b",
        "accent-dim": "#a97d38",
        cyan: "#5fb2c9",
        "cyan-dim": "#3f7d8f",
        // Functional semantics (waterfall + risk only)
        pos: "#5fa47f",
        neg: "#c9736f",
        warn: "#d9a441",
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
