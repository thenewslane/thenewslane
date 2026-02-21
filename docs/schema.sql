-- =============================================================================
-- VIDEO-FIRST AI-CURATED TRENDING NEWS PLATFORM
-- PostgreSQL / Supabase Database Schema
-- =============================================================================
--
-- EXECUTION ORDER (enforced by this file):
--   1. BEGIN transaction
--   2. Extensions
--   3. CREATE TABLE  (all tables, FK-dependency order, no indexes or triggers)
--   4. CREATE FUNCTION  (set_updated_at, then is_admin — after user_profiles exists)
--   5. ALTER TABLE ... ENABLE ROW LEVEL SECURITY  (all tables)
--   6. CREATE POLICY  (all policies — is_admin() is now resolvable)
--   7. CREATE INDEX  (all indexes)
--   8. CREATE TRIGGER  (all triggers — set_updated_at() is now resolvable)
--   9. COMMIT transaction
--
-- Why this order matters:
--   • is_admin() references public.user_profiles in its SQL body.
--     PostgreSQL 14+ resolves SQL-language function bodies at definition time,
--     so the function MUST be created after the table exists.
--   • Triggers reference set_updated_at(), so triggers run last.
--   • Policies reference is_admin(), so policies run after the function.
--   • The transaction guarantees nothing partial is saved on any error.
--
-- The service-role key (Inngest pipeline) bypasses RLS entirely.
-- The anon / authenticated Supabase keys are governed by the policies below.
-- =============================================================================

BEGIN;

-- =============================================================================
-- SECTION 1: EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- =============================================================================
-- SECTION 2: TABLES  (FK-dependency order — no indexes or triggers yet)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- TABLE: categories
-- Reference list of the 10 content verticals used for classification,
-- multiplier look-up, and user preference filtering.
-- ---------------------------------------------------------------------------
CREATE TABLE public.categories (
  id          SERIAL        PRIMARY KEY,
  name        TEXT          NOT NULL UNIQUE,
  slug        TEXT          NOT NULL UNIQUE,
  description TEXT,
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: config
-- Key-value store for tunable runtime configuration: viral prediction weights,
-- tier thresholds, brand safety blocklist, distribution rules, etc.
-- All values are JSONB so they can hold scalars, arrays, or objects.
-- ---------------------------------------------------------------------------
CREATE TABLE public.config (
  id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  key         TEXT          NOT NULL UNIQUE,
  value       JSONB         NOT NULL,
  description TEXT,
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: runs_log
-- One row per Inngest CRON execution (every 4 hours). batch_id is the shared
-- identifier linking raw_signals, trending_topics, viral_predictions, and
-- brand_safety_log to the same pipeline run.
-- ---------------------------------------------------------------------------
CREATE TABLE public.runs_log (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id          TEXT        NOT NULL UNIQUE,
  status            TEXT        NOT NULL DEFAULT 'running'
                                CHECK (status IN ('running', 'completed', 'failed', 'partial')),
  started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at      TIMESTAMPTZ,
  signals_collected INTEGER     NOT NULL DEFAULT 0,
  topics_processed  INTEGER     NOT NULL DEFAULT 0,
  topics_published  INTEGER     NOT NULL DEFAULT 0,
  topics_rejected   INTEGER     NOT NULL DEFAULT 0,
  error_message     TEXT,
  metadata          JSONB,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: user_profiles
-- Extends auth.users with application-level profile data.
-- is_admin = TRUE grants full read access via the is_admin() helper.
-- NOTE: is_admin() is defined AFTER this table (see Section 3).
-- ---------------------------------------------------------------------------
CREATE TABLE public.user_profiles (
  id            UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email         TEXT        NOT NULL UNIQUE,
  display_name  TEXT,
  avatar_url    TEXT,
  is_admin      BOOLEAN     NOT NULL DEFAULT FALSE,
  is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
  last_seen_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: raw_signals
-- Raw, unprocessed data collected from every platform source per batch run.
-- Retained for debugging, audit, and future XGBoost training datasets.
-- ---------------------------------------------------------------------------
CREATE TABLE public.raw_signals (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id        TEXT        NOT NULL REFERENCES public.runs_log(batch_id) ON DELETE CASCADE,
  platform        TEXT        NOT NULL
                              CHECK (platform IN (
                                'twitter', 'reddit', 'youtube',
                                'google_trends', 'google_news'
                              )),
  topic_keyword   TEXT        NOT NULL,
  title           TEXT,
  url             TEXT,
  source_id       TEXT,
  raw_data        JSONB       NOT NULL DEFAULT '{}',
  engagement_data JSONB,
  collected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: trending_topics
-- Central content table. One row per topic that entered the pipeline.
-- Holds the full AI-generated content package, media URLs, viral score,
-- and lifecycle status from pipeline entry through publication.
-- ---------------------------------------------------------------------------
CREATE TABLE public.trending_topics (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id         TEXT        NOT NULL REFERENCES public.runs_log(batch_id) ON DELETE RESTRICT,
  category_id      INTEGER     REFERENCES public.categories(id) ON DELETE SET NULL,

  -- Identity
  title            TEXT        NOT NULL,
  slug             TEXT        NOT NULL UNIQUE,

  -- AI-generated content package (Sonnet 4.5)
  summary          TEXT,
  article          TEXT,
  social_copy      JSONB,                   -- {facebook, instagram, twitter, youtube}
  script           TEXT,                    -- video narration script (ElevenLabs input)
  iab_tags         TEXT[],                  -- IAB content taxonomy tags
  schema_blocks    JSONB,                   -- schema.org structured data blocks

  -- Media assets (Supabase Storage paths or embed URLs)
  thumbnail_url    TEXT,                    -- Flux 1.1 Pro generated image
  video_url        TEXT,                    -- final assembled video
  video_type       TEXT        CHECK (video_type IN (
                                 'kling_generated',
                                 'youtube_embed',
                                 'vimeo_embed'
                               )),

  -- Viral scoring
  viral_tier       INTEGER     CHECK (viral_tier IN (1, 2, 3)),
  viral_score      NUMERIC(5,4),            -- 0.0000 – 1.0000 from viral_predictions

  -- Lifecycle
  status           TEXT        NOT NULL DEFAULT 'pending'
                               CHECK (status IN (
                                 'pending',
                                 'predicting',
                                 'brand_checking',
                                 'generating',
                                 'published',
                                 'rejected'
                               )),
  rejection_reason TEXT,
  published_at     TIMESTAMPTZ,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: viral_predictions
-- Stores every feature score and model output for a topic from the Viral
-- Prediction Agent. Also holds actual_virality_score filled in by the
-- weekly Learning Loop for model weight tuning.
-- ---------------------------------------------------------------------------
CREATE TABLE public.viral_predictions (
  id                         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id                   UUID         NOT NULL REFERENCES public.trending_topics(id) ON DELETE CASCADE,
  batch_id                   TEXT         NOT NULL REFERENCES public.runs_log(batch_id) ON DELETE RESTRICT,

  -- Feature Engineering scores
  cross_platform_score       NUMERIC(5,4) NOT NULL DEFAULT 0,
  velocity_ratio             NUMERIC(7,4) NOT NULL DEFAULT 0,
  acceleration_score         NUMERIC(5,4) NOT NULL DEFAULT 0,
  publication_gap_score      NUMERIC(5,4) NOT NULL DEFAULT 0,
  sentiment_polarity         NUMERIC(5,4) NOT NULL DEFAULT 0,  -- VADER (-1 to 1)
  time_of_day_multiplier     NUMERIC(4,3) NOT NULL DEFAULT 1,
  category_multiplier        NUMERIC(4,3) NOT NULL DEFAULT 1,

  -- Weighted Linear Model output (→ XGBoost after 30 days of labelled data)
  weighted_score             NUMERIC(5,4) NOT NULL DEFAULT 0,

  -- LLM Validator (Claude Haiku — called only for the 40-60% score band)
  llm_validated              BOOLEAN,
  llm_confidence             NUMERIC(5,4),
  llm_reasoning              TEXT,

  -- Decision
  tier_assigned              INTEGER      CHECK (tier_assigned IN (1, 2, 3)),
  rejected                   BOOLEAN      NOT NULL DEFAULT FALSE,
  rejection_reason           TEXT,

  -- Learning loop fields (populated by the weekly async job)
  actual_virality_score      NUMERIC(5,4),
  actual_virality_updated_at TIMESTAMPTZ,

  created_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: brand_safety_log
-- Three-stage brand safety pipeline result per topic:
--   Stage 1 — keyword blocklist (config table)
--   Stage 2 — Llama Guard 3 (toxicity / safety classification)
--   Stage 3 — Claude Haiku brand suitability check
-- Topics only advance to content generation when overall_passed = TRUE.
-- ---------------------------------------------------------------------------
CREATE TABLE public.brand_safety_log (
  id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id                UUID        NOT NULL REFERENCES public.trending_topics(id) ON DELETE CASCADE,
  batch_id                TEXT        NOT NULL REFERENCES public.runs_log(batch_id) ON DELETE RESTRICT,

  -- Stage 1
  keyword_check_passed    BOOLEAN     NOT NULL DEFAULT FALSE,
  blocked_keywords        TEXT[],

  -- Stage 2
  llama_guard_passed      BOOLEAN,
  llama_guard_score       NUMERIC(5,4),
  llama_guard_categories  TEXT[],

  -- Stage 3
  haiku_check_passed      BOOLEAN,
  haiku_brand_score       NUMERIC(5,4),
  haiku_reasoning         TEXT,

  -- Aggregate
  overall_passed          BOOLEAN     NOT NULL DEFAULT FALSE,

  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: distribution_log
-- One row per platform per topic for every social distribution attempt.
-- Tracks post IDs, URLs, retry counts, and engagement snapshots (Learning Loop).
-- ---------------------------------------------------------------------------
CREATE TABLE public.distribution_log (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id              UUID        NOT NULL REFERENCES public.trending_topics(id) ON DELETE CASCADE,
  platform              TEXT        NOT NULL
                                    CHECK (platform IN (
                                      'facebook', 'instagram', 'twitter', 'youtube'
                                    )),
  status                TEXT        NOT NULL DEFAULT 'pending'
                                    CHECK (status IN (
                                      'pending', 'posted', 'failed', 'skipped'
                                    )),
  platform_post_id      TEXT,
  platform_url          TEXT,
  posted_at             TIMESTAMPTZ,
  error_message         TEXT,
  retry_count           INTEGER     NOT NULL DEFAULT 0,
  engagement_data       JSONB,
  engagement_updated_at TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: user_preferences
-- Per-user personalisation. One row per user (UNIQUE on user_id).
-- Controls which categories and viral tiers appear in the feed.
-- ---------------------------------------------------------------------------
CREATE TABLE public.user_preferences (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID        NOT NULL UNIQUE REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  preferred_categories  INTEGER[],
  preferred_viral_tiers INTEGER[]
                          CHECK (preferred_viral_tiers <@ ARRAY[1, 2, 3]),
  notification_enabled  BOOLEAN     NOT NULL DEFAULT TRUE,
  email_digest_enabled  BOOLEAN     NOT NULL DEFAULT FALSE,
  digest_frequency      TEXT        DEFAULT 'weekly'
                          CHECK (digest_frequency IN ('daily', 'weekly', NULL)),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: user_submissions
-- Authenticated users submit topic suggestions for editorial review.
-- Moderators (admins) approve or reject and attach notes.
-- ---------------------------------------------------------------------------
CREATE TABLE public.user_submissions (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID        NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  category_id     INTEGER     REFERENCES public.categories(id) ON DELETE SET NULL,
  title           TEXT        NOT NULL,
  url             TEXT,
  description     TEXT,
  status          TEXT        NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'approved', 'rejected')),
  moderator_notes TEXT,
  reviewed_by     UUID        REFERENCES public.user_profiles(id) ON DELETE SET NULL,
  reviewed_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: deletion_audit_log
-- Immutable append-only ledger. Every admin-triggered row deletion must write
-- a full data_snapshot here for compliance and GDPR audit trails.
-- ---------------------------------------------------------------------------
CREATE TABLE public.deletion_audit_log (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name    TEXT        NOT NULL,
  record_id     TEXT        NOT NULL,
  deleted_by    UUID        REFERENCES public.user_profiles(id) ON DELETE SET NULL,
  reason        TEXT,
  data_snapshot JSONB       NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: consent_records
-- GDPR / privacy compliance. Append-only per consent event.
-- The most recent row per (user_id, consent_type) is the current state.
-- ---------------------------------------------------------------------------
CREATE TABLE public.consent_records (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID        NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  consent_type  TEXT        NOT NULL
                            CHECK (consent_type IN (
                              'privacy_policy',
                              'terms_of_service',
                              'marketing',
                              'data_processing',
                              'cookies'
                            )),
  granted       BOOLEAN     NOT NULL,
  version       TEXT        NOT NULL,
  ip_address    INET,
  user_agent    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- =============================================================================
-- SECTION 3: FUNCTIONS
-- set_updated_at() has no table deps and can be defined at any point.
-- is_admin() references public.user_profiles in its SQL body — PostgreSQL 14+
-- resolves SQL-language function bodies at definition time, so this MUST come
-- after CREATE TABLE public.user_profiles above.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- FUNCTION: set_updated_at
-- Trigger helper — stamps updated_at = NOW() on every row write.
-- LANGUAGE plpgsql bodies are NOT resolved at definition time, so this
-- could technically go before the tables, but we keep all functions together
-- for clarity and to enforce the documented execution order.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;


-- ---------------------------------------------------------------------------
-- FUNCTION: is_admin
-- Returns TRUE when the currently authenticated user has is_admin = TRUE
-- in public.user_profiles.  SECURITY DEFINER makes it run as the function
-- owner (postgres / service role), which means:
--   (a) it bypasses RLS on user_profiles — no infinite recursion, and
--   (b) it works correctly even when user_profiles has RLS enabled.
-- STABLE tells the planner it returns the same value within a single query,
-- allowing it to be inlined and called efficiently inside policy USING clauses.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL
SECURITY DEFINER
STABLE
AS $$
  SELECT COALESCE(
    (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()),
    FALSE
  );
$$;


-- =============================================================================
-- SECTION 4: ENABLE ROW LEVEL SECURITY
-- All tables locked down; service-role key bypasses this entirely.
-- =============================================================================

ALTER TABLE public.categories         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.config             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.runs_log           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.raw_signals        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trending_topics    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viral_predictions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_safety_log   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.distribution_log   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_submissions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deletion_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_records    ENABLE ROW LEVEL SECURITY;


-- =============================================================================
-- SECTION 5: ROW LEVEL SECURITY POLICIES
-- is_admin() is fully resolved at this point (function + table both exist).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- categories — public read, admin write
-- ---------------------------------------------------------------------------
CREATE POLICY "categories_public_select"
  ON public.categories FOR SELECT
  USING (TRUE);

CREATE POLICY "categories_admin_insert"
  ON public.categories FOR INSERT
  WITH CHECK (public.is_admin());

CREATE POLICY "categories_admin_update"
  ON public.categories FOR UPDATE
  USING (public.is_admin());

CREATE POLICY "categories_admin_delete"
  ON public.categories FOR DELETE
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- config — admin only (contains model weights, blocklists, platform secrets)
-- ---------------------------------------------------------------------------
CREATE POLICY "config_admin_all"
  ON public.config FOR ALL
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- runs_log — admin only
-- ---------------------------------------------------------------------------
CREATE POLICY "runs_log_admin_all"
  ON public.runs_log FOR ALL
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- user_profiles — users see/edit their own row; admins see/edit all rows.
--                 Non-admins cannot elevate is_admin on their own record.
-- ---------------------------------------------------------------------------
CREATE POLICY "user_profiles_select_own_or_admin"
  ON public.user_profiles FOR SELECT
  USING (auth.uid() = id OR public.is_admin());

CREATE POLICY "user_profiles_insert_self"
  ON public.user_profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

CREATE POLICY "user_profiles_update_own_or_admin"
  ON public.user_profiles FOR UPDATE
  USING (auth.uid() = id OR public.is_admin())
  WITH CHECK (
    -- Admins can set any value; non-admins cannot grant themselves is_admin
    CASE
      WHEN public.is_admin() THEN TRUE
      ELSE is_admin = FALSE
    END
  );

CREATE POLICY "user_profiles_delete_admin_only"
  ON public.user_profiles FOR DELETE
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- raw_signals — admin only (internal pipeline data, never exposed to users)
-- ---------------------------------------------------------------------------
CREATE POLICY "raw_signals_admin_all"
  ON public.raw_signals FOR ALL
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- trending_topics — published topics publicly readable; all other statuses
--                   and all write operations require admin.
-- ---------------------------------------------------------------------------
CREATE POLICY "trending_topics_public_select_published"
  ON public.trending_topics FOR SELECT
  USING (status = 'published' OR public.is_admin());

CREATE POLICY "trending_topics_admin_insert"
  ON public.trending_topics FOR INSERT
  WITH CHECK (public.is_admin());

CREATE POLICY "trending_topics_admin_update"
  ON public.trending_topics FOR UPDATE
  USING (public.is_admin());

CREATE POLICY "trending_topics_admin_delete"
  ON public.trending_topics FOR DELETE
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- viral_predictions — admin only (internal scoring, not for end users)
-- ---------------------------------------------------------------------------
CREATE POLICY "viral_predictions_admin_all"
  ON public.viral_predictions FOR ALL
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- brand_safety_log — admin only (contains moderation detail)
-- ---------------------------------------------------------------------------
CREATE POLICY "brand_safety_log_admin_all"
  ON public.brand_safety_log FOR ALL
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- distribution_log — admin only (contains platform post IDs / credentials)
-- ---------------------------------------------------------------------------
CREATE POLICY "distribution_log_admin_all"
  ON public.distribution_log FOR ALL
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- user_preferences — users manage their own row; admins can see all
-- ---------------------------------------------------------------------------
CREATE POLICY "user_preferences_select_own_or_admin"
  ON public.user_preferences FOR SELECT
  USING (auth.uid() = user_id OR public.is_admin());

CREATE POLICY "user_preferences_insert_own"
  ON public.user_preferences FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_preferences_update_own_or_admin"
  ON public.user_preferences FOR UPDATE
  USING (auth.uid() = user_id OR public.is_admin());

CREATE POLICY "user_preferences_delete_own_or_admin"
  ON public.user_preferences FOR DELETE
  USING (auth.uid() = user_id OR public.is_admin());


-- ---------------------------------------------------------------------------
-- user_submissions — users see/create/edit their own pending submissions;
--                    admins can see and moderate all.
-- ---------------------------------------------------------------------------
CREATE POLICY "user_submissions_select_own_or_admin"
  ON public.user_submissions FOR SELECT
  USING (auth.uid() = user_id OR public.is_admin());

CREATE POLICY "user_submissions_insert_own"
  ON public.user_submissions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_submissions_update_own_pending_or_admin"
  ON public.user_submissions FOR UPDATE
  USING (
    (auth.uid() = user_id AND status = 'pending')
    OR public.is_admin()
  );

CREATE POLICY "user_submissions_delete_admin_only"
  ON public.user_submissions FOR DELETE
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- deletion_audit_log — admin only (compliance ledger)
-- ---------------------------------------------------------------------------
CREATE POLICY "deletion_audit_log_admin_all"
  ON public.deletion_audit_log FOR ALL
  USING (public.is_admin());


-- ---------------------------------------------------------------------------
-- consent_records — users can read their own records and append new consent
--                   events; no UPDATE/DELETE for regular users (append-only);
--                   admins can manage all records.
-- ---------------------------------------------------------------------------
CREATE POLICY "consent_records_select_own_or_admin"
  ON public.consent_records FOR SELECT
  USING (auth.uid() = user_id OR public.is_admin());

CREATE POLICY "consent_records_insert_own"
  ON public.consent_records FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "consent_records_admin_manage"
  ON public.consent_records FOR ALL
  USING (public.is_admin());


-- =============================================================================
-- SECTION 6: INDEXES
-- Covering frequently-queried columns: batch_id, status, published_at,
-- viral_tier, category_id, user_id, and high-cardinality sort columns.
-- =============================================================================

-- config
CREATE INDEX idx_config_key
  ON public.config (key);

-- runs_log
CREATE INDEX idx_runs_log_batch_id
  ON public.runs_log (batch_id);
CREATE INDEX idx_runs_log_status
  ON public.runs_log (status);
CREATE INDEX idx_runs_log_started_at
  ON public.runs_log (started_at DESC);

-- user_profiles
CREATE INDEX idx_user_profiles_email
  ON public.user_profiles (email);
CREATE INDEX idx_user_profiles_is_admin
  ON public.user_profiles (is_admin) WHERE is_admin = TRUE;

-- raw_signals
CREATE INDEX idx_raw_signals_batch_id
  ON public.raw_signals (batch_id);
CREATE INDEX idx_raw_signals_platform
  ON public.raw_signals (platform);
CREATE INDEX idx_raw_signals_topic_keyword
  ON public.raw_signals (topic_keyword);
CREATE INDEX idx_raw_signals_collected_at
  ON public.raw_signals (collected_at DESC);

-- trending_topics
CREATE INDEX idx_trending_topics_batch_id
  ON public.trending_topics (batch_id);
CREATE INDEX idx_trending_topics_status
  ON public.trending_topics (status);
CREATE INDEX idx_trending_topics_published_at
  ON public.trending_topics (published_at DESC) WHERE published_at IS NOT NULL;
CREATE INDEX idx_trending_topics_viral_tier
  ON public.trending_topics (viral_tier) WHERE viral_tier IS NOT NULL;
CREATE INDEX idx_trending_topics_category_id
  ON public.trending_topics (category_id);
CREATE INDEX idx_trending_topics_viral_score
  ON public.trending_topics (viral_score DESC);

-- viral_predictions
CREATE INDEX idx_viral_predictions_topic_id
  ON public.viral_predictions (topic_id);
CREATE INDEX idx_viral_predictions_batch_id
  ON public.viral_predictions (batch_id);
CREATE INDEX idx_viral_predictions_tier
  ON public.viral_predictions (tier_assigned);
CREATE INDEX idx_viral_predictions_score
  ON public.viral_predictions (weighted_score DESC);

-- brand_safety_log
CREATE INDEX idx_brand_safety_log_topic_id
  ON public.brand_safety_log (topic_id);
CREATE INDEX idx_brand_safety_log_batch_id
  ON public.brand_safety_log (batch_id);
CREATE INDEX idx_brand_safety_log_passed
  ON public.brand_safety_log (overall_passed);

-- distribution_log
CREATE INDEX idx_distribution_log_topic_id
  ON public.distribution_log (topic_id);
CREATE INDEX idx_distribution_log_platform
  ON public.distribution_log (platform);
CREATE INDEX idx_distribution_log_status
  ON public.distribution_log (status);
CREATE INDEX idx_distribution_log_posted_at
  ON public.distribution_log (posted_at DESC) WHERE posted_at IS NOT NULL;

-- user_preferences
CREATE INDEX idx_user_preferences_user_id
  ON public.user_preferences (user_id);

-- user_submissions
CREATE INDEX idx_user_submissions_user_id
  ON public.user_submissions (user_id);
CREATE INDEX idx_user_submissions_status
  ON public.user_submissions (status);
CREATE INDEX idx_user_submissions_category_id
  ON public.user_submissions (category_id);
CREATE INDEX idx_user_submissions_created_at
  ON public.user_submissions (created_at DESC);

-- deletion_audit_log
CREATE INDEX idx_deletion_audit_log_table_name
  ON public.deletion_audit_log (table_name);
CREATE INDEX idx_deletion_audit_log_record_id
  ON public.deletion_audit_log (record_id);
CREATE INDEX idx_deletion_audit_log_deleted_by
  ON public.deletion_audit_log (deleted_by);
CREATE INDEX idx_deletion_audit_log_created_at
  ON public.deletion_audit_log (created_at DESC);

-- consent_records
CREATE INDEX idx_consent_records_user_id
  ON public.consent_records (user_id);
CREATE INDEX idx_consent_records_consent_type
  ON public.consent_records (consent_type);
CREATE INDEX idx_consent_records_created_at
  ON public.consent_records (created_at DESC);
CREATE INDEX idx_consent_records_user_type
  ON public.consent_records (user_id, consent_type, created_at DESC);


-- =============================================================================
-- SECTION 7: TRIGGERS
-- set_updated_at() is now defined (Section 3), so all CREATE TRIGGER
-- statements are safe to run here.
-- =============================================================================

CREATE TRIGGER trg_categories_updated_at
  BEFORE UPDATE ON public.categories
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_config_updated_at
  BEFORE UPDATE ON public.config
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_runs_log_updated_at
  BEFORE UPDATE ON public.runs_log
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_user_profiles_updated_at
  BEFORE UPDATE ON public.user_profiles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_raw_signals_updated_at
  BEFORE UPDATE ON public.raw_signals
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_trending_topics_updated_at
  BEFORE UPDATE ON public.trending_topics
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_viral_predictions_updated_at
  BEFORE UPDATE ON public.viral_predictions
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_brand_safety_log_updated_at
  BEFORE UPDATE ON public.brand_safety_log
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_distribution_log_updated_at
  BEFORE UPDATE ON public.distribution_log
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_user_preferences_updated_at
  BEFORE UPDATE ON public.user_preferences
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_user_submissions_updated_at
  BEFORE UPDATE ON public.user_submissions
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_deletion_audit_log_updated_at
  BEFORE UPDATE ON public.deletion_audit_log
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_consent_records_updated_at
  BEFORE UPDATE ON public.consent_records
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- OPTIONAL: auto-create user_profile on Supabase Auth signup.
-- Uncomment and run separately (or add via Dashboard → Database → Triggers)
-- after verifying auth schema access in your project.
-- =============================================================================
/*
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, display_name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1))
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
*/

COMMIT;
