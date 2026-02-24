# Database migrations

Run these in the **Supabase SQL Editor** (or your migration tool) in order.

| Migration | Description |
|-----------|-------------|
| `001_add_fact_check_and_draft.sql` | Adds `fact_check` column (yes/no, default no) and `draft` status to `trending_topics`. Backfills existing published rows with `fact_check=yes`. **Run before deploying the fact-check pipeline.** |

After running a migration, redeploy the agent and web app so they use the new schema.
