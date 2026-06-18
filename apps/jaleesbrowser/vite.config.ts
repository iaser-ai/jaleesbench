import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// `base: "./"` keeps every asset reference relative, so the same build works under
// a project-path host (e.g. GitHub Pages `/jaleesbench/`) and a local dev server at
// `/` without hardcoding a prefix (spec §5.7).
export default defineConfig({
  base: "./",
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
  },
});
