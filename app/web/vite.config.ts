import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Load .env from the REPO ROOT (two levels up) so a single root .env controls
  // everything — the backend secrets AND the frontend's VITE_API_BASE. Only
  // VITE_-prefixed vars are ever exposed to the browser, so DATABASE_URL /
  // GROQ_API_KEY in that same file stay server-side and never reach the bundle.
  envDir: "../..",
  server: {
    port: 5173,
    host: true,
  },
  build: {
    target: "es2020",
    chunkSizeWarningLimit: 1200,
  },
});
