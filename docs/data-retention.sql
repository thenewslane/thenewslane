-- =============================================================================
-- Data Retention Jobs (pg_cron)
--
-- Supabase has pg_cron enabled by default. Run these statements in the
-- Supabase SQL Editor or via psql to register the scheduled jobs.
--
-- Verify registered jobs with:
--   SELECT * FROM cron.job;
--
-- Remove a job with:
--   SELECT cron.unschedule('job-name');
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Delete raw_signals older than 90 days
--    Schedule: every Sunday at 03:00 UTC
-- -----------------------------------------------------------------------------
SELECT cron.schedule(
  'delete-raw-signals',
  '0 3 * * 0',
  $$
    DELETE FROM public.raw_signals
    WHERE created_at < NOW() - INTERVAL '90 days';
  $$
);


-- -----------------------------------------------------------------------------
-- 2. Delete viral_predictions older than 180 days
--    Schedule: every Sunday at 03:30 UTC
-- -----------------------------------------------------------------------------
SELECT cron.schedule(
  'delete-viral-predictions',
  '30 3 * * 0',
  $$
    DELETE FROM public.viral_predictions
    WHERE created_at < NOW() - INTERVAL '180 days';
  $$
);


-- -----------------------------------------------------------------------------
-- 3. Anonymize user_submissions older than 2 years
--    Nulls URL and description; replaces title with '[anonymized]'.
--    Schedule: 1st of every month at 04:00 UTC
-- -----------------------------------------------------------------------------
SELECT cron.schedule(
  'anonymize-user-submissions',
  '0 4 1 * *',
  $$
    UPDATE public.user_submissions
    SET
      title       = '[anonymized]',
      url         = NULL,
      description = NULL
    WHERE
      created_at < NOW() - INTERVAL '2 years'
      AND title != '[anonymized]';
  $$
);
