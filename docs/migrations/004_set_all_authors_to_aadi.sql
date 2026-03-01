-- Migration 004: Set all author names and bylines to Aadi
-- Run via Supabase Dashboard → SQL Editor (or run scripts/update_all_authors_to_aadi.py)

BEGIN;

UPDATE public.trending_topics
  SET author_name     = 'Aadi',
      author_honorific = NULL
  WHERE author_name IS DISTINCT FROM 'Aadi'
     OR author_honorific IS NOT NULL;

COMMIT;
