# Phase 4 — Async plane: exports & scheduled email

**Goal:** move slow and scheduled work off the request/response path. Build CSV **exports** (generated in the background, stored in object storage, delivered by a link) and **scheduled email** (a nightly open-tickets digest and SLA-breach reminders), using Celery + Redis + MinIO + MailHog.

**Done when:** clicking "Export" returns immediately and the CSV arrives via email + is downloadable from MinIO; and a scheduled task emails a digest that lands in MailHog on a cron-like schedule.

## Concepts to teach here

- **Why async at all.** An HTTP request should be fast (sub-second). Anything slow — building a big CSV, calling a flaky third party, sending email — must not block the user's request or risk a timeout. So we *enqueue a job* and respond right away; a worker does the heavy lifting later. Analogy: a restaurant taking your order (fast) vs. cooking it (slow, happens in the kitchen).
- **The pieces.** A **task** is a function that can run in the background. A **broker** (Redis) is the queue that holds pending tasks. A **worker** is a process that pulls tasks and runs them. **Celery Beat** is a scheduler that enqueues tasks on a timetable (the cron of the async world).
- **Idempotency & retries.** Networks fail; workers crash mid-task. Design tasks so running them twice is safe (idempotent) and so transient failures retry with backoff. This mindset carries straight into webhooks (Phase 6).
- **Object storage for artifacts.** Generated files don't belong in the DB or on a pod's disk (pods are ephemeral). They go to MinIO (local) / S3 (cloud); we hand out a short-lived signed URL.

## Build steps (vertical slice)

1. **Add Celery + Redis broker.** Wire Celery into the Django project, point it at `REDIS_URL`, add a `worker` and a `beat` service to Compose. Confirm a trivial `debug_task` runs in the worker.
2. **Add MinIO + `django-storages`.** Configure S3-compatible storage against MinIO locally (same code targets S3 in Phase 7). Create a bucket for exports.
3. **Add MailHog.** Point Django's email backend at MailHog's SMTP locally; MailHog's web UI is your fake inbox. Same email code will target SES later.
4. **Export flow.**
   - `POST /api/orgs/<slug>/exports/` creates an `Export(status="pending")` row and enqueues `build_export.delay(export_id)`, returns `202` with the export id.
   - `build_export` streams tickets to a CSV, uploads to MinIO, sets `status="ready"` + a signed URL, and enqueues an email with the link.
   - SPA polls `GET /exports/<id>/` (or is notified) and shows a download button when ready.
   - Make it idempotent: re-running for an already-ready export shouldn't duplicate work.
5. **Scheduled email.** Define `send_daily_digest` (per org: counts of open/pending tickets, oldest untouched) and `check_sla_breaches`. Register them on a Beat schedule (e.g. digest at 8am, SLA check hourly). Use `celery-beat`'s database scheduler so schedules are editable without redeploy.

Representative task (let them adapt):

```python
@shared_task(bind=True, max_retries=3, retry_backoff=True)
def build_export(self, export_id):
    export = Export.objects.get(id=export_id)
    if export.status == "ready":
        return                                   # idempotent: already done
    try:
        url = write_tickets_csv_to_storage(export)   # streams to MinIO/S3
        export.mark_ready(url)
        email_export_link.delay(export.id)
    except TransientError as exc:
        raise self.retry(exc=exc)                # backoff + retry
```

## Verify

- Click Export → immediate `202`; within seconds the row flips to `ready`, the file appears in the MinIO console, and an email with the link shows up in MailHog.
- Trigger the digest task manually (`celery ... call send_daily_digest`) → a digest email lands in MailHog with correct counts.
- Beat is running: leave it up and confirm the scheduled task fires on time (shorten the interval to test, then restore).
- Kill the worker mid-export and restart → the task retries/resumes without producing a corrupt or duplicate file.

## Best practices to call out

- **Keep tasks small, idempotent, and retryable.** Pass ids, not big objects; re-fetch inside the task.
- **Don't block the web process** waiting on a task result; return a handle and let the client poll or get notified.
- **Signed, expiring URLs** for downloads — never make the bucket public.
- **Set task time limits and a dead-letter/max-retries policy** so a poison task can't loop forever.
- **Separate queues** for latency-sensitive vs. bulk work as you grow (mention, don't over-engineer now).
- **Beat schedules in the DB** so ops can adjust timing without a deploy.

## Canonical docs

- Celery: https://docs.celeryq.dev/en/stable/
- Celery + Django: https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
- Periodic tasks (Beat): https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
- django-celery-beat: https://django-celery-beat.readthedocs.io/
- django-storages (S3): https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
- MinIO: https://min.io/docs/minio/container/index.html
- MailHog: https://github.com/mailhog/MailHog
- Django email: https://docs.djangoproject.com/en/stable/topics/email/

## Common issues (lab copilot fodder)

- **Task "sent" but nothing happens** → no worker consuming that queue, or broker URL mismatch; check the worker logs and `REDIS_URL`.
- **Export works locally but link 403s** → bucket/credentials or signing config; MinIO needs the right endpoint + path-style setting.
- **Emails vanish** → wrong email backend; confirm it points to MailHog SMTP and check MailHog's UI, not a real inbox.
- **Beat runs tasks twice** → two Beat processes running; there must be exactly one scheduler.
- **Big export eats memory** → stream rows/use a generator instead of building the whole CSV in memory.
