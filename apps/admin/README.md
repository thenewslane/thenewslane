# Admin — theNewslane

Admin panel for pipeline overview, theme, distribution, predictions, and submissions.

## Running locally

From repo root (or with `pnpm -F admin dev`):

```bash
pnpm --filter admin dev
```

Runs at http://localhost:3001.

## Deploying to Vercel

Set these **Environment Variables** in the Vercel project (Settings → Environment Variables):

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL (auth + anon access) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key (middleware + layout auth) |
| `SUPABASE_URL` | Yes | Same as above; used by server-side data (dashboard, etc.) |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key (bypasses RLS for admin queries) |

If any of these are missing, the app will show a **503** or an on-page error instead of a 500, with instructions to add the variables.

Users must have `user_profiles.is_admin = true` to access the app after signing in.
