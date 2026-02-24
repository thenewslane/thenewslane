# Performance audit summary

## 1. Lighthouse CI

### Setup

- **Install (global):** `npm install -g @lhci/cli`
- **Or use project:** `@lhci/cli` is a devDependency in `apps/web`; use `npx lhci` from `apps/web`.

### Configuration

- **`apps/web/lighthouserc.js`** — LHCI config that:
  - Tests **3 article pages** when `LHCI_URLS` is set (comma-separated list).
  - Otherwise tests **one URL** (`LHCI_BASE_URL` or `http://localhost:3000`).
  - With server: `startServerCommand: 'npm run start'` (set `LHCI_SKIP_SERVER=1` when the server is already running).
  - Asserts: Performance ≥ 0.5, Accessibility / Best Practices / SEO ≥ 0.8 (warn only).
  - Uploads to temporary public storage so you can view the report.

### Running

**Option A — Full run (3 article pages from sitemap):**

```bash
cd apps/web
npm run lighthouse:ci
```

This script (from `scripts/run-lighthouse-ci.js`):

1. Runs `npm run build` in `apps/web`.
2. Starts `npm run start` in the background.
3. Fetches `/sitemap.xml`, picks up to 3 article URLs.
4. Runs `lhci autorun` with those URLs and `LHCI_SKIP_SERVER=1`.

**Option B — Quick single-URL run:**

```bash
cd apps/web
npm run build   # ensure build exists
lhci autorun    # or: npx lhci autorun
```

Lighthouse will start the server, then run against `http://localhost:3000`.

### Reading scores

After `lhci autorun`, the CLI prints a link to the report. Open it to see:

- **Performance** (LCP, INP, CLS, TBT, etc.)
- **Accessibility**
- **Best Practices**
- **SEO**

Target: **Performance ≥ 90**, others ≥ 90. If Performance &lt; 90, use the report to fix:

- **LCP &gt; 2.5s** — Prioritize LCP element (e.g. hero image with `priority`, preload, or faster server/CDN).
- **CLS &gt; 0.1** — Reserve space (width/height or aspect-ratio) for images and dynamic content.
- **INP &gt; 200ms** — Optimize or defer heavy event handlers; reduce main-thread work.
- **TBT &gt; 200ms** — Split large JS (dynamic import, lighter libs), reduce long tasks.

---

## 2. Performance-related changes in the app

- **Article hero image (LCP):** Already uses Next.js `<Image priority>`. Wrapper has explicit `width: 100%`, `aspectRatio: 16/9`, `minHeight: 200` to reduce CLS.
- **Below-the-fold images:** TopicCard thumbnails use `loading="lazy"`.
- **Fonts:** Inter loaded with `display=swap`; CSP allows `https://fonts.gstatic.com` for font files.
- **Images:** Next.js config uses `formats: ['image/webp', 'image/avif']` for smaller responses.

---

## 3. Bundle analysis

### Run

```bash
cd apps/web
ANALYZE=true npm run build
```

With Supabase env vars set, the build completes and opens (or writes) the report under  
`apps/web/.next/analyze/` (e.g. `client.html`, `nodejs.html`).

If the build fails during static generation (e.g. missing Supabase), the **analyzer still runs** after the compile step; check `.next/analyze/` for the report.

### What to do

- Open `client.html` and look for **chunks or packages &gt; 100kb**.
- Prefer **dynamic imports** for heavy, below-the-fold features (e.g. `next/dynamic` for modals, charts).
- Replace large dependencies with lighter alternatives where possible.

---

## 4. Sitemap and robots.txt

### Automated test

```bash
node scripts/test-robots-sitemap.js [BASE_URL]
# e.g. node scripts/test-robots-sitemap.js https://thenewslane.com
```

Checks:

- **robots.txt** — HTTP 200, contains `User-agent: *` and a `Sitemap:` URL.
- **sitemap.xml** — HTTP 200, valid `<urlset>`, counts `<loc>` entries.

### Sitemap 404 check

```bash
node scripts/test-sitemap.js [BASE_URL]
```

Reports total URLs, most recent article date, and any URL that returns 404.

---

## 5. Compliance flows (manual)

See **`docs/compliance-test-manual.md`** for step-by-step checks in a **fresh incognito** session:

1. **GDPR** — No analytics/ad cookies or GA/GTM requests before consent; banner visible; after “Accept”, consent stored and analytics may load.
2. **CCPA** — Do Not Sell/Share flow sets opt-out (e.g. `nl_ccpa_opt_out`); ads become non-personalized.
3. **Under-13 (COPPA)** — Under-13 path blocks registration / does not grant advertising consent; no collection of personal info from minors.

Confirm **no data collection occurs before consent** (cookies and network tab).

---

## Summary

| Item                         | Status / action |
|-----------------------------|-----------------|
| Lighthouse CI install/config | Done — `apps/web/lighthouserc.js` + `scripts/run-lighthouse-ci.js` |
| Run LHCI (3 article pages)  | `cd apps/web && npm run lighthouse:ci` (needs build + env) |
| Performance fixes (LCP/CLS) | Hero image priority + explicit dimensions; lazy below-fold |
| Bundle analyzer             | `ANALYZE=true npm run build`; reports in `.next/analyze/` |
| Sitemap/robots test         | `node scripts/test-robots-sitemap.js [BASE_URL]` |
| Sitemap 404 test            | `node scripts/test-sitemap.js [BASE_URL]` |
| Compliance (GDPR/CCPA/&lt;13) | Manual steps in `docs/compliance-test-manual.md` |

**Remaining (cannot auto-fix here):**

- **Lighthouse scores** — Must run against your deployed or local site with real data; fix any Performance &lt; 90 using the report (LCP, CLS, INP, TBT).
- **Bundle size** — Review `.next/analyze/client.html` and replace or code-split any package &gt; 100kb.
- **Compliance** — Manually verify in incognito that there is no data collection before consent and that CCPA/under-13 flows behave as required.
