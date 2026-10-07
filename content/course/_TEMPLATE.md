---
title: "Lesson N: <the promise, in the reader's language — not the tech's>"
description: "<one sentence a support engineer would recognise as their problem>"
pubDate: 2026-01-01
lesson: 0
phase: 0
tags: []
ticket: "<the one-line support ticket this lesson teaches you to handle>"
draft: true
---

> **Copy this file to start a new article.** Delete these instruction blocks as
> you fill each section. Keep `draft: true` until reviewed.
>
> Field notes: `lesson` orders the course; `phase` maps back to the build phase
> in `docs/`; `ticket` is the hook and doubles as the article's search intent.

## The ticket

> Open with a realistic support ticket, quoted as a customer would actually
> write it — vague, emotional, missing detail. This is the hook and the frame.

```
Subject: <what the customer typed>
From: <role, company>

<Two or three lines. No technical detail. The way tickets really arrive.>
```

**What you can tell from this alone:** <almost nothing — say so, and say why
that is the normal starting position>

## Why this part of the system exists

> Plain English, no jargon. What problem was this piece invented to solve?
> An analogy earns its place here.

## Concepts you need

> Define every term the first time. One line each, plain words first, precise
> wording second. If a reader has to look something up elsewhere, this section
> failed.

- **<Term>** — <plain-English meaning>. <Why it matters here.>

## Build it

> The actual steps. Real commands, in order, copy-pasteable. Say what each one
> does before the reader runs it — never a wall of commands with no narration.

```bash
<command>
```

<What that did, and what to expect on screen.>

## Verify it

> A concrete, falsifiable check. Not "it should work" — an exact thing to see.

**You'll know it worked when:** <precise observable outcome>

```bash
<verification command>
```

```
<expected output>
```

## Break it, then fix it

> The core of this course. Break the thing deliberately, then diagnose it from
> symptoms alone — as if you had not just built it.

**Break it:**

```bash
<command that breaks it>
```

**What the customer sees:** <the symptom, in their words>

**What you see:** <logs, status codes, empty lists — the evidence available>

**Reason it through:**

1. <First thing to check, and why that one first>
2. <What each possible result rules in or out>
3. <Narrowing to the cause>

**Root cause:** <the actual mechanism, explained>

**Fix it:**

```bash
<command that restores it>
```

**Why this failure mode is dangerous:** <especially if it fails silently>

## Trade-offs & decisions

> Why this design and not the obvious alternatives. Link the ADR for the full
> record. Support engineers who understand *why* a system is shaped a certain
> way escalate far better than ones who only know what buttons to press.

| Option | Pros | Cons | Chosen |
|---|---|---|---|
| | | | |

Full record: [`docs/adr/NNNN-<slug>.md`](../../docs/adr/NNNN-<slug>.md)

## What actually broke for me

> Real errors from `docs/troubleshooting-log.md`, quoted verbatim. This is the
> credibility section — it proves the walkthrough is real and not idealised.

## Production reality check

> What we did here vs. what production does, from `docs/known-gaps.md`. Name the
> shortcut honestly and say when it starts to matter at scale.

## Support takeaways

> The section a reader screenshots. Make it scannable and immediately usable.

**Next time you see this ticket, check in this order:**

1. <fastest check that rules out the most>
2. <next>
3. <next>

**Questions to ask the customer:** <the ones that actually narrow it down>

**When to escalate:** <the specific signal that this is not yours to fix>

## Next

<One line pointing to the next lesson and what it unlocks.>
