# Manual compliance flow tests

Run these in a **fresh incognito/private** browser to confirm no data collection before consent.

## 1. GDPR consent flow

1. Open the site in a new incognito window.
2. **Before clicking anything**: Open DevTools → Application → Cookies / Local Storage. Confirm there is **no** `nl_consent_v1` (or similar) and no analytics cookies (e.g. `_ga`).
3. Confirm the consent banner is visible.
4. Click **Accept all** (or equivalent).
5. Check again: `nl_consent_v1` should now exist with `analytics: true` (and optionally `advertising: true`). GA4 script may load only after this.
6. **Expected**: No GA4/GTM requests, no analytics cookies, and no ad personalization until the user accepts.

## 2. CCPA opt-out flow

1. Fresh incognito; go to the site.
2. Accept cookies (so the site is functional).
3. Find and open the **Do Not Sell or Share My Personal Information** (or **Do Not Sell**) link (often in footer or privacy page).
4. On the CCPA page, enable **opt-out** (e.g. toggle or button).
5. Check `localStorage`: expect something like `nl_ccpa_opt_out === 'true'`.
6. **Expected**: Subsequent ad requests use NPA (non-personalized) and/or `restrictDataProcessing`; no sale/sharing of personal info for ads.

## 3. Under-13 age gate (COPPA)

1. If the site has registration/onboarding, look for an age or birthdate field.
2. Enter a birth date that makes the user under 13 (or select “Under 13” if offered).
3. **Expected**: Registration or personalized features are blocked; no advertising consent for minors; no collection of personal info from under-13 users.

## Quick checklist

- [ ] No analytics cookies or GA/GTM requests before consent.
- [ ] Consent banner visible on first visit (incognito).
- [ ] After “Accept”, consent stored (e.g. `nl_consent_v1`) and analytics can load.
- [ ] CCPA opt-out sets `nl_ccpa_opt_out` and ads become non-personalized.
- [ ] Under-13 path blocks registration / does not grant advertising consent.

If any step fails, note the URL, browser, and what you saw (cookies, network requests) for debugging.
