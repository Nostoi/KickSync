import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  root: resolve(__dirname, "src"),
  base: "/static/web_dist/",
  server: {
    port: 5173,
    host: "0.0.0.0"
  },
  build: {
    outDir: resolve(__dirname, "../web_dist"),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: resolve(__dirname, "src/main.js")
    }
  }
});
