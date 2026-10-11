import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";
import { docsSchema } from "@astrojs/starlight/schema";

// Starlight reads one collection called "docs". Ours comes from
// ../content/course/ instead of Starlight's default src/content/docs/, and
// every id gets a "course/" prefix so lessons live at /course/<file-name>/.
// Only numbered lesson files count: README.md and _TEMPLATE.md are skipped.
export const collections = {
  docs: defineCollection({
    loader: glob({
      pattern: "[0-9][0-9]-*.{md,mdx}",
      base: "../content/course",
      generateId: ({ entry }) => `course/${entry.replace(/\.mdx?$/, "")}`,
    }),
    // The lesson fields are optional only because Starlight checks custom
    // pages (like the home page) against this same schema. Every lesson sets them.
    schema: docsSchema({
      extend: z
        .object({
          pubDate: z.coerce.date(),
          lesson: z.number(),
          phase: z.number(),
          tags: z.array(z.string()),
          ticket: z.string(),
        })
        .partial(),
    }),
  }),
};
