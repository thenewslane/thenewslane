-- Migration 001: Add fact_check column and 'draft' status for fact-checking pipeline
-- Run in Supabase SQL Editor. Safe to run (IF NOT EXISTS / IF EXISTS).

-- 1. Add fact_check column. Fact-check agent sets to 'yes' after verification.
ALTER TABLE public.trending_topics
  ADD COLUMN IF NOT EXISTS fact_check TEXT NOT NULL DEFAULT 'no'
  CHECK (fact_check IN ('yes', 'no'));

-- 2. Allow 'draft' status. (If your DB uses a different constraint name, run the inner ALTER manually.)
ALTER TABLE public.trending_topics DROP CONSTRAINT IF EXISTS trending_topics_status_check;
ALTER TABLE public.trending_topics
  ADD CONSTRAINT trending_topics_status_check
  CHECK (status IN (
    'pending', 'predicting', 'brand_checking', 'generating',
    'draft', 'published', 'rejected'
  ));

-- Backfill: mark existing published rows as fact-checked so they stay visible on the site
UPDATE public.trending_topics SET fact_check = 'yes' WHERE status = 'published';
