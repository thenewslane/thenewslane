# Social Platform API Setup for Make.com

This guide covers how to create the API credentials needed to connect each social platform in Make.com.

---

## Facebook Graph API

### What you need
- A Facebook Developer account
- A Facebook Page (business or creator)
- A Facebook App with `pages_manage_posts` and `pages_read_engagement` permissions

### Steps

1. **Create a Facebook App**
   - Go to [developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App**
   - Select **Business** type
   - Name it (e.g. "theNewslane Distribution")
   - Add the **Pages API** product

2. **Generate a Page Access Token**
   - In your app dashboard, go to **Tools** → **Graph API Explorer**
   - Select your app and your Facebook Page from the dropdowns
   - Add permissions: `pages_manage_posts`, `pages_read_engagement`, `publish_to_groups`
   - Click **Generate Access Token** and follow the OAuth flow
   - Use the **Access Token Debugger** to extend the token to a long-lived token (60 days)
   - For production, use a **System User** token that does not expire

3. **Note these values**
   - `FACEBOOK_PAGE_ID` — found in your Facebook Page settings under **About**
   - `FACEBOOK_PAGE_ACCESS_TOKEN` — the long-lived page token from step 2

4. **Add to Make.com**
   - In Make.com, open any **HTTP module** targeting Graph API
   - Pass `access_token` as a query parameter or header
   - Alternatively, use the native **Facebook Pages** Make.com connection and follow the OAuth flow

---

## Instagram Graph API

### Requirements
- An **Instagram Business** or **Creator** account
- The Instagram account must be **linked to a Facebook Page**
- Same Facebook App as above

### Steps

1. **Link Instagram to your Facebook Page**
   - Facebook Page → **Settings** → **Linked Accounts** → connect your Instagram account

2. **Get your Instagram Business Account ID**
   - Graph API Explorer: `GET /me/accounts` — find your page, then:
   - `GET /{page_id}?fields=instagram_business_account`
   - Copy the `instagram_business_account.id`

3. **Required permissions**
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`

4. **Note this value**
   - `INSTAGRAM_BUSINESS_ACCOUNT_ID` — from step 2

5. **Make.com setup**
   - Use the same `FACEBOOK_PAGE_ACCESS_TOKEN` — it authorises Instagram Graph API too
   - Use the **HTTP** module (not the native Instagram module) for the two-step publish flow

---

## Twitter / X API (OAuth 2.0)

### What you need
- A Twitter Developer account ([developer.twitter.com](https://developer.twitter.com))
- A Project and App in the Developer Portal
- A Twitter account to post from

### Steps

1. **Create a Twitter Developer App**
   - Go to [developer.twitter.com/en/portal](https://developer.twitter.com/en/portal) → **Projects & Apps** → **Create App**
   - Select your existing project or create a new one
   - Enable **OAuth 2.0** under **User authentication settings**
   - Set **App permissions** to **Read and Write**
   - Set **Type of App** to **Web App, Automated App or Bot**
   - Add `https://www.make.com/oauth/cb/twitter2` as a **Callback URI**

2. **Note these values**
   - `TWITTER_CLIENT_ID` — from the **Keys and Tokens** tab (OAuth 2.0 section)
   - `TWITTER_CLIENT_SECRET` — same tab

3. **Connect in Make.com**
   - In Make.com, add a **Twitter (X)** module to your scenario
   - Click **Add connection** → enter your Client ID and Client Secret
   - Authorize the connection by logging in with the Twitter account that will post

4. **Tier / quota notes**
   - Free tier: 1,500 tweets/month, can only read your own tweets
   - Basic tier ($100/month): 3,000 tweets/month — recommended for automation

---

## YouTube Data API v3 (OAuth 2.0)

### What you need
- A Google account with a YouTube channel
- A Google Cloud project

### Steps

1. **Create a Google Cloud project**
   - Go to [console.cloud.google.com](https://console.cloud.google.com)
   - Create a new project (e.g. "theNewslane YouTube")

2. **Enable the YouTube Data API v3**
   - In your project → **APIs & Services** → **Library**
   - Search for **YouTube Data API v3** and enable it

3. **Create OAuth 2.0 credentials**
   - **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URIs: `https://www.make.com/oauth/cb/google`
   - Download the JSON — you will need Client ID and Client Secret

4. **Configure OAuth consent screen**
   - User type: **External** (or Internal if using Google Workspace)
   - Add scopes: `https://www.googleapis.com/auth/youtube.upload`
   - Add your Google account as a test user (until the app is verified)

5. **Connect in Make.com**
   - Add a **YouTube** module → **Add connection**
   - Choose **OAuth 2.0** and enter your Client ID and Client Secret
   - Complete the Google OAuth flow with the account that owns the YouTube channel

6. **Quota notes**
   - Default quota: 10,000 units/day
   - Video upload costs 1,600 units — allows ~6 uploads/day on the free quota
   - Request a quota increase via the Google Cloud Console if needed

---

## Storing Credentials Securely in Make.com

- Use **Make.com Data Stores** or **Environment Variables** (in scenario settings) for access tokens
- Never hard-code tokens directly in HTTP module URLs — use **variables** or **connections**
- Rotate long-lived Facebook tokens every 60 days or switch to System User tokens for zero maintenance
