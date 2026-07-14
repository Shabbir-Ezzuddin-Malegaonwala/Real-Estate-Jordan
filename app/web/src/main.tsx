import ReactDOM from "react-dom/client";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "maplibre-gl/dist/maplibre-gl.css";
import "./index.css";
import App from "./App";
import { initDataSource } from "./lib/dataSource";

// Resolves real-vs-mock (and, if real, primes the area list) before the first
// render so every DataSource consumer's synchronous listAreas()/getBundle()
// call is correct from mount — no loading flicker, no stale-mock-forever bug.
initDataSource().finally(() => {
  ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
});
