# Phase 3 — Admin, impersonation & feature flags

**Goal:** the operator surface. Deskly staff get a hardened admin, the ability to *impersonate* a customer's user to reproduce bugs (fully audited), and **feature flags** to gate features by plan or roll them out gradually.

**Done when:** from the admin you can start impersonating an agent, see the app exactly as they do, stop, and find both actions in an audit log; and a feature can be turned on for one org, for `pro` plans, or for 5% of orgs without a deploy.

## Concepts to teach here

- **Why an operator admin exists.** Real SaaS teams need to support customers without asking for their password. Django ships a powerful admin; the work is *hardening* it and adding two operator superpowers safely.
- **Impersonation = acting as another user.** Enormously useful ("I can see the bug the customer sees") and enormously sensitive (you're inside their account). The rule: it must be *deliberate, scoped, reversible, and logged*. Analogy: a bank manager who can open your account to help you — but every access is recorded.
- **Feature flags.** A switch that changes behavior at runtime without a deploy. Three uses to teach: **plan gating** (pro-only features), **gradual rollout** (dark-launch to X% to catch problems early), and **kill switch** (turn a misbehaving feature off instantly). This is how modern teams decouple *deploy* from *release*.
- **Audit logs.** Append-only records of sensitive actions. Non-negotiable for anything touching another user's data.

## Build steps (vertical slice)

1. **Harden Django admin.** Restrict to staff, put it behind auth (and ideally a non-obvious URL + admin-only 2FA later), register the core models with sensible `list_display`/`search_fields`/`readonly_fields`, and make `AuditLog` read-only in the admin.
2. **Audit log model.** `AuditLog(actor, action, target_user, organization, metadata_json, created_at)`. Write a small helper `record_audit(...)` used by any sensitive action.
3. **Impersonation.** Use `django-hijack` (maintained, handles the session swap and a visible "you are impersonating" banner) *or* implement a minimal version: an admin action that stores `impersonator_id` + `impersonated_id` in the session and swaps `request.user`. Whichever you pick:
   - Only staff can start it; you can't impersonate another staff/superuser.
   - Show a persistent banner in the SPA so it's impossible to forget you're impersonating.
   - `record_audit("impersonation.start"/"impersonation.stop", ...)` on both edges.
   - Impersonation respects tenant scoping — you see exactly what that user sees, nothing more.
4. **Feature flags.** Use `django-waffle` (flags/switches/samples) or a small `Flag` model. Support: per-org overrides, plan-based rules, and percentage rollout. Add a helper `flag_enabled("ai_suggested_replies", org, request)` and a serializer field so the SPA can show/hide UI accordingly.
5. **Gate a real feature.** Wire the Phase 5 "AI suggested replies" behind `ai_suggested_replies` so this isn't academic — flip it per org and watch the UI change.

Representative flag check + audit (let them adapt):

```python
def flag_enabled(name, org, request=None):
    override = org.feature_overrides.filter(name=name).first()
    if override:
        return override.enabled
    return waffle.flag_is_active(request, name) if request else False

def record_audit(actor, action, *, target_user=None, organization=None, **meta):
    AuditLog.objects.create(actor=actor, action=action, target_user=target_user,
                            organization=organization, metadata=meta)
```

## Verify

- As staff, start impersonating an agent → the SPA shows a banner and the ticket list reflects *that agent's* org; stop → you're yourself again.
- `AuditLog` has a start and stop row with actor, target, and timestamp.
- Turn `ai_suggested_replies` on for Org A only → its agents see the feature; Org B doesn't. Flip a percentage rollout and confirm roughly the right proportion.
- A non-staff user cannot reach impersonation at all (403).

## Best practices to call out

- **Impersonation is deny-by-default and staff-only**, can't target other admins, and every start/stop is audited. If you can't log it, don't build it.
- **Make impersonation visible.** The banner prevents the "I forgot I was in someone's account" class of incidents.
- **Flags need an owner and an expiry plan.** Stale flags rot into dead branches; note that real teams track and remove them.
- **Audit logs are append-only.** No edit/delete in the admin.
- **Harden the admin URL and access** — it's the highest-value target in the whole app.

## Canonical docs

- Django admin: https://docs.djangoproject.com/en/stable/ref/contrib/admin/
- django-hijack: https://django-hijack.readthedocs.io/
- django-waffle: https://waffle.readthedocs.io/
- Background reading on flags: https://martinfowler.com/articles/feature-toggles.html

## Common issues (lab copilot fodder)

- **Impersonation banner missing in the SPA** → the impersonation state isn't exposed to the frontend; add it to the `/api/me/` payload.
- **Flag changes require a reload** → expected; teach the difference between build-time and runtime config, and where to cache flag lookups.
- **Percentage rollout looks "sticky" per user** → that's correct (consistent bucketing by user/org id) so a user doesn't flip-flop; explain why stable hashing matters.
- **Audit rows editable** → mark them readonly and, ideally, block deletes at the model/DB level.
