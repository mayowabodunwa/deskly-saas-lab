import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

// Only numbered lesson files count: README.md and _TEMPLATE.md are skipped.
const course = defineCollection({
  loader: glob({ pattern: "[0-9][0-9]-*.{md,mdx}", base: "../content/course" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    lesson: z.number(),
    phase: z.number(),
    tags: z.array(z.string()).default([]),
    ticket: z.string(),
    draft: z.boolean().default(true),
  }),
});

export const collections = { course };
