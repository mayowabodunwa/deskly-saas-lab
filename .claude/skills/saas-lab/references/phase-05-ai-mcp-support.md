# Phase 5 — AI plane: in-app assistant, MCP, and the lab copilot

**Goal:** three connected AI capabilities. (1) An **in-app support assistant** that drafts replies to tickets, grounded in the org's knowledge base. (2) An **MCP server** that exposes Deskly's data as tools an AI client (Claude Desktop / the app) can call. (3) The **lab copilot** pattern you use throughout the build to explain errors the learner hits.

**Done when:** opening a ticket shows an AI-drafted reply the agent can edit and send (never auto-sent, and gated by the Phase 3 flag); and Claude, connected to Deskly's MCP server, can answer "how many open tickets does Org A have?" by calling a real tool.

> **Cost note (say this out loud):** this is the *only* non-free dependency in the lab — the model API. Keep it to cents by using a small/cheap model for drafts, enabling **prompt caching** for the repeated system prompt + knowledge context, and capping `max_tokens`. Everything else in Deskly stays free. Before quoting any specific model name, pricing, limit, or SDK detail, consult the **product-self-knowledge** skill rather than memory — those facts change.

## Concepts to teach here

- **Grounding / RAG (retrieval-augmented generation).** Don't ask a model to invent support answers — *retrieve* the org's relevant knowledge articles and past resolved tickets, put them in the prompt, and ask the model to answer *using that context*. This is how you get accurate, on-brand replies instead of hallucinations. Start simple: keyword/`ILIKE` search or Postgres full-text; graduate to vector embeddings + `pgvector` only if the learner wants it.
- **Human-in-the-loop.** The assistant *drafts*; the agent *approves*. Teach why auto-sending AI text to customers is a trust and safety risk. The flag from Phase 3 lets you roll it out carefully.
- **What MCP is and why it's better than raw DB access.** The Model Context Protocol is an open standard for exposing *tools*, *resources*, and *prompts* to AI clients over a well-defined interface. Instead of handing a model database credentials, you expose a small, explicit, auditable set of tools (`search_tickets`, `get_ticket`, `org_stats`) with typed inputs and permission checks. The AI can only do what you exposed. Analogy: a well-designed API for an AI consumer.
- **Tool design.** Good tools are narrow, well-described, and return concise structured data. Bad tools are "run any SQL." Teach the difference — it's the same instinct as good API design.

## Build steps (vertical slice)

### A. In-app support assistant
1. **Knowledge model + search.** `KnowledgeArticle(organization, title, body)`. Add search (Postgres full-text to start). Seed a few articles.
2. **Assistant service.** A backend service `draft_reply(ticket)` that: retrieves top-k relevant articles + the ticket thread, builds a grounded prompt ("answer as a support agent, using only the context; if unsure, say so"), calls the model API, and returns a draft + the sources it used.
3. **Endpoint + UI, behind the flag.** `POST /api/tickets/<id>/suggest-reply/` returns the draft. The SPA shows it in an editable box with a "sources" chip; the agent edits and sends. Gate the whole feature on `ai_suggested_replies` (Phase 3).
4. **Safety rails.** Cap tokens, add a per-org rate limit, log every call (prompt hash, tokens, latency) for cost visibility, and never auto-send.

### B. MCP server
5. **Stand up an MCP server** (e.g. a small FastMCP service, or the reference MCP SDK) as its own container in Compose. It authenticates to Deskly's API with a scoped token and exposes tools:
   - `search_tickets(org, query, status?)` → list of matches
   - `get_ticket(org, id)` → ticket + thread
   - `org_stats(org)` → counts by status, SLA breaches this week
   Each tool re-uses the *same tenant scoping and permissions* as the API — the MCP server is just another API client, not a backdoor.
6. **Connect a client.** Point Claude Desktop (or the app's connector settings) at the MCP server and demonstrate asking a natural-language question that triggers `org_stats`. This is the "AI can operate/answer questions about the SaaS" requirement, done the standard way.

### C. Lab copilot (use this all through the build)
7. **Codify the pattern** you already use when the learner hits errors: (a) restate what the error *means* in plain language, (b) name the most likely cause *given which phase/slice they're in*, (c) suggest the smallest diagnostic step before any fix, (d) then fix and explain. Optionally expose it in-app as a "explain this error" helper that feeds a stack trace + context to the assistant.

Representative grounded draft (let them adapt; verify model/SDK specifics via the product-self-knowledge skill):

```python
def draft_reply(ticket):
    context = search_knowledge(ticket.organization, ticket.subject, k=4)
    system = ("You are a Deskly support agent. Answer using ONLY the provided context. "
              "If the context is insufficient, say what else you need. Be concise and kind.")
    user = render_prompt(ticket=ticket, context=context)
    resp = llm.messages(system=system, messages=[{"role": "user", "content": user}],
                        max_tokens=500)   # cap cost; enable prompt caching on system+context
    return {"draft": resp.text, "sources": [c.id for c in context]}
```

## Verify

- With the flag ON for an org, opening a ticket yields a relevant, grounded draft with source chips; with the flag OFF, the feature is absent.
- The draft is never auto-sent — it lands in an editable field.
- Claude, connected to the MCP server, answers an org-stats question by actually calling the tool (check the MCP server logs for the tool invocation).
- MCP tools respect tenant scoping: asking about an org the token can't access returns nothing/denied, not a leak.

## Best practices to call out

- **Ground, don't guess.** Retrieval + "use only this context" beats a bare prompt for accuracy.
- **Human-in-the-loop for anything customer-facing.** Draft, review, send.
- **Expose *narrow* MCP tools, not raw data access.** Same permission model as your API; log every tool call.
- **Watch cost from day one** — cap tokens, cache the static prompt prefix, log usage, prefer a cheaper model for drafts.
- **Never put secrets or other tenants' data in a prompt.** Prompt-injection and cross-tenant leakage are the new SQL injection; sanitize retrieved content and scope retrieval to the org.
- **Verify product facts via the product-self-knowledge skill**, not memory, before stating models/pricing/limits.

## Canonical docs

- Model Context Protocol: https://modelcontextprotocol.io/ and the spec https://modelcontextprotocol.io/specification
- MCP servers/SDKs: https://github.com/modelcontextprotocol
- Anthropic API + prompt caching + tool use: https://docs.claude.com/ (and confirm specifics via the product-self-knowledge skill)
- Postgres full-text search: https://www.postgresql.org/docs/current/textsearch.html
- pgvector (optional, for embeddings): https://github.com/pgvector/pgvector

## Common issues (lab copilot fodder)

- **Drafts are generic / wrong** → retrieval isn't returning relevant context; inspect what `search_knowledge` returned and tighten the query or add articles.
- **Costs creeping up** → uncapped tokens or no caching; add `max_tokens`, cache the static prefix, log per-call usage.
- **MCP client won't connect** → transport/URL/auth mismatch; check the client config and the server logs, and confirm the scoped token works against the API directly first.
- **MCP tool returns another org's data** → the tool bypassed `for_org`; route every tool through the same scoped API path.
- **Model/pricing detail is stale** → you answered from memory; re-check with the product-self-knowledge skill.
