import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";
import { remarkLessonLinks } from "./src/lib/remark-lesson-links.mjs";

// Lessons live outside this folder, in ../content/course/, so they stay
// readable on GitHub as plain Markdown. Links between them are written as
// relative file links (e.g. "01-whose-data-is-this.mdx"); the remark plugin
// rewrites those into site URLs at build time.
export default defineConfig({
  integrations: [mdx()],
  markdown: {
    remarkPlugins: [remarkLessonLinks],
    shikiConfig: { themes: { light: "github-light", dark: "github-dark" } },
  },
});
