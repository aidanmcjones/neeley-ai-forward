import { defineConfig } from "vite";
import { resolve } from "node:path";

// The Part 2 add-on: one self-contained script dropped next to Parker's bundle on his artifact
// (see ui/addon/part2/README.md). Built to ui/dist/assets/part2-addon.js with a stable name so the one
// <script> line in his index.html never changes.
//   cd ui && npx vite build --config addon/part2/vite.config.ts
export default defineConfig({
  root: resolve(__dirname),
  build: {
    outDir: resolve(__dirname, "../../dist/assets"),
    emptyOutDir: false,
    sourcemap: false,
    minify: true,
    lib: { entry: resolve(__dirname, "main.ts"), name: "NeedlePart2", formats: ["iife"], fileName: () => "part2-addon.js" },
    rollupOptions: { output: { inlineDynamicImports: true } },
  },
});
