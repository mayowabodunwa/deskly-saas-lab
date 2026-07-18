# Phase 6 — Integrations: public API, webhooks, and interactive docs

**Goal:** make Deskly a platform others build on. A **public REST API** (token-authed, versioned, rate-limited), **outbound webhooks** (signed, retried, logged) so customers get pushed events, and **interactive OpenAPI docs** with a live "try it" console.

**Done when:** a customer can create a ticket via the public API using a token, receives a signed `ticket.created` webhook at their endpoint, and can explore + call the API from a Swagger/Redoc page that shows every endpoint and lets them test with their token.

## Concepts to teach here

- **Pull vs push.** An **API** lets a customer *pull* data or *push* changes on their schedule. **Webhooks** let Deskly *push* events to the customer the instant something happens, so they don't have to poll. Real integrations use both.
- **Webhook security.** The customer's endpoint is public on the internet — how do they know a POST really came from Deskly and wasn't forged or replayed? You **sign** each payload with an HMAC using a per-endpoint secret and include a timestamp; the receiver recomputes the signature to verify. Teach HMAC signing + timestamp (replay protection) as the standard pattern.
- **Delivery reliability.** Their endpoint will sometimes be down. You must **retry with backoff**, cap attempts, and **log every delivery** (status, response, attempts) so both sides can debug. This reuses the idempotency/retry mindset from Phase 4 — deliveries run as Celery tasks.
- **API versioning & rate limiting.** Public APIs are contracts. Version them (`/api/v1/`) so you can evolve without breaking customers, and rate-limit per token to protect the platform.
- **Docs as a product.** For an API, the docs *are* the UX. OpenAPI (formerly Swagger) is a machine-readable description of your API; from it you get an interactive console, client SDKs, and always-accurate reference docs. Generating the spec from code keeps docs honest.

## Build steps (vertical slice)

1. **API tokens.** `ApiToken(organization, name, hashed_token, scopes, last_used)`. Issue via the settings UI, store only a hash, authenticate the public API with a `Token`/`Bearer` header. This is distinct from the human JWT flow in Phase 2 — server-to-server auth.
2. **Versioned public API.** Namespace public endpoints under `/api/v1/`, reuse the DRF viewsets but with token auth + per-token throttling. Everything stays tenant-scoped via the token's org.
3. **Webhook model + dispatch.**
   - `WebhookEndpoint(organization, url, secret, events[], is_active)` and `WebhookDelivery(endpoint, event, payload, status, attempts, response_code, ...)`.
   - On domain events (`ticket.created`, `ticket.updated`, `comment.created`), enqueue `deliver_webhook.delay(...)`.
   - The task signs the payload (HMAC-SHA256 over `timestamp.body`, header like `X-Deskly-Signature`), POSTs, records the delivery, and retries with backoff on failure up to a cap.
   - Add a "resend" button and a deliveries log in the UI so customers can debug.
4. **OpenAPI docs + test console.** Generate the schema from DRF with `drf-spectacular`, serve **Swagger UI** and/or **Redoc**, and enable "Authorize" so a user pastes a token and calls endpoints live. Document auth, pagination, errors, and rate limits.
5. **Receiver example.** Give the learner a tiny sample receiver (a 20-line Flask/FastAPI app or a webhook.site tip) that verifies the signature — so they experience both sides.

Representative signing + delivery (let them adapt):

```python
def sign(secret: bytes, timestamp: str, body: bytes) -> str:
    msg = timestamp.encode() + b"." + body
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()

@shared_task(bind=True, max_retries=5, retry_backoff=True)
def deliver_webhook(self, delivery_id):
    d = WebhookDelivery.objects.select_related("endpoint").get(id=delivery_id)
    body = json.dumps(d.payload).encode()
    ts = str(int(time.time()))
    headers = {"X-Deskly-Signature": sign(d.endpoint.secret, ts, body),
               "X-Deskly-Timestamp": ts, "Content-Type": "application/json"}
    try:
        r = requests.post(d.endpoint.url, data=body, headers=headers, timeout=5)
        d.record(r.status_code)
        if r.status_code >= 500:
            raise self.retry()
    except requests.RequestException as exc:
        d.record(None); raise self.retry(exc=exc)
```

## Verify

- Create a ticket through `/api/v1/` using an API token (no session/JWT) → it appears, scoped to the token's org.
- A registered endpoint receives a signed `ticket.created` POST; your sample receiver verifies the signature successfully; a tampered body fails verification.
- Point an endpoint at a URL that returns 500 → the delivery retries with backoff and the attempts are logged; fix the URL and "resend" succeeds.
- The Swagger/Redoc page lists every v1 endpoint; "Authorize" with a token lets you create a ticket from the browser and see the response.
- Hammer the API past the rate limit → you get `429` with a clear message.

## Best practices to call out

- **Sign webhooks + include a timestamp**; document how receivers verify. Provide the secret once and let customers rotate it.
- **Retry with capped exponential backoff and log everything.** Deliverability + debuggability are the whole game.
- **Version from v1** and never break a released contract; add, don't mutate.
- **Rate-limit per token** and return proper `429`s with `Retry-After`.
- **Store only hashed tokens**; show the plaintext once at creation.
- **Generate docs from code** so they can't drift from reality.

## Canonical docs

- DRF (viewsets, throttling, versioning): https://www.django-rest-framework.org/api-guide/throttling/ and https://www.django-rest-framework.org/api-guide/versioning/
- drf-spectacular (OpenAPI): https://drf-spectacular.readthedocs.io/
- OpenAPI spec: https://spec.openapis.org/oas/latest.html
- Swagger UI: https://swagger.io/tools/swagger-ui/ · Redoc: https://redocly.com/redoc
- HMAC: https://datatracker.ietf.org/doc/html/rfc2104
- Standardized webhook signing conventions: https://www.standardwebhooks.com/

## Common issues (lab copilot fodder)

- **Receiver says signature invalid** → mismatch in what's signed (raw body vs re-serialized JSON) or the secret; sign the *exact bytes* you send and verify the same bytes.
- **Webhooks fire but never arrive** → receiver behind localhost; use a tunneling tool or webhook.site during dev.
- **Duplicate deliveries** → receivers must be idempotent (use an event id); teach that at-least-once delivery is normal.
- **Swagger "try it" gets 401** → the "Authorize" token/scheme isn't wired to the spec's security definition; align the auth class with the documented scheme.
- **Docs missing endpoints** → schema generation not picking up a viewset; check spectacular settings and serializers.
