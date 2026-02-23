# Compliance Checklist — GDPR, CCPA, COPPA

This document lists every compliance requirement, the file(s) where it is implemented, and the test command or manual step to verify it.

---

## GDPR (EU General Data Protection Regulation)

| # | Requirement | Status | Implementation file(s) | Test / Verification |
|---|-------------|--------|------------------------|---------------------|
| G1 | Consent banner displayed before any tracking | ✅ | `apps/web/app/providers.tsx` → `ConsentBanner` rendered when no consent stored | Load site in incognito — banner must appear before any GA4/GPT tag fires |
| G2 | Consent stored in localStorage and respected across sessions | ✅ | `apps/web/app/providers.tsx` (`nl_consent_v1` key) | Accept consent, reload page — banner must not reappear |
| G3 | GA4 fires only when `consent.analytics = true` | ✅ | `apps/web/components/AnalyticsScripts.tsx` — GA4 block gated on `consent.analytics` | Deny analytics consent — open DevTools Network tab, confirm no requests to `google-analytics.com` |
| G4 | GPT always loads but uses NPA(1) when `consent.advertising = false` | ✅ | `apps/web/components/AnalyticsScripts.tsx` — `setRequestNonPersonalizedAds(useNpa ? 1 : 0)` | Deny advertising consent — confirm GPT loads (`window.googletag` exists) and NPA mode is active via `googletag.pubads().isRequestNonPersonalized()` in DevTools console |
| G5 | Ad slots show placeholder (no real ad) without advertising consent | ✅ | `packages/ui/web/AdSlot.tsx`, `apps/web/components/ads/AdSlot.tsx` — placeholder div rendered when `!adsAllowed` | Deny advertising — confirm ad slot shows "Advertisement" placeholder |
| G6 | Right to withdraw consent (cookie settings link) | ✅ | `apps/web/components/Footer.tsx` → "Cookie Settings" link calls `resetConsent()` | Click "Cookie Settings" in footer — banner must reappear |
| G7 | Data retention — raw_signals deleted after 90 days | ✅ | `docs/data-retention.sql` — weekly `DELETE` via `pg_cron` | Run `SELECT * FROM cron.job WHERE jobname = 'delete-raw-signals';` in Supabase SQL Editor |
| G8 | Data retention — viral_predictions deleted after 180 days | ✅ | `docs/data-retention.sql` — weekly `DELETE` via `pg_cron` | Run `SELECT * FROM cron.job WHERE jobname = 'delete-viral-predictions';` |
| G9 | Data retention — user_submissions anonymized after 2 years | ✅ | `docs/data-retention.sql` — monthly `UPDATE` via `pg_cron` | Run `SELECT * FROM cron.job WHERE jobname = 'anonymize-user-submissions';` |
| G10 | Canonical URLs on all pages | ✅ | `apps/web/app/page.tsx`, `apps/web/app/trending/[slug]/page.tsx` — `alternates.canonical` in Next.js metadata | View page source — confirm `<link rel="canonical">` tag present |

---

## CCPA (California Consumer Privacy Act)

| # | Requirement | Status | Implementation file(s) | Test / Verification |
|---|-------------|--------|------------------------|---------------------|
| C1 | "Do Not Sell My Personal Information" link | ✅ | `apps/web/components/Footer.tsx` → link to `/do-not-sell` | Confirm link visible in footer on all pages |
| C2 | Do-Not-Sell page sets `nl_ccpa_opt_out = true` in localStorage | ✅ | `apps/web/app/do-not-sell/page.tsx` | Visit `/do-not-sell`, opt out — `localStorage.getItem('nl_ccpa_opt_out')` must equal `'true'` |
| C3 | GPT uses `restrictDataProcessing: true` when CCPA opted out | ✅ | `apps/web/components/AnalyticsScripts.tsx` — `setPrivacySettingsForAll({restrictDataProcessing:true})` when `ccpaOptOut` | After CCPA opt-out, reload — confirm `setPrivacySettingsForAll` called (check DevTools console for GPT logs) |
| C4 | Ad Manager NPA mode when CCPA opted out | ✅ | `apps/web/components/AnalyticsScripts.tsx` — `useNpa = true` when `ccpaOptOut` | After opt-out, confirm `setRequestNonPersonalizedAds(1)` via DevTools |
| C5 | CCPA opt-out persisted to `user_profiles.ccpa_opt_out` for authenticated users | ✅ | `apps/web/app/do-not-sell/page.tsx` → Supabase update | Log in, opt out — query `SELECT ccpa_opt_out FROM user_profiles WHERE id = '...'` |

---

## COPPA (Children's Online Privacy Protection Act)

| # | Requirement | Status | Implementation file(s) | Test / Verification |
|---|-------------|--------|------------------------|---------------------|
| P1 | Age gate on registration — prevents under-13 sign-up | ✅ | `apps/web/app/register/page.tsx` — date of birth required; under-13 blocked | Attempt to register with DOB ≤ 13 years ago — must be blocked with error message |
| P2 | `is_minor` flag set in `user_profiles` for ages 13–17 | ✅ | Registration flow — `is_minor = true` when 13 ≤ age < 18 | After registering with age 15, query `user_profiles.is_minor` — must be `true` |
| P3 | `isMinor` fetched from profile and exposed in `ConsentContext` | ✅ | `apps/web/app/providers.tsx` → fetches `user_profiles.is_minor` on auth | Log in as minor user — `useConsent().isMinor` must be `true` in React DevTools |
| P4 | `advertising` consent forced to `false` for minors | ✅ | `apps/web/app/providers.tsx` → `setConsent` overrides advertising to `false` when `isMinor` | Log in as minor — inspect `ConsentContext.consent.advertising` — must be `false` |
| P5 | Ad slots show placeholder for minors (no real ad displayed) | ✅ | `packages/ui/web/AdSlot.tsx` + `apps/web/components/ads/AdSlot.tsx` — `isMinor` prop forces placeholder | Log in as minor — all ad slots must show "Advertisement" placeholder |
| P6 | GPT NPA mode for minors | ✅ | `apps/web/components/AnalyticsScripts.tsx` — `useNpa = isMinor || …` | Log in as minor — confirm `setRequestNonPersonalizedAds(1)` in GPT init script |

---

## Google Ad Manager (GAM) Compliance

| # | Requirement | Status | Implementation file(s) | Test / Verification |
|---|-------------|--------|------------------------|---------------------|
| A1 | GPT script loaded asynchronously | ✅ | `apps/web/components/AnalyticsScripts.tsx` — `strategy="afterInteractive"` | Confirm GPT script is not render-blocking (Lighthouse audit) |
| A2 | Ad slots only displayed after ConsentBanner interaction | ✅ | `apps/web/components/ads/AdSlot.tsx` — checks `consent !== null` via `useConsent()` | On first load (no consent), ad slots must show placeholder only |
| A3 | Slot destroyed on component unmount (no memory leaks) | ✅ | `apps/web/components/ads/AdSlot.tsx` — `useEffect` return calls `googletag.destroySlots()` | Navigate between article pages — confirm no duplicate slot errors in browser console |
| A4 | IAB category targeting passed to GAM for contextual relevance | ✅ | `apps/web/app/trending/[slug]/page.tsx` — `targeting={{ iab_categories: topic.iab_tags }}` | Inspect GPT slot in DevTools — confirm `iab_categories` key-value in targeting |
| A5 | Network code `23173092177` used in all ad unit paths | ✅ | `apps/web/config/ad-units.ts` | Grep codebase: `rg "23173092177" apps/web/` |

---

## How to Run Automated Tests

```bash
# Schema markup validation (fetches 3 article pages and checks JSON-LD)
node scripts/test-schema.js https://thenewslane.com

# Sitemap health check (total URLs, most recent date, 404 spot-check)
node scripts/test-sitemap.js https://thenewslane.com
```

---

## Manual Audit Steps

1. **Consent banner flow:**
   Open site in a fresh incognito window. Confirm the ConsentBanner appears immediately, blocking all tracking until a choice is made.

2. **Analytics gating:**
   In DevTools Network tab, filter by `google-analytics` or `gtag`. Deny analytics consent — zero requests should appear. Accept — requests should fire within seconds.

3. **GPT NPA verification:**
   After denying advertising consent, open the browser console and run:
   ```js
   googletag.pubads().isRequestNonPersonalized()
   // Should return true (1)
   ```

4. **CCPA opt-out:**
   Navigate to `/do-not-sell`, click opt out. Run in console:
   ```js
   localStorage.getItem('nl_ccpa_opt_out') // "true"
   ```
   Reload the page and re-check the GPT state above.

5. **Minor account ad gating:**
   Create a test account with date of birth showing age 15. After login, inspect:
   ```js
   // In React DevTools (Providers component state)
   isMinor === true
   consent.advertising === false
   ```
   Confirm all ad slots show the "Advertisement" placeholder.
