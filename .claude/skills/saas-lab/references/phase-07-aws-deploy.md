# Phase 7 — Cloud: deploy to AWS (local→cloud, free-tier)

**Goal:** take the exact containers that run locally and run them on AWS, swapping the local backing services for managed ones — Postgres→RDS, object storage→S3, email→SES — with config/secrets injected at runtime. Stay inside the free tier.

**Done when:** the app is reachable at a real URL, using RDS Postgres, S3 for exports, and SES for email, with no secrets baked into images — and you can point at exactly which local piece each cloud piece replaced.

> **Free-tier discipline (say this first):** the AWS free tier is generous but easy to overspend by accident. Before creating anything, set a **billing alarm/budget**, prefer the smallest instance sizes (`t3.micro`/`t4g.micro`), use a single AZ, and **tear resources down** when not learning. Call out any resource that has no free tier (e.g. a NAT Gateway, most load balancers beyond the free hours) so the learner opts in knowingly. When in doubt, keep Redis and even Postgres as containers on one small instance instead of managed services.

## Concepts to teach here

- **Local↔cloud parity.** The reason we containerized from Phase 0: the image is the deployable unit. "Deploy" mostly means *run the same image with different environment variables*. This de-mystifies the cloud.
- **Managed services vs self-hosted.** RDS runs Postgres so you don't babysit backups/patching; S3 is durable object storage; SES sends real email. You trade a little money/lock-in for a lot less ops. Teach when each is worth it.
- **Where config and secrets live.** Never in the image or git. Use SSM Parameter Store / Secrets Manager and inject at runtime. Use an IAM role for the compute so the app gets S3/SES permissions *without* long-lived keys.
- **Registry.** Images are pushed to ECR and pulled by the runtime. Same image you built locally.
- **Pick the simplest runtime that teaches the idea.** Options, simplest first: a single **EC2** box running your Compose file; **ECS Fargate** (serverless containers); or full **EKS** (save real Kubernetes for Phase 8 locally to avoid EKS cost). Recommend EC2+Compose or Fargate for the free-tier lab.

## Build steps (vertical slice)

1. **Guardrails first.** Create an AWS Budget + billing alarm. Create a non-root IAM user for yourself with MFA. Note the region you'll use.
2. **Provision backing services (smallest sizes).**
   - **RDS Postgres** (free-tier `db.t3.micro`, single-AZ) — get the connection string.
   - **S3 bucket** for exports (block public access; the app writes with an IAM role and hands out signed URLs — same code as MinIO).
   - **SES** — verify a sender identity; note it starts in sandbox (can only send to verified addresses) which is fine for a lab. Same Django email code as MailHog.
3. **Secrets & config.** Put `DATABASE_URL`, `SECRET_KEY`, model API key, etc. in SSM/Secrets Manager. Give the compute an **IAM role** granting least-privilege S3/SES access — no static keys.
4. **Build & push images to ECR.** Tag with a git SHA (immutable, traceable). This is your first taste of a real release artifact.
5. **Run it.** On the chosen runtime (EC2+Compose or Fargate), run backend, worker, and beat from the pushed images with the cloud env vars. Run migrations as a one-off task/command.
6. **Front door + TLS.** Put the app behind a proxy/load balancer or a single Nginx on the box; get HTTPS (ACM cert or a simple certbot). Set `ALLOWED_HOSTS`, `SECURE_*` settings, and the SPA's API base URL.
7. **Smoke test the same checks** you used locally: `/api/health/`, login, create ticket, run an export (lands in S3), trigger an email (arrives via SES to a verified address).

> **Next:** once the app is live, `references/phase-07b-edge-cdn.md` puts a CDN in front (fast static delivery + private-file signing) and locks the origin down so nobody can bypass the edge. Do it right after this phase — it builds on the same S3 bucket and app origin.

## Verify

- The public URL serves the app over HTTPS; `/api/health/` reports db+redis healthy against the cloud services.
- An export writes to the **S3 bucket** and the signed link downloads.
- A test email is delivered via **SES** to a verified address.
- No secret appears in any image layer or in git (spot-check the Dockerfile and history); the app reaches S3/SES via the **IAM role**, not static keys.
- The billing dashboard shows near-zero spend; you can `terraform destroy`/tear down cleanly.

## Best practices to call out

- **Immutable, SHA-tagged images**; never deploy `:latest` to anything you care about.
- **Least-privilege IAM roles**, no long-lived access keys on the box.
- **Secrets in a secret store**, injected at runtime.
- **Backups on** for RDS (free-tier includes some) and know your restore story.
- **Run migrations as a discrete, logged step**, not implicitly on boot in multi-replica setups.
- **Tear down when idle.** Consider capturing the whole setup as **Infrastructure-as-Code** (Terraform/CDK) so you can create+destroy repeatably — a great stretch goal that makes the free tier safe.
- **Harden the images** (non-root user, minimal base) before they face the internet.

## Canonical docs

- AWS Free Tier: https://aws.amazon.com/free/ · Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- ECR: https://docs.aws.amazon.com/AmazonECR/latest/userguide/ · ECS/Fargate: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/
- RDS: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/ · S3: https://docs.aws.amazon.com/AmazonS3/latest/userguide/
- SES: https://docs.aws.amazon.com/ses/latest/dg/ · SES sandbox: https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html
- IAM roles: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html · SSM Parameter Store: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html
- Terraform (optional IaC): https://developer.hashicorp.com/terraform/docs

## Common issues (lab copilot fodder)

- **Surprise bill** → almost always a NAT Gateway, an idle load balancer, or an oversized RDS; the budget alarm you set in step 1 catches it. Prefer public subnets + one small instance for a lab.
- **App can't reach RDS** → security group doesn't allow the app's SG on 5432, or it's in a different subnet/AZ; teach security groups as virtual firewalls.
- **SES won't send** → still in sandbox / unverified recipient; verify identities or request production access.
- **`DisallowedHost` / CSRF-origin errors** → `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` not set for the real domain.
- **S3 AccessDenied** → the IAM role lacks the bucket action, or you're still using MinIO's path-style/endpoint settings; switch to real S3 config.
