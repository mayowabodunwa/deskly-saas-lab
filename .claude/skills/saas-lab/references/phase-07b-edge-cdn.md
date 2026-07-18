# Phase 7b — Edge, CDN & origin protection

**Goal:** put a CDN in front of Deskly so static assets are served fast from the edge, serve private files (exports) safely through it, get the caching rules right, and then **lock the origin down** so nobody can bypass the edge by hitting the backend directly.

**Done when:** the SPA loads from CDN edge caches with correct cache headers, exports are still private (signed, never publicly cached), and the origin (S3 bucket and/or the Django app) refuses any request that didn't come through the CDN.

> Do this right after Phase 7 — it builds on the same S3 bucket and EC2/ALB you provisioned. It stays free: CloudFront and Cloudflare both have standing free tiers (verify current quotas, they change). Locally you don't need a real CDN — your Nginx reverse proxy plays the edge so the concepts are real before the cloud.

## Concepts to teach here

- **What a CDN is and why.** A content delivery network is a fleet of edge servers worldwide that cache copies of your content close to users. First request fills the cache from your **origin** (S3 or your app); subsequent nearby requests are served from the edge — faster for users, far less load on your origin. It also absorbs traffic spikes and DDoS.
- **Cache the right things, never the wrong things.** In a *multi-tenant* app this is a safety issue, not just performance:
  - **SPA build** (Vite's hashed JS/CSS/images) → perfect to cache aggressively; it's identical for everyone and immutable.
  - **Exports / any per-tenant file** → private; may pass through the CDN but only with signed access and **no shared caching**.
  - **Authenticated API responses** → **never cache at a shared edge.** Caching one tenant's data at the edge and serving it to another is a cross-tenant leak. This is the Phase 1 isolation rule, now at the network layer.
- **Why hashed filenames unlock caching.** Because Vite names files `app.9f2a1c.js`, the content at a URL never changes — so you can cache it "forever." A deploy produces new hashes and a new `index.html`; the trick is caching assets forever but **never** caching `index.html`, so a deploy goes live instantly.
- **Origin protection.** Once a CDN fronts you, the origin is still on the internet. If people can hit it directly they bypass your caching, WAF, rate limits, and (for S3) your signed-URL protection. So you force *all* traffic through the CDN.

## Build steps (vertical slice)

### A. Local: practice the caching rules on Nginx (the edge stand-in)
1. Serve the built SPA via Nginx and set cache headers so the pattern is real before the cloud:

```nginx
location /assets/ {                       # hashed, immutable files
    add_header Cache-Control "public, max-age=31536000, immutable";
}
location = /index.html {                   # the pointer to current assets
    add_header Cache-Control "no-cache";   # revalidate every load
}
location /api/ {                           # never cache authenticated API
    add_header Cache-Control "no-store";
    proxy_pass http://backend:8000;
}
```

### B. Cloud: CDN for the SPA (S3 origin + CloudFront)
2. Put the SPA build in an S3 bucket, create a **CloudFront** distribution with that bucket as origin. Carry the same cache rules: long-lived for `/assets/*`, `no-cache` for `index.html`.
3. Add an SPA fallback so client-side routes work: map 403/404 to `/index.html` (a "custom error response" in CloudFront).
4. (Alternative) **Cloudflare** in front of the same origin is the easiest free path and bundles DNS + TLS + basic WAF; or host the static build on **Cloudflare Pages / Netlify / Vercel** for a zero-config CDN. Running S3+CloudFront yourself teaches more plumbing — pick based on how much you want to learn vs. ship.

### C. Cloud: private files through the CDN (exports)
5. Keep exports **private**. Serve them through CloudFront but require **signed URLs / signed cookies** so only an authorized, time-limited request works. This layers on top of the S3 signing from Phase 4 — the edge won't serve the file to an anonymous or expired request, and it's never stored in a shared cache.

### D. Lock down the origin (the second half of your question)

**Case 1 — S3 origin (SPA build, exports).** Use **CloudFront Origin Access Control (OAC)**: turn on "Block all public access" on the bucket, then a bucket policy that allows read **only** from your distribution. (OAC is the current mechanism; it replaced the older "Origin Access Identity/OAI" in old tutorials.)

```json
{
  "Effect": "Allow",
  "Principal": { "Service": "cloudfront.amazonaws.com" },
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::deskly-assets/*",
  "Condition": { "StringEquals": {
    "AWS:SourceArn": "arn:aws:cloudfront::<account-id>:distribution/<dist-id>" } }
}
```

Now the bucket is unreachable except through CloudFront.

**Case 2 — app origin (Django on EC2/ALB).** S3 tricks don't apply; use one or more, weakest → strongest:
- **Shared-secret header.** The CDN injects a custom header on every origin request; the app rejects anything without it. Simple and survives IP changes:
  ```nginx
  if ($http_x_origin_verify != "<long-random-secret>") { return 403; }
  ```
  (Set the header as a CloudFront origin custom header / Cloudflare transform rule, and keep the secret in your secret store.)
- **IP allowlisting.** Restrict the origin's security group to the CDN's ranges. On AWS, reference the managed prefix list `com.amazonaws.global.cloudfront.origin-facing` directly in the security group so it auto-updates as CloudFront ranges change; Cloudflare publishes its ranges similarly.
- **No public origin at all (strongest).** A **Cloudflare Tunnel** (`cloudflared`) or CloudFront **VPC origins / PrivateLink** means the origin has no public IP — the CDN reaches it privately. Nothing to bypass because nothing is exposed.

Recommended lab order: shared-secret header first (5 minutes, immediate), then the managed-prefix-list allowlist, then mention tunnel/VPC-origin as the production endgame.

## Verify

- Load the SPA: `/assets/*` responses show `Cache-Control: ...immutable` and hit the edge cache on a second load (check the CDN cache-hit header); `index.html` is `no-cache`.
- Deploy a change → new hashed assets go live immediately (the fresh `index.html` points at them), old assets still cache fine.
- An export downloads only via its signed URL/cookie; a plain CDN URL without the signature is refused; the file never appears in a shared cache.
- Hit the S3 bucket URL directly → **denied** (OAC + block-public-access). Hit the app's origin URL/IP directly without the secret header → **403**. Through the CDN → works.
- No authenticated `/api/*` response is ever served from cache (`no-store`).

## Best practices to call out

- **Cache immutable assets forever, never cache `index.html` or authed API.** This one rule prevents both stale deploys and cross-tenant cache leaks.
- **Private files use signed URLs/cookies end to end** (S3 signing + CDN signing); never make an export bucket or path public.
- **Always pair a CDN with origin lockdown.** A CDN in front of a wide-open origin is theater — attackers just skip it.
- **Prefer the managed prefix list over hand-copied IP ranges** so allowlists don't rot.
- **Terminate TLS at the edge**, redirect HTTP→HTTPS, and enable the CDN's basic WAF/rate limiting while you're there.
- **Set a cache-busting/invalidation habit** — rely on hashed filenames; reserve cache invalidations for `index.html`-type files.

## Canonical docs

- CloudFront: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/
- Origin Access Control (OAC): https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
- Signed URLs / cookies: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html
- Restrict origin to CloudFront (managed prefix list): https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html
- S3 Block Public Access: https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
- Cloudflare CDN/cache: https://developers.cloudflare.com/cache/ · Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflare Pages: https://developers.cloudflare.com/pages/
- HTTP caching (MDN): https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching

## Common issues (lab copilot fodder)

- **Deploy doesn't show up / users see old app** → `index.html` got cached; set it to `no-cache` and rely on hashed asset names, or invalidate just that path.
- **SPA routes 404 on refresh** → missing the 403/404 → `/index.html` fallback in the distribution.
- **Bucket still publicly reachable** → block-public-access off, or the bucket policy grants `*` instead of only your distribution ARN.
- **Origin reachable directly, bypassing the CDN** → you added a CDN but no origin lockdown; add the secret header or prefix-list allowlist.
- **Signed export URL "works for everyone"** → you signed the S3 URL but left the CDN behavior public; sign at the CDN layer too (or serve exports only via signed CloudFront URLs).
- **CORS errors after moving assets to a CDN domain** → the SPA now loads from a different origin; set the API's CORS/`CSRF_TRUSTED_ORIGINS` accordingly (ties back to Phase 0/2).
