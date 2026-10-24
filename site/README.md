# Course website

The website for **Support Engineering by Building Systems**, built with
[Astro](https://docs.astro.build/) and its documentation theme,
[Starlight](https://starlight.astro.build/). It serves the course: the lessons
in `../content/course/NN-*.mdx`, in order, with their interactive parts.

The lessons live in `content/course/`, outside this folder, so they stay
readable on GitHub. This folder is only the machinery that turns them into web
pages. The engineering notes in `docs/` are not published.

**From Starlight, for free:** the lesson sidebar, "On this page" headings,
search (built sites only, see below), a light/dark/auto switch, the draft
banner, previous/next links, copy buttons on code, and a phone layout.

**Ours, on top:** the home page with progress, quizzes, reveals, checklists,
"mark this lesson complete", and the ticket simulator.

## Run it

```bash
make site
```

Then open <http://localhost:4321>. Edit a lesson and the page reloads by
itself. Like the rest of Deskly, it runs in Docker, so nothing is installed on
your Mac. It doesn't start with `make up`: the site isn't part of the app.

## Drafts and search

`draft: true` lessons **show** while running `make site`, with a draft banner,
and are **left out** of a real build. So nothing can be published by accident.

Search only works on a **built** site, because its index is made during the
build. To try it, build and preview (drafts won't be in it):

```bash
docker compose --profile site run --rm -p 4322:4321 site sh -c "npx astro build && npx astro preview --host 0.0.0.0"
```

Then open <http://localhost:4322>.

## Interactive pieces

Import them at the top of a lesson, just under the frontmatter:

```mdx
import Reveal from "../../site/src/components/Reveal.astro";
import Quiz from "../../site/src/components/Quiz.astro";
import Checklist from "../../site/src/components/Checklist.astro";
import TicketSimulator from "../../site/src/components/TicketSimulator.astro";
```

| Component | What it does | Example |
|---|---|---|
| `<Reveal>` | Hides its contents until the reader clicks. Used for "think first, then look". Works without JavaScript. | `<Reveal label="Show the root cause">…</Reveal>` |
| `<Quiz>` | One multiple-choice question, with instant feedback and an explanation. `answer` counts from 0. | `<Quiz question="…" options={["a", "b"]} answer={1}>Why.</Quiz>` |
| `<Checklist>` | Tick boxes for "I ran this" steps, remembered in the reader's browser. `id` must be unique across the course. | `<Checklist id="l0-verify" items={["…", "…"]} />` |
| `<TicketSimulator>` | A practice ticket. The reader picks checks, sees real outputs, and names the cause, against a clock. Each run hides a random cause. | `<TicketSimulator scenario={siteDown} />` |

Every code block gets a **Copy** button automatically, and each lesson ends
with a **Mark this lesson complete** button. Progress shows on the home page.

Each lesson also needs a sidebar label in its frontmatter:

```yaml
sidebar:
  label: "0 · The site is down"
  order: 0
```

### Writing a simulator scenario

A scenario is a TypeScript file in `src/scenarios/` (see `types.ts` for its
shape, and `site-down.ts` for a full example). It has one ticket, a list of
checks the reader can choose (each with a time cost), a list of possible
causes, and several **variants**: one per hidden cause, each with the result
every check gives. **Every output must be real**, captured from Deskly with
that part broken. The simulator exists to practise reading real evidence.

Progress is stored in the reader's own browser (`localStorage`). It's a
convenience, not an account: a different browser or a private window starts
fresh.

## Links

Write links the way that works on GitHub. A small plugin
(`src/lib/remark-lesson-links.mjs`) rewrites them for the site:

- `01-whose-data-is-this.mdx` becomes `/course/01-whose-data-is-this/`
- `../../docs/...` becomes the file on GitHub. **The repo is private for now**,
  so those links only work for its owner.

## If something looks wrong

- **The sidebar's lesson list is empty.** Starlight's automatic sidebar matches
  lessons by file path, and ours live outside its usual folder. The config uses
  `directory: "../content/course"` for exactly this reason. Don't "fix" it back
  to `"course"`.
- **The site won't start after `package.json` changes.** The container keeps
  its own copy of the installed packages. Rebuild with fresh ones:
  `docker compose --profile site up --build -V site`.

## If a page suddenly says "not found"

Switching git branches can briefly delete lesson files. The running site sees
them disappear but doesn't always notice them come back, and then logs
`The collection "course" does not exist or is empty`. Restart it:

```bash
docker compose --profile site restart site
```

## Not done yet

- **Hosting.** Nothing is deployed. The site builds to plain files in `dist/`,
  which GitHub Pages, Netlify or Cloudflare Pages can serve for free.
- **Search, RSS, a custom domain.** Add when there's enough content to need them.
