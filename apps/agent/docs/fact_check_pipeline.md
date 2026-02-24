# Fact-check pipeline

Content is written to the database in **draft** mode and only appears on the site after the fact-check agent has verified it.

## Flow

1. **Publish node** writes each topic with `status=draft`, `fact_check=no`, `published_at=null`.
2. **Fact-check node** runs after publish (and can be run on a schedule):
   - Selects up to 50 rows from `trending_topics` where `fact_check=no`.
   - For each row:
     - **Date verification**: Rejects if `summary` or `article` contain a year &lt; (current_year − 1) or a future year.
     - **LLM cross-check**: Claude Haiku reviews title/summary/article for wrong dates and factual errors.
   - If both pass: sets `fact_check=yes`, `status=published`, `published_at=now`, then triggers Vercel revalidate and IndexNow.
   - If either fails: row stays `fact_check=no` (draft); no revalidate/IndexNow.

3. **Web site** shows only rows with `status=published` **and** `fact_check=yes`.

## Database

- **Migration**: Run `docs/migrations/001_add_fact_check_and_draft.sql` in the Supabase SQL Editor (adds `fact_check` column and `draft` status; backfills existing published rows with `fact_check=yes`).
- **Columns**:
  - `trending_topics.fact_check`: `'yes' | 'no'`, default `'no'`.
  - `trending_topics.status`: includes `'draft'` (content saved but not yet fact-checked).

## Admin

- Dashboard shows **Drafts (pending fact-check)** count and a **Recent drafts** table (last 5 rows with `fact_check=no`).
- **Topics published today** and **Recent Pipeline Runs → Published** use the count of topics that passed fact-check (`fact_checked_topic_ids`).

## Implementation steps (reference)

1. Schema: add `fact_check`, `draft` status.
2. Web: filter all topic queries by `fact_check=yes`.
3. Publish node: write `status=draft`, `fact_check=no`.
4. Fact-check node: query, verify, set `yes` + publish.
5. Graph: add `fact_check` node after `publish`.
6. Date verification in `verify_topic()`.
7. LLM cross-check in `verify_topic()`.
8. Only fact-checked rows get `status=published` (done in step 4).
9. Admin dashboard draft/fact_check view.
10. This doc.
