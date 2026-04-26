import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: {
    "process.env": {},
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    lib: {
      entry: resolve(__dirname, "src/widget-entry.jsx"),
      name: "AIRepairEstimatorWidget",
      formats: ["iife"],
      fileName: () => "widget.js",
    },
    cssCodeSplit: false,
    emptyOutDir: true,
    outDir: "dist",
  },
});
