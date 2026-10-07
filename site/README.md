# Course website

The website for **Support Engineering by Building Systems**, built with
[Astro](https://docs.astro.build/). It has two sections:

| Section | Reads from | What's there |
|---|---|---|
| **Course** | `../content/course/NN-*.mdx` | Lessons, in order, with interactive parts |
| **Articles** | `../content/articles/*.md` | Standalone articles |

The writing lives in `content/`, outside this folder, so it stays readable on
GitHub. This folder is only the machinery that turns it into web pages.

## Run it

```bash
make site
```

Then open <http://localhost:4321>. Edit a lesson and the page reloads by
itself. Like the rest of Deskly, it runs in Docker, so nothing is installed on
your Mac. It doesn't start with `make up`: the site isn't part of the app.

## Drafts

`draft: true` lessons and articles **show** while running `make site`, with a
"Draft" badge, and are **left out** of a real build. So nothing can be
published by accident. To include drafts in a build (for a preview):

```bash
docker compose --profile site run --rm -e SHOW_DRAFTS=1 site npx astro build
```

## Interactive pieces

Import them at the top of a lesson, just under the frontmatter:

```mdx
import Reveal from "../../site/src/components/Reveal.astro";
import Quiz from "../../site/src/components/Quiz.astro";
import Checklist from "../../site/src/components/Checklist.astro";
```

| Component | What it does | Example |
|---|---|---|
| `<Reveal>` | Hides its contents until the reader clicks. Used for "think first, then look". Works without JavaScript. | `<Reveal label="Show the root cause">…</Reveal>` |
| `<Quiz>` | One multiple-choice question, with instant feedback and an explanation. `answer` counts from 0. | `<Quiz question="…" options={["a", "b"]} answer={1}>Why.</Quiz>` |
| `<Checklist>` | Tick boxes for "I ran this" steps, remembered in the reader's browser. `id` must be unique across the course. | `<Checklist id="l0-verify" items={["…", "…"]} />` |

Every code block also gets a **Copy** button automatically, and each lesson
ends with a **Mark this lesson complete** button. Progress shows on the course
page.

Progress is stored in the reader's own browser (`localStorage`). It's a
convenience, not an account: a different browser or a private window starts
fresh.

## Links

Write links the way that works on GitHub. A small plugin
(`src/lib/remark-lesson-links.mjs`) rewrites them for the site:

- `01-whose-data-is-this.mdx` becomes `/course/01-whose-data-is-this/`
- `../../docs/...` becomes the file on GitHub. **The repo is private for now**,
  so those links only work for its owner.

## Not done yet

- **Hosting.** Nothing is deployed. The site builds to plain files in `dist/`,
  which GitHub Pages, Netlify or Cloudflare Pages can serve for free.
- **Search, RSS, a custom domain.** Add when there's enough content to need them.
