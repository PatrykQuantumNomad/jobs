// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

// https://astro.build/config
export default defineConfig({
  site: "https://patrykgolabek.github.io",
  base: "/jobs",
  trailingSlash: "always",
  vite: {
    plugins: [tailwindcss()],
  },
});
