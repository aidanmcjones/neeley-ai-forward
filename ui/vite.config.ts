import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" so dist/ opens from any static server or sub-path.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5173, strictPort: false },
  build: { outDir: "dist", sourcemap: false, chunkSizeWarningLimit: 1200 },
});
