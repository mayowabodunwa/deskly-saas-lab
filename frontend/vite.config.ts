import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy /api to the backend so the SPA calls same-origin (no CORS).
// Inside docker the backend is reachable as "backend"; locally it's localhost.
const apiTarget = process.env.VITE_API_PROXY || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: { "/api": { target: apiTarget, changeOrigin: true } },
  },
});
