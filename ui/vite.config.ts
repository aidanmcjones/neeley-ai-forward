import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { memosIndex } from "./vite.memos-index.js";

// base "./" so dist/ opens from any static server or sub-path. memosIndex() serves / emits
// data/memos_index.json so the chat's chips paint before the full memos.json arrives.
export default defineConfig({
  base: "./",
  plugins: [react(), memosIndex()],
  server: { port: 5173, strictPort: false },
  build: { outDir: "dist", sourcemap: false, chunkSizeWarningLimit: 1200 },
});
