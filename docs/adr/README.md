# Architecture Decision Records (ADRs)

An **ADR** is a short document capturing one significant decision: the situation
we were in, what we chose, what we gave up, and what we rejected.

## Why bother

Six months from now nobody remembers *why*. Without a record, a future engineer
sees a deliberate choice, mistakes it for an accident, and "fixes" it — usually
reintroducing the exact problem the decision was made to avoid.

ADRs are **append-only and immutable**. You never rewrite one. If a decision
changes, you write a *new* ADR that supersedes it, and mark the old one
`Superseded by ADR-NNNN`. The history of your thinking is the valuable part.

## When does something need an ADR?

The test: **would a future engineer look at this and ask "why on earth did they
do it that way?"**

- Yes → write an ADR.
- No, it's the obvious choice → a line in the phase note is enough.

Also worth one: anything expensive to reverse later, anything with a security or
scaling consequence, and anything where you seriously considered an alternative.

## Index

| # | Decision | Status | Phase |
|---|---|---|---|
| [0001](0001-local-first-docker-compose.md) | Local-first stack on Docker Compose | Accepted | 0 |
| [0002](0002-tenant-column-isolation.md) | Shared database with a tenant column | Accepted (implementation pending) | 1 |

## Statuses

- **Proposed** — under discussion, not yet acted on.
- **Accepted** — decided; this is what we do.
- **Superseded by ADR-NNNN** — replaced by a later decision. Left in place.
- **Deprecated** — no longer applies, nothing replaced it.

## Template

```markdown
# ADR-NNNN — <short decision title>

- **Status:** Proposed | Accepted | Superseded by ADR-NNNN | Deprecated
- **Date:** YYYY-MM-DD
- **Phase:** N

## Context
<The situation and the forces at play. What made a decision necessary?
 Written so someone with no history on the project understands the pressure.>

## Decision
<What we chose, stated plainly and actively: "We will ...">

## Consequences
**Good:** <what this buys us>
**Bad:** <what it costs us — be honest; a consequence-free decision is a
 decision that wasn't really made>
**Risks to watch:** <what could bite us, and the signal it is happening>

## Alternatives considered
| Option | Why not |
|---|---|
```
