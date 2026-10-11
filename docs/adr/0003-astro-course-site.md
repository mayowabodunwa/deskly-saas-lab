# ADR-0003 — One Astro site, inside the repo, for the course and articles

- **Status:** Accepted, amended twice on 2026-10-09 (Articles removed; moved to Starlight; see the end)
- **Date:** 2026-10-07
- **Phase:** cross-cutting (course publishing)

## Context

Each Deskly phase becomes a published lesson, and the owner also wants a place
for standalone articles. The course should be **interactive**: readers hide
the answer while they diagnose, check themselves with quick questions, tick off
steps, and copy commands without retyping them.

Lessons were already being written as Markdown with generator-neutral YAML
frontmatter in `content/course/`.

Constraints: free to host, no Node installed on the host Mac (ADR-0001), and
the owner's own typing time should stay on Deskly rather than on web tooling.

## Decision

We will build **one Astro site** in `site/` inside this repo, with two
sections: **Course** (`content/course/NN-*.mdx`) and **Articles**
(`content/articles/*.md`). Interactivity comes from three small components
(`Reveal`, `Quiz`, `Checklist`) used inside MDX lessons, plus a copy button
on every code block and per-lesson completion stored in the reader's browser.

The writing stays in `content/` and the site reads it from there. The site
runs in Docker under a Compose **profile**, so `make up` doesn't start it;
`make site` does.

## Consequences

**Good**

- One tool, one design, one build for both sections. The output is plain
  static files, so it can be hosted for free (GitHub Pages, Netlify, Cloudflare).
- Lessons stay readable as Markdown on GitHub. Interactive pieces are a few
  tags; everything else is ordinary text.
- `draft: true` content shows in development and is left out of real builds, so
  nothing publishes by accident.

**Bad**

- MDX is stricter than Markdown: a stray `{` or `<` in prose breaks the build,
  and HTML comments aren't allowed.
- On GitHub, the component tags (`<Quiz …>`) appear as raw text inside the
  lesson.
- Progress lives in each reader's browser. There are no accounts, so it doesn't
  follow a reader between devices.
- Astro 7 made a new Markdown engine (Sätteri) the default. Our link-rewriting
  plugin needs the older remark engine, installed explicitly as
  `@astrojs/markdown-remark`.

**Risks to watch**

- Links to `docs/` point at the GitHub repo, which is **private**. Readers will
  hit 404s until the repo is public, or those notes are published too.
- Moving the website to its own repo later means moving `content/` with it.

## Alternatives considered

| Option | Why not |
|---|---|
| Separate tools: a static generator for articles, a course platform for lessons | Two things to learn and maintain, two designs, readers bouncing between sites. Hosted course platforms (Teachable, Thinkific) cost money each month and hold the content. |
| Astro Starlight (ready-made docs theme) | Strong for documentation, but it owns the routing and look. A plain Astro site with a few components was simpler to explain and shape around the break-it lesson format. |
| Hugo | Fast and a single program, but its templating is harder for a beginner, and adding interactive components is clumsier. |
| In-browser terminals (real Docker per reader) | Needs paid servers per reader. The course deliberately has readers run the real system on their own machine. |
| The site in its own repo | Considered and offered. The owner chose a folder inside Deskly so lessons and code stay together. |

## Amendment — 2026-10-09: Articles section removed

The Articles section came from a misreading. "A static generator for both
articles and the course" was taken to mean a second kind of writing (blog
posts). The owner meant the per-phase articles, which *are* the course
lessons. With no articles planned, the section and `content/articles/` were
removed, and the site now serves the course only.

Publishing the engineering notes from `docs/` in that slot was offered,
because it would fix the lesson links that 404 against the private repo. It was
declined: the notes stay private working documents. **Those links still 404 for
other readers** until the repo is public or the links change.

The rest of this decision stands.

## Amendment — 2026-10-09: moved onto Starlight

The owner asked for the site to follow standard course-site practice. Most of
that (a lesson sidebar, "On this page" headings, search, a light/dark switch,
callouts, a phone layout) is exactly what **Starlight**, Astro's official
documentation theme, ships with and maintains. Building it by hand would mean
maintaining it by hand. That reverses the "plain Astro" choice in the
alternatives table above, which was right for a three-page site and wrong for
a real course.

What changed: Starlight owns routing and layout. Lessons load from
`../content/course/` into Starlight's `docs` collection with a `course/` id
prefix. Our components (Reveal, Quiz, Checklist, LessonComplete) carried over
unchanged, restyled with Starlight's theme variables. Search is built by
Pagefind at build time, so it doesn't work in the dev server.

Added at the same time: the **ticket simulator**, a practice ticket where the
reader chooses checks against a clock and sees real captured outputs. It's the
course's signature interactive piece, aimed at exactly the skill the course
teaches.

Costs: Starlight's look is "documentation" unless customised, and it has its
own conventions to learn. Two needed workarounds: the sidebar's
`autogenerate.directory` must be the lessons' real path (`../content/course`),
and the lesson-only frontmatter fields are optional in the schema, because
Starlight validates the custom home page against it too.
