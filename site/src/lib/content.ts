import { getCollection } from "astro:content";

// Drafts show while developing (`npm run dev`) and are left out of a real
// build, so nothing marked `draft: true` can be published by accident.
// Set SHOW_DRAFTS=1 to include them in a build anyway, e.g. for a preview.
const showDrafts = import.meta.env.DEV || process.env.SHOW_DRAFTS === "1";

export async function getLessons() {
  const all = await getCollection("course", ({ data }) => showDrafts || !data.draft);
  return all.sort((a, b) => a.data.lesson - b.data.lesson);
}
