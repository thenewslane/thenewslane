# GAM & AdSense — Step-by-step walkthrough

This guide walks you through everything needed for Google Ad Manager (GAM) and AdSense on theNewslane: accounts, ads.txt, ad units, optional API access, and AdSense auto ads.

---

## Part 1: Google AdSense

### Step 1.1 — Sign up / use existing AdSense

1. Go to [Google AdSense](https://www.google.com/adsense).
2. Sign in with the Google account you want to use for ad revenue.
3. If you’re new: **Add site** and enter your domain (e.g. `thenewslane.com`). Complete verification (add the code or use the DNS record AdSense gives you).
4. Once the site is approved, note:
   - **Publisher ID:** AdSense → **Account** → **Settings** → “Your publisher ID” (format `pub-XXXXXXXXXXXXXXXX`, 16 digits).

### Step 1.2 — Get your ads.txt certification (for ads.txt)

1. In AdSense go to **Account** → **Settings** (or **Sites** → your site → **ads.txt**).
2. Find the line that looks like:  
   `google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0`  
   The last value is your **certification (authorization) ID**.
3. Copy your **publisher ID** and **certification ID**; you’ll put them in your site’s `ads.txt` and `app-ads.txt`.

### Step 1.3 — Enable Auto ads (optional)

1. In AdSense go to **Ads** → **Auto ads**.
2. Select your site and turn **Auto ads** on.
3. In your app, set the env var so the script loads:
   - `NEXT_PUBLIC_ADSENSE_CLIENT_ID=ca-pub-XXXXXXXXXXXXXXXX`  
   (Use your real publisher ID; `ca-pub-` is the standard prefix for the client parameter.)

---

## Part 2: Google Ad Manager (GAM)

### Step 2.1 — Use or create a GAM network

1. Go to [Google Ad Manager](https://admanager.google.com).
2. Sign in with the same (or desired) Google account.
3. If you don’t have a network: create one (e.g. “theNewslane”); this gives you a **network code** (e.g. `23173092177`).
4. Note your **network code** (shown in the UI, often in the URL or under Admin → Global settings).

### Step 2.2 — Link AdSense to GAM (if you use both)

1. In GAM go to **Admin** → **Global settings**.
2. Under “AdSense association” (or linked accounts), link your AdSense account so GAM can use AdSense demand.
3. This allows your GAM ad units to also show AdSense backfill.

### Step 2.3 — Get GAM ads.txt certification ID

1. In GAM go to **Admin** → **Global settings**.
2. Find the **ads.txt** section.
3. Copy the certification (authorization) ID Google shows for your seller account (often similar format to AdSense, e.g. `f08c47fec0942fa0`).
4. You’ll use: **network code** + **certification ID** in `ads.txt` and `app-ads.txt`.

### Step 2.4 — Create the four ad units (manual)

The site expects these four ad units. Create them in GAM so paths and sizes match the code.

1. In GAM go to **Admin** → **Ad units**.
2. Select the root (network) ad unit.
3. For each row in the table below, click **New ad unit** → **Ad unit** and set:

| Ad unit name         | Path (code)        | Sizes              |
|----------------------|--------------------|---------------------|
| Header Leaderboard   | `header_leaderboard` | 728×90, 970×90     |
| Article Rectangle    | `article_rectangle`  | 300×250, 300×600   |
| In Content           | `in_content`         | 300×250, 336×280   |
| Mobile Anchor        | `mobile_anchor`       | 320×50, 320×100    |

4. **Path** = the “Ad unit code” (e.g. `in_content`). The full path in requests will be `/{network_code}/{path}` (e.g. `/23173092177/in_content`).
5. Save each unit. Front-end config is in `apps/web/config/ad-units.ts`; it already uses network code `23173092177`. If your network code is different, update that file and any env that might override it.

---

## Part 3: ads.txt and app-ads.txt on your site

### Step 3.1 — What to put in the files

The repo has placeholders in:

- `apps/web/public/ads.txt`
- `apps/web/public/app-ads.txt`

Each line format:  
`domain, publisher_id, relationship_type, certification_id`

Replace placeholders with your real values.

### Step 3.2 — ads.txt (web)

1. Open `apps/web/public/ads.txt`.
2. **AdSense line:**  
   Replace `pub-0000000000000000` with your AdSense publisher ID (e.g. `pub-1234567890123456`).  
   Replace the last value with your **AdSense** certification ID from Step 1.2.
3. **GAM line:**  
   Keep `google.com` and `23173092177` (or your network code).  
   Replace the last value with your **GAM** certification ID from Step 2.3.
4. Save. The file is served at `https://yourdomain.com/ads.txt`.

### Step 3.3 — app-ads.txt (in-app)

1. Open `apps/web/public/app-ads.txt`.
2. Use the **same** lines as in `ads.txt` (same publisher IDs and certification IDs).
3. Save. Served at `https://yourdomain.com/app-ads.txt`.

### Step 3.4 — Verify

1. After deploy, open `https://yourdomain.com/ads.txt` and `https://yourdomain.com/app-ads.txt` and confirm the lines are correct.
2. In AdSense: **Sites** → your site → **ads.txt** — use “Check” / “Validate” if available.
3. In GAM: **Admin** → **Global settings** → **ads.txt** — use the validator link Google provides.

---

## Part 4: GAM API (optional — create ad units / orders / line items)

Use this only if you want to create ad units (or later orders/line items) via API instead of the UI.

### Step 4.1 — Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Create or select a project (e.g. “theNewslane”).
3. **APIs & Services** → **Enable API** → search for **“Google Ad Manager API”** → Enable.

### Step 4.2 — Service account for GAM

1. In Cloud Console go to **IAM & Admin** → **Service accounts**.
2. **Create service account** — name it (e.g. “gam-ad-units”), no roles needed in GCP.
3. Create a **JSON key** and download it; keep it secret (e.g. `gam-service-account.json`).
4. Note the service account **email** (e.g. `gam-ad-units@project-id.iam.gserviceaccount.com`).

### Step 4.3 — Grant the service account access in GAM

1. In GAM go to **Admin** → **Access & authorization** (or **Users**) and add a **user**.
2. Enter the **service account email** from Step 4.2.
3. Assign a role that can create/edit ad units (and orders/line items if you’ll use the SOAP API later), e.g. “Network administrator” or a custom role with the right permissions.
4. Save.

### Step 4.4 — Create ad units via script (this repo)

1. Set credentials:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/gam-service-account.json
   export GAM_NETWORK_CODE=23173092177
   ```
2. From repo root (or `apps/web`):
   ```bash
   cd apps/web
   node scripts/create-gam-ad-units.js
   ```
3. If the script succeeds, the four ad units are created. If it fails (e.g. API not enabled or permissions), create them manually (Part 2, Step 2.4).

### Step 4.5 — Orders and line items (SOAP API)

- **Ad units:** Use the script above (REST) or the GAM UI.
- **Orders and line items:** The current Ad Manager **REST Beta** doesn’t expose full create for orders/line items. Use either:
  - **GAM UI:** **Delivery** → **Orders** → create order → add line items; or
  - **Ad Manager SOAP API:** [OrderService](https://developers.google.com/ad-manager/api/reference/latest/OrderService), [LineItemService](https://developers.google.com/ad-manager/api/reference/latest/LineItemService) with the same scope: `https://www.googleapis.com/auth/dfp`, and the same service account (or OAuth2) that has access in GAM.

Details and a short reference table are in `docs/GAM_AD_UNITS_SETUP.md`.

---

## Checklist

- [ ] AdSense: Publisher ID and certification ID noted.
- [ ] AdSense: Auto ads enabled (optional); `NEXT_PUBLIC_ADSENSE_CLIENT_ID` set in app env.
- [ ] GAM: Network code and ads.txt certification ID noted.
- [ ] GAM: Four ad units created (manual or via script) with correct paths and sizes.
- [ ] `ads.txt` and `app-ads.txt` updated with real IDs and live at `https://yourdomain.com/ads.txt` and `.../app-ads.txt`.
- [ ] (Optional) GAM API: Service account created, GAM access granted, ad-units script run; orders/line items via UI or SOAP if needed.

After this, the site’s existing GAM slots (see `apps/web/config/ad-units.ts` and the ad components) will request the correct units, and AdSense auto ads will load when the client ID is set and the user has consented.
