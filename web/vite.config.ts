import { defineConfig } from "vite";
import { resolve } from "node:path";

/**
 * Multi-entry build: every interactive page gets its own TS entry.
 * Hashed output lands in app/static/dist/ and is loaded by base.html via
 * the Vite manifest — no runtime stat() calls for cache-busting.
 */
export default defineConfig({
  root: resolve(__dirname),
  resolve: {
    alias: { "@": resolve(__dirname, "src") },
  },
  build: {
    outDir: resolve(__dirname, "..", "app", "static", "dist"),
    emptyOutDir: true,
    manifest: "manifest.json",
    assetsInlineLimit: 0,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "src", "main.ts"),
        styles: resolve(__dirname, "src", "styles", "main.css"),
        index: resolve(__dirname, "src", "pages", "index.ts"),
        driver: resolve(__dirname, "src", "pages", "driver.ts"),
        headToHead: resolve(__dirname, "src", "pages", "headToHead.ts"),
        createChampionship: resolve(__dirname, "src", "pages", "createChampionship.ts"),
        driverPositions: resolve(__dirname, "src", "pages", "driverPositions.ts"),
        championship: resolve(__dirname, "src", "pages", "championship.ts"),
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
