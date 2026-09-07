# Troubleshooting Log

Append-only record of everything that broke, surprised us, or turned out to be a
dead end during the Deskly build. **Newest first.**

This file is the raw material for the "What actually broke for me" and
"Break it, then fix it" sections of each course article — and it is the part
that makes a public write-up credible. Idealised tutorials are everywhere; a
record of real failure is not.

## How to use it

Three entry types:

| Tag | Means |
|---|---|
| `ERROR` | It broke loudly. Something failed and said so. |
| `GOTCHA` | It "worked", but not the way we expected. Silent wrong behaviour. |
| `DEAD-END` | An approach we tried and abandoned — and why. |

Every entry answers five things in order: **Symptom → What it means → Root cause
→ Fix → Lesson.**

**Error text is quoted verbatim, never paraphrased.** Someone hitting the same
wall will paste their error into a search box — it has to match character for
character.

---

## 2026-07-18 — `GOTCHA` — Phase 0 — Container user had no home directory

**Symptom**
<!-- TODO: paste the verbatim error or the exact behaviour you saw.
     Recorded after the fact: the fix was adding `-m` to `useradd`, so the
     trigger was almost certainly a tool trying to write to `/home/app`
     (pip cache, shell history, or a dev-container extension) and finding no
     such directory. Replace this block with what you actually saw. -->

**What it means**
Linux gives every user a "home directory" — a private folder for that user's
settings, caches and temp files. `useradd -r` creates a *system* user for
running a service, and by default does **not** create one. Most of the time
that's fine, because a service just runs code. It stops being fine the moment
something tries to save a file "in your home folder" and there is no home
folder to save it in.

**Root cause**
`backend/Dockerfile` created the non-root `app` user without a home directory:

```dockerfile
RUN groupadd -r app && useradd -r -g app app
```

**Fix**
Add `-m` ("make the home directory"):

```dockerfile
RUN groupadd -r app && useradd -r -g app -m app
```

**Lesson**
Running containers as a **non-root user** is correct and important — if an
attacker breaks into the process, they land as a limited user rather than as
root with full control. But "non-root" has consequences beyond permissions: no
home directory, no write access outside declared volumes. Cheap to fix once you
know; confusing when a tool fails with a vague path error.

*Support angle:* "it works locally but fails in the container" is very often a
**permissions or missing-path** problem, not a code problem.

---

## 2026-08-08 — `ERROR` — Phase 0 / Concept T1 — Port 5432 already in use

**Symptom**
`docker compose up` failed to start the `db` service.

<!-- TODO: replace with your verbatim scrollback if you still have it.
     The text below is the standard Docker message for this condition and is
     RECONSTRUCTED, not quoted. -->

```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:5432 -> 0.0.0.0:0: listen tcp 0.0.0.0:5432: bind: address already in use
```

**What it means**
A "port" is a numbered door on your machine; only one program can hold a given
door at a time. Port **5432** is Postgres's standard door. Docker tried to open
it for Deskly's database and found something already standing there — almost
always a Postgres installed directly on the Mac, or another project's container
still running.

**Root cause**
`docker-compose.yml` published the container's port 5432 onto host port 5432,
which was already taken:

```yaml
ports: ["5432:5432"]
```

**Fix**
Move the **host** side to a free port. The left number is the door on your Mac;
the right number is the door inside the container. Only the left one has to
change:

```yaml
ports: ["5433:5432"]
```

Nothing inside Docker changes — the backend container still reaches the database
on 5432 over Docker's internal network. Only tools running on your Mac (a GUI
client like TablePlus, or `psql` in your terminal) now connect on **5433**.

Diagnose it before changing anything:

```bash
lsof -i :5432          # what is holding the port
docker ps              # is it another container of mine
```

**Lesson**
Port conflicts are one of the most common first-day Docker errors, and the
message is more intimidating than the problem. `address already in use` always
means the same thing: something else got there first. The two useful questions
are *what is holding it* and *do I need that thing running*.

*Support angle:* this is the shape of a whole class of tickets — a resource
that can only have one owner, quietly claimed by something the user forgot was
running.

---

<!-- New entries go ABOVE this line, newest first. Copy the shape above:
     ## DATE — TAG — Phase/Slice — one-line title
     Symptom (verbatim) / What it means / Root cause / Fix / Lesson -->
