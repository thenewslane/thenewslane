# Google Ad Manager — Create ad units automatically

The site uses four ad units with network code **23173092177**. You can create them manually in the GAM UI or use the GAM API to create them in one go.

---

## Option 1: Manual creation in GAM UI

1. Log in to [Google Ad Manager](https://admanager.google.com).
2. Go to **Admin** → **Ad units**.
3. Select the root (network) and click **New ad unit** → **Ad unit**.
4. Create each of these (name and sizes must match the code in `apps/web/config/ad-units.ts`):

| Ad unit name         | Path (append to /23173092177/) | Sizes              |
|----------------------|---------------------------------|--------------------|
| Header Leaderboard   | `header_leaderboard`            | 728×90, 970×90     |
| Article Rectangle    | `article_rectangle`            | 300×250, 300×600   |
| In Content           | `in_content`                    | 300×250, 336×280   |
| Mobile Anchor        | `mobile_anchor`                 | 320×50, 320×100    |

5. Save each. The full unit path in code is `/{network_code}/{path}` (e.g. `/23173092177/in_content`).

---

## Option 2: Create via Google Ad Manager API (Beta)

The [Ad Manager API (Beta)](https://developers.google.com/ad-manager/api/beta) lets you create ad units programmatically.

### Prerequisites

- A Google Cloud project with **Ad Manager API** enabled.
- A service account with access to your Ad Manager network (or OAuth2 credentials).
- Network code: **23173092177**.

### Steps

1. **Enable the API**  
   In [Google Cloud Console](https://console.cloud.google.com) → your project → **APIs & Services** → **Enable** the **Google Ad Manager API**.

2. **Create a service account**  
   **IAM & Admin** → **Service accounts** → **Create**. Grant it access to Ad Manager (or use a user account with OAuth2).

3. **Install the Node client** (from repo root or `apps/web`):
   ```bash
   npm install @google-ads/admanager
   ```

4. **Run the create script** (after setting credentials):
   ```bash
   cd apps/web
   export GAM_NETWORK_CODE=23173092177
   # Set Application Default Credentials (e.g. GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json)
   node scripts/create-gam-ad-units.js
   ```

The script in `apps/web/scripts/create-gam-ad-units.js` creates the four ad units listed above under the root ad unit for your network. If the script fails (e.g. auth or API not enabled), use Option 1 to create the units manually; the site will work as long as the paths and sizes in GAM match `apps/web/config/ad-units.ts`.

---

## Matching the code

The front-end expects these exact paths (see `apps/web/config/ad-units.ts`):

- `/23173092177/header_leaderboard`
- `/23173092177/article_rectangle`
- `/23173092177/in_content`
- `/23173092177/mobile_anchor`

Sizes must include the dimensions listed in the table above. Creating the units in GAM (manually or via API) with these paths and sizes ensures the site’s ad requests are accepted and fill correctly.
