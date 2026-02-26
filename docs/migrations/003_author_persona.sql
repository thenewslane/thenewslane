-- Migration 003: Add author persona columns to trending_topics
-- Run via Supabase Dashboard → SQL Editor (or supabase db push)

BEGIN;

ALTER TABLE public.trending_topics
  ADD COLUMN IF NOT EXISTS author_name      TEXT,
  ADD COLUMN IF NOT EXISTS author_honorific TEXT;

-- Backfill existing rows with the publication default
-- (matches historic AUTHOR_NAME env var behaviour)
UPDATE public.trending_topics
  SET author_name = 'theNewslane Editorial'
  WHERE author_name IS NULL;

CREATE INDEX IF NOT EXISTS idx_trending_topics_author_name
  ON public.trending_topics (author_name);

COMMIT;
