# Deskly — product spec

Read this first when a build session starts fresh. It gives the learner a concrete product to hang every technical concept on. A vague "todo app" doesn't force you to confront multi-tenancy, async work, or integrations — a support desk does.

## One-liner

**Deskly is a multi-tenant SaaS help desk.** Companies sign up, invite their support agents, and manage customer support tickets. Deskly notifies people by email, exports data, exposes a public API + webhooks so customers can plug it into their own tools, and has an AI assistant that drafts replies and explains issues.

## Who uses it

- **Organization owner** — signs up, owns billing/plan, invites agents, configures the org.
- **Agent** — works tickets: reads, replies, changes status, assigns.
- **Viewer** — read-only (e.g. a manager watching metrics).
- **End customer** — the person who filed the ticket (initially via email or the public API; a customer portal is an optional stretch goal).
- **Deskly staff (you)** — the platform operator. Uses the admin to support customers, impersonate accounts to reproduce bugs, and roll features out behind flags.

This role list is deliberately small but gives us real **RBAC** (role-based access control) to implement in Phase 2.

## Core domain objects

Keep the model small and sharp. Everything below is scoped to an organization (the tenant boundary).

- **Organization** — the tenant. Has a plan (`free`, `pro`), a name, a slug.
- **Membership** — links a User to an Organization with a `role` (owner/agent/viewer). A user can belong to several orgs.
- **Ticket** — belongs to an org. Has subject, body, `status` (open/pending/closed), `priority`, a requester (the customer), an optional assignee (an agent), timestamps.
- **Comment** — a message on a ticket. Has an author, body, and `is_internal` (agent-only note vs. reply visible to the customer).
- **KnowledgeArticle** — help-center content the AI assistant retrieves from when drafting replies (Phase 5).
- **WebhookEndpoint** / **WebhookDelivery** — a customer-registered URL and the log of attempts (Phase 6).
- **ApiToken** — a per-org token for the public API (Phase 6).
- **AuditLog** — records sensitive actions, especially impersonation (Phase 3).

## What each requirement maps to

This is the "why this product" table — use it to motivate each phase.

- **Multi-tenancy** → Organizations own all data; every query is tenant-scoped. This is *the* defining SaaS concern.
- **Admin impersonation** → Deskly staff need to see exactly what a customer's agent sees to reproduce a bug. Naturally sensitive → must be audited.
- **Feature flags** → Roll "AI suggested replies" out to `pro` orgs first, or dark-launch a risky feature to 5% of orgs. Plan-gating and gradual rollout in one mechanism.
- **OAuth / JWT / Sessions** → Agents log into the web app (session cookie). Customers' backends call the public API (JWT / token). "Sign in with Google" (OAuth) removes password management.
- **Exports (queue)** → "Export all tickets to CSV" can be slow → must run off the request thread as a background job, then email a download link.
- **Email scheduling (queue)** → A nightly "open tickets digest" and SLA-breach reminders → scheduled periodic tasks.
- **AI assistant** → When an agent opens a ticket, Deskly drafts a suggested reply grounded in the org's knowledge base. Huge real-world SaaS feature.
- **MCP integration** → Expose Deskly's tickets/search as MCP tools so Claude (in Claude Desktop or the app) can answer "how many tickets breached SLA this week?" or help operate the lab.
- **Webhooks / API / docs** → Customers integrate Deskly with their own systems: our webhooks push `ticket.created` events out; our REST API + interactive OpenAPI docs let them pull and push data with a live "try it" console.
- **Containers / K8s / AWS** → Ship the whole thing reproducibly, from laptop to a real (free-tier) cloud cluster.

## Scope discipline

The goal is *learning the shape of production*, not shipping a startup. So:
- **In scope:** the objects above, the flows those requirements imply, and doing each one the way the docs recommend.
- **Explicitly out of scope (mention, don't build unless asked):** real billing/payments, a polished customer-facing portal, i18n, mobile apps, and horizontal scale tuning. These are great stretch goals once the core lab works.

Keep the learner anchored here whenever scope creep threatens to stall a phase.
