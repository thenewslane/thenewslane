# Make.com Automation Setup Instructions

This document provides step-by-step instructions for building the four Make.com distribution scenarios for theNewslane platform.

---

## Prerequisites

- Make.com account with at least the Basic plan (supports Supabase + social API connections)
- Supabase project URL and Service Role API key
- Social platform API credentials (see `docs/social-api-setup.md`)

---

## Scenario 1 — Facebook & Instagram Post

**Trigger:** New published article in Supabase  
**Platforms:** Facebook Page + Instagram Business Account

### Modules (in order)

1. **Supabase — Watch Rows**
   - Connection: your Supabase connection
   - Table: `trending_topics`
   - Filter column: `status`
   - Filter value: `published`
   - Sort by: `published_at` descending
   - Limit: 1 (process one at a time)

2. **Supabase — Get a Row** *(optional — for fresh data)*
   - Table: `trending_topics`
   - Filter: `id` = `{{1.id}}`

3. **HTTP — Make a Request** (Facebook Page Post with image)
   - URL: `https://graph.facebook.com/v19.0/{{FACEBOOK_PAGE_ID}}/photos`
   - Method: `POST`
   - Body type: `application/x-www-form-urlencoded`
   - Fields:
     | Key | Value |
     |-----|-------|
     | `url` | `{{1.thumbnail_url}}` |
     | `caption` | See Facebook caption template below |
     | `access_token` | `{{FACEBOOK_PAGE_ACCESS_TOKEN}}` |

   **Facebook caption template:**
   ```
   {{1.social_copy.facebook | replace: "ARTICLE_LINK_PLACEHOLDER" : "https://thenewslane.com/trending/{{1.slug}}"}}
   ```

4. **HTTP — Make a Request** (Instagram Container Create)
   - URL: `https://graph.facebook.com/v19.0/{{INSTAGRAM_BUSINESS_ACCOUNT_ID}}/media`
   - Method: `POST`
   - Body type: `application/x-www-form-urlencoded`
   - Fields:
     | Key | Value |
     |-----|-------|
     | `image_url` | `{{1.thumbnail_url}}` |
     | `caption` | `{{1.social_copy.instagram}}` |
     | `access_token` | `{{FACEBOOK_PAGE_ACCESS_TOKEN}}` |
   - Store response: save `id` as `instagram_container_id`

5. **HTTP — Make a Request** (Instagram Publish)
   - URL: `https://graph.facebook.com/v19.0/{{INSTAGRAM_BUSINESS_ACCOUNT_ID}}/media_publish`
   - Method: `POST`
   - Body type: `application/x-www-form-urlencoded`
   - Fields:
     | Key | Value |
     |-----|-------|
     | `creation_id` | `{{instagram_container_id}}` |
     | `access_token` | `{{FACEBOOK_PAGE_ACCESS_TOKEN}}` |
   - Store response: save `id` as `instagram_post_id`

6. **Supabase — Update a Row** (log Facebook distribution)
   - Table: `distribution_log`
   - Insert or update by: `topic_id` + `platform`
   - Fields:
     | Column | Value |
     |--------|-------|
     | `topic_id` | `{{1.id}}` |
     | `platform` | `facebook` |
     | `status` | `posted` |
     | `platform_post_id` | `{{4.id}}` *(Facebook photo ID)* |
     | `platform_url` | `https://facebook.com/{{FACEBOOK_PAGE_ID}}_{{4.id}}` |
     | `posted_at` | `{{now}}` |

7. **Supabase — Update a Row** (log Instagram distribution)
   - Same as Step 6 but `platform = instagram`, `platform_post_id = {{instagram_post_id}}`

### Error handling

- On each HTTP module, add an **Error Handler** route:
  - Set `status = failed` and `error_message = {{error.message}}` in `distribution_log`
  - Increment `retry_count` by 1

---

## Scenario 2 — Twitter / X Thread

**Trigger:** Same Supabase Watch Rows (status = published)

### Modules (in order)

1. **Supabase — Watch Rows** *(same as Scenario 1)*

2. **HTTP — Make a Request** (Download thumbnail image)
   - URL: `{{1.thumbnail_url}}`
   - Method: `GET`
   - Response type: `File`
   - Store response as: `thumbnail_file`

3. **Twitter — Create a Tweet** (Tweet 1 — with image)
   - Connection: Twitter OAuth2 connection
   - Text: `{{1.social_copy.twitter | split: "---" | first}}` *(first section of twitter copy)*
   - Media: attach `{{thumbnail_file}}`
   - Store response: save `id` as `tweet1_id`

4. **Twitter — Create a Tweet** (Tweet 2 — reply)
   - Text: `{{1.social_copy.twitter | split: "---" | at: 1}}`
   - In reply to Tweet ID: `{{tweet1_id}}`
   - Store response: save `id` as `tweet2_id`

5. **Twitter — Create a Tweet** (Tweet 3 — final reply with link)
   - Text: `Read more 👉 https://thenewslane.com/trending/{{1.slug}}`
   - In reply to Tweet ID: `{{tweet2_id}}`

6. **Supabase — Update a Row** (log Twitter distribution)
   - Fields:
     | Column | Value |
     |--------|-------|
     | `topic_id` | `{{1.id}}` |
     | `platform` | `twitter` |
     | `status` | `posted` |
     | `platform_post_id` | `{{tweet1_id}}` |
     | `platform_url` | `https://twitter.com/i/web/status/{{tweet1_id}}` |
     | `posted_at` | `{{now}}` |

### Notes

- Twitter's free API tier allows 1,500 tweets/month. Monitor quota carefully.
- If `social_copy.twitter` is formatted as a single string, split it at paragraph breaks (`\n\n`) instead of `---`.

---

## Scenario 3 — YouTube Shorts Upload (Tier 1 Only)

**Trigger:** Supabase Watch Rows filtered to `viral_tier = 1` and status = `published`

### Modules (in order)

1. **Supabase — Watch Rows**
   - Table: `trending_topics`
   - Filter: `status = published` AND `viral_tier = 1`
   - Add a **Filter** module after Step 1:
     - Condition: `{{1.instagram_video_url}}` is not empty

2. **HTTP — Make a Request** (Download Shorts video from Supabase Storage)
   - URL: `{{1.instagram_video_url}}`
   - Method: `GET`
   - Response type: `File`
   - Store response as: `shorts_video_file`

3. **YouTube — Upload a Video**
   - Connection: YouTube OAuth2 connection
   - File: `{{shorts_video_file}}`
   - Title: `{{1.title}} #Shorts`
   - Description:
     ```
     {{1.summary}}
     
     Read the full story 👉 https://thenewslane.com/trending/{{1.slug}}
     
     #news #trending #shorts
     ```
   - Tags: `{{1.iab_tags | join: ","}}` + `news,shorts,trending`
   - Category ID: `25` (News & Politics)
   - Privacy: `public`
   - Made for kids: `No`
   - Store response: save `id` as `youtube_video_id`

4. **Supabase — Update a Row** (log YouTube distribution)
   - Fields:
     | Column | Value |
     |--------|-------|
     | `topic_id` | `{{1.id}}` |
     | `platform` | `youtube` |
     | `status` | `posted` |
     | `platform_post_id` | `{{youtube_video_id}}` |
     | `platform_url` | `https://youtube.com/shorts/{{youtube_video_id}}` |
     | `video_url` | `{{1.instagram_video_url}}` |
     | `posted_at` | `{{now}}` |

---

## Scenario 4 — Retry Failed Distributions

**Trigger:** Scheduled — every 2 hours

### Modules (in order)

1. **Schedule** trigger
   - Interval: Every 2 hours

2. **Supabase — Search Rows**
   - Table: `distribution_log`
   - Filter: `status = failed` AND `retry_count < 3`
   - Order by: `created_at` ascending
   - Limit: 10

3. **Iterator** — iterate over rows from Step 2

4. **Supabase — Get a Row** (fetch the full topic)
   - Table: `trending_topics`
   - Filter: `id = {{3.topic_id}}`

5. **Router** — branch by `platform` value:
   - Branch A: `platform = facebook` → re-run Facebook HTTP module (Step 3 from Scenario 1)
   - Branch B: `platform = instagram` → re-run Instagram HTTP modules (Steps 4–5 from Scenario 1)
   - Branch C: `platform = twitter` → re-run Twitter modules (Steps 3–5 from Scenario 2)
   - Branch D: `platform = youtube` → re-run YouTube upload module (Step 3 from Scenario 3)

6. **Supabase — Update a Row** (update retry status on success)
   - Fields:
     | Column | Value |
     |--------|-------|
     | `id` | `{{3.id}}` |
     | `status` | `posted` |
     | `retry_count` | `{{3.retry_count + 1}}` |
     | `posted_at` | `{{now}}` |

7. **Error handler** on each branch:
   - Update `distribution_log`:
     | Column | Value |
     |--------|-------|
     | `id` | `{{3.id}}` |
     | `status` | `failed` |
     | `retry_count` | `{{3.retry_count + 1}}` |
     | `error_message` | `{{error.message}}` |

---

## Common Settings

### Supabase connection setup
- **Host:** `https://YOUR_PROJECT_REF.supabase.co`
- **API Key:** Use the **Service Role** key (not the anon key) so Make.com can write to `distribution_log`
- **Schema:** `public`

### Rate limiting
- Add a **Sleep** module (1–2 seconds) between platform API calls to avoid hitting rate limits.

### Deduplication
- Use Make.com's built-in **Duplicate Guard** or filter on `{{1.id}}` to prevent processing the same article twice if the scenario runs concurrently.
