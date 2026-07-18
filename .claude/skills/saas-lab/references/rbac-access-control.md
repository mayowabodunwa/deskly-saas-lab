# RBAC deep-dive — limiting access by permission

Cross-cutting reference. Phase 2 gives Deskly three roles (owner/agent/viewer) and a couple of permission classes — enough to get moving. Open this when the learner wants **real** access control: granular permissions, enforcement at every layer, object- and field-level rules, a permission-aware UI, and a test that locks it all in. This is one of the highest-leverage things to get right in a SaaS, because a gap here is a security incident, not a bug.

## Concepts to teach here

- **Roles vs permissions.** A **permission** is a single fine-grained capability: `ticket.reply`, `ticket.assign`, `member.invite`, `export.create`, `webhook.manage`, `org.settings.edit`. A **role** is a *named bundle* of permissions (owner = everything; agent = work tickets; viewer = read-only). Code checks **permissions**, not roles. Why: you can change what a role can do — or add custom roles later (a nice Pro-plan feature via Phase 3 flags) — without hunting down every `if role == "agent"` in the codebase. Analogy: a role is a job title; permissions are the individual keys on the keyring that title carries.
- **Defense in depth — enforce at three layers.** The same rule is expressed three times on purpose:
  1. **Data layer (queryset):** you can only load rows you're allowed to see. Deny by default (Phase 1's `for_org`, plus row-level filters where needed).
  2. **API layer (the real gate):** each endpoint declares the permission it requires; the request is refused without it. *This is the boundary that actually protects you.*
  3. **UI layer (UX only):** hide or disable controls the user can't use, so they never see a button that would just 403. **Never trust the UI** — a hidden button is a convenience, not a security control. Someone can always call the API directly.
  This directly answers "limit access based on permission": the UI *reflects* permissions; the API *enforces* them; the data layer is the *backstop*.
- **View-level vs object-level.** "Can this user reply to tickets?" is view-level. "Can this user reply to *this* ticket?" is object-level (e.g. it must be in their org, and maybe only if they're the assignee). Both matter; object-level catches the [IDOR](https://owasp.org/www-community/attacks/) class of bug where a valid user pokes at another record's id.
- **Field-level.** Some fields within an allowed object are still restricted — e.g. a `Comment.is_internal` agent note must not appear to a `viewer` (or a future customer). Enforce in the serializer.
- **Least privilege + deny by default.** New endpoints require an explicit permission; anything unspecified is denied. The safe failure mode is "no access," never "all access."

## Build steps (vertical slice)

### 1. Define the permission catalog and role map
Keep permissions as constants and roles as bundles, in one place:

```python
# permissions.py
class Perm:
    TICKET_VIEW   = "ticket.view"
    TICKET_REPLY  = "ticket.reply"
    TICKET_ASSIGN = "ticket.assign"
    TICKET_DELETE = "ticket.delete"
    MEMBER_INVITE = "member.invite"
    ORG_SETTINGS  = "org.settings.edit"
    EXPORT_CREATE = "export.create"
    WEBHOOK_MANAGE = "webhook.manage"

ROLE_PERMISSIONS = {
    "owner":  {p for p in vars(Perm).values() if isinstance(p, str)},  # all
    "agent":  {Perm.TICKET_VIEW, Perm.TICKET_REPLY, Perm.TICKET_ASSIGN, Perm.EXPORT_CREATE},
    "viewer": {Perm.TICKET_VIEW},
}

def permissions_for(membership):
    if membership is None:
        return set()
    return ROLE_PERMISSIONS.get(membership.role, set())

def has_perm(membership, perm):
    return perm in permissions_for(membership)
```

(Starting with a static role→permission map is the right call. Only move to storing per-role permissions in the DB — enabling custom roles — once the learner actually needs it; note that as the graduation path.)

### 2. Enforce at the API layer (DRF)
A single permission class that reads the required permission off the view, so every endpoint is explicit:

```python
class HasOrgPermission(BasePermission):
    def has_permission(self, request, view):
        required = getattr(view, "required_permission", None)
        membership = getattr(request, "membership", None)   # resolved in Phase 1/2
        if required is None:      # deny-by-default: unspecified = no access
            return False
        return has_perm(membership, required)

    def has_object_permission(self, request, view, obj):
        # object-level: must be same tenant, plus any per-object rule
        if getattr(obj, "organization_id", None) != request.organization.id:
            return False
        return True

class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasOrgPermission]
    def get_permissions_map(self):  # different action → different permission
        return {"list": Perm.TICKET_VIEW, "retrieve": Perm.TICKET_VIEW,
                "create": Perm.TICKET_REPLY, "update": Perm.TICKET_REPLY,
                "destroy": Perm.TICKET_DELETE}
    @property
    def required_permission(self):
        return self.get_permissions_map().get(self.action)
    def get_queryset(self):
        return Ticket.objects.for_org(self.request.organization)   # data-layer backstop
```

### 3. Object- and field-level rules
- **Object-level:** `has_object_permission` already blocks cross-tenant ids. Add per-object logic where the product needs it (e.g. "an agent may only reassign tickets assigned to them" — check `obj.assignee_id == request.user.id`).
- **Field-level:** redact restricted fields in the serializer based on permissions:

```python
class CommentSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        m = self.context["request"].membership
        if instance.is_internal and not has_perm(m, Perm.TICKET_REPLY):
            return None            # viewers never see internal agent notes
        return data
```

### 4. Expose permissions to the frontend (permission-aware UI)
Return the user's **effective permissions** for the active org so the SPA can render accordingly:

```python
# GET /api/me/ -> { "user": {...}, "org": "...", "role": "agent",
#                   "permissions": ["ticket.view", "ticket.reply", ...] }
```

Then a tiny React guard so the UI mirrors the backend (UX only — the API still enforces):

```tsx
function Can({ perm, children }: { perm: string; children: React.ReactNode }) {
  const { permissions } = useAuth();          // from /api/me/
  return permissions.includes(perm) ? <>{children}</> : null;
}
// <Can perm="ticket.delete"><DeleteButton/></Can>
```

### 5. Get the interactions right
- **Impersonation (Phase 3):** while impersonating, permissions come from the *impersonated* membership, **not** your staff account — you see exactly what they can do, nothing more. Staff-only powers must not leak through impersonation.
- **Feature flags (Phase 3):** flags and permissions are **both** required and answer different questions. A flag decides *whether a feature exists* for an org; RBAC decides *who inside that org may use it*. `flag_enabled(...) AND has_perm(...)`.
- **Public API tokens (Phase 6):** tokens carry **scopes** — the same idea as permissions, for machines. Map token scopes onto the same catalog so API and UI enforcement stay consistent.
- **Audit (Phase 3):** log denials of sensitive actions and any change to a member's role; role changes are exactly the kind of privilege escalation you want a trail for.

### 6. Lock it in with a permission-matrix test
The single most valuable test in this area — role × action → expected outcome — so a future refactor can't silently widen access:

```python
MATRIX = {   # (role, action) : allowed?
    ("viewer", "create_ticket"): False, ("agent", "create_ticket"): True,
    ("viewer", "delete_ticket"): False, ("agent", "delete_ticket"): False,
    ("owner",  "delete_ticket"): True,  ("agent", "invite_member"): False,
    ("owner",  "invite_member"): True,
}
# parametrize a test that logs in as each role and asserts the API status matches.
```

## Verify

- A **viewer** gets `403` creating/deleting tickets and never sees those buttons; an **agent** can reply/assign but not delete or invite; an **owner** can do org settings + invites.
- Poking another org's ticket id returns `404/403` (object-level + tenant backstop), even for an owner.
- A `viewer` never receives `is_internal` comments in any API response (field-level).
- `/api/me/` returns the correct effective permission list; hiding a button doesn't stop the API from enforcing (test by calling the endpoint directly).
- While impersonating a viewer, you *cannot* perform agent/owner actions.
- The permission-matrix test passes and fails loudly if a role is accidentally widened.

## Best practices to call out

- **Check permissions, not roles, in code.** Roles are data; permissions are the interface.
- **Enforce on the server; the UI is a hint.** Every hide-in-UI must have a matching API denial.
- **Deny by default** — unspecified permission = no access; new endpoints must opt in.
- **Object-level checks stop IDOR** — always confirm the record belongs to the caller's org (and any per-object rule) before acting.
- **Keep one catalog** shared by API permissions, token scopes, and the UI, so the three never drift.
- **Test the matrix** and **audit role changes** — privilege escalation is the scariest failure mode.
- **Graduate to DB-stored roles only when needed** (custom roles), not preemptively.

## Canonical docs

- DRF permissions (custom + object-level): https://www.django-rest-framework.org/api-guide/permissions/
- Django auth & permissions model: https://docs.djangoproject.com/en/stable/topics/auth/default/
- OWASP access control cheat sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- OWASP broken access control (why this matters): https://owasp.org/Top10/A01_2021-Broken_Access_Control/
- (If you outgrow role maps) django-guardian for per-object perms: https://django-guardian.readthedocs.io/ · or a policy engine like OpenFGA/Oso for relationship-based access.

## Common issues (lab copilot fodder)

- **UI hides the button but the action still works via curl** → you only did UI-layer "security"; add the API permission check. This is the #1 RBAC mistake.
- **Owner can read another org's record** → you checked role but forgot the tenant/object check; role ≠ tenant. Add `has_object_permission`.
- **New endpoint is wide open** → no `required_permission` set and the class defaulted to allow; make the default *deny*.
- **Viewer sees internal notes** → field-level redaction missing in the serializer.
- **Staff powers leak during impersonation** → permissions read from the staff user instead of the impersonated membership.
- **Flag on but user still blocked (or vice-versa)** → you conflated "feature exists" with "user may use it"; require both.
