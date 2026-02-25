-- =============================================================================
-- MIGRATION 002: PREDICTIVE ANALYTICS TABLES
-- Adds reader behavioral event tracking, feature store, prediction cache,
-- and persona mapping tables for the analytics service.
-- =============================================================================

BEGIN;

-- =============================================================================
-- SECTION 1: TABLES
-- =============================================================================

-- ---------------------------------------------------------------------------
-- TABLE: reader_events
-- Raw behavioral event log ingested from the frontend JS tracker or
-- webhook sources (Segment, Snowplow, custom). One row per event.
-- No PII stored — uses opaque session_id and user_id (UUID).
-- ---------------------------------------------------------------------------
CREATE TABLE public.reader_events (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id    TEXT        NOT NULL,
  user_id       UUID        REFERENCES public.user_profiles(id) ON DELETE SET NULL,
  event_type    TEXT        NOT NULL CHECK (event_type IN (
    'pageview', 'click', 'scroll_depth', 'time_on_page',
    'newsletter_click', 'paywall_hit', 'subscribe', 'unsubscribe',
    'register', 'share'
  )),
  topic_id      UUID        REFERENCES public.trending_topics(id) ON DELETE SET NULL,
  category_id   INTEGER     REFERENCES public.categories(id) ON DELETE SET NULL,
  metadata      JSONB       NOT NULL DEFAULT '{}',
  device_type   TEXT,
  geo_country   TEXT,
  referrer      TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: reader_features
-- Aggregated feature store for ML models. One row per registered user,
-- recomputed every 15-30 minutes by the feature engineering pipeline.
-- ---------------------------------------------------------------------------
CREATE TABLE public.reader_features (
  id                        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                   UUID        UNIQUE REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  session_id                TEXT,
  session_count             INTEGER     DEFAULT 0,
  total_pageviews           INTEGER     DEFAULT 0,
  articles_read_last_7d     INTEGER     DEFAULT 0,
  articles_read_last_30d    INTEGER     DEFAULT 0,
  avg_time_on_page_sec      NUMERIC(8,2) DEFAULT 0,
  avg_scroll_depth_pct      NUMERIC(5,2) DEFAULT 0,
  top_category_id           INTEGER     REFERENCES public.categories(id),
  category_distribution     JSONB       DEFAULT '{}',
  newsletter_open_rate      NUMERIC(5,4) DEFAULT 0,
  total_paywall_hits        INTEGER     DEFAULT 0,
  total_shares              INTEGER     DEFAULT 0,
  days_since_registration   INTEGER,
  days_since_last_visit     INTEGER,
  visit_frequency_weekly    NUMERIC(5,2) DEFAULT 0,
  device_type_primary       TEXT,
  geo_country               TEXT,
  is_subscriber             BOOLEAN     DEFAULT FALSE,
  subscription_start_date   TIMESTAMPTZ,
  computed_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: reader_predictions
-- Persisted model inference outputs with explainability metadata.
-- One row per (user, prediction_type) per model run.
-- ---------------------------------------------------------------------------
CREATE TABLE public.reader_predictions (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID        REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  session_id        TEXT,
  prediction_type   TEXT        NOT NULL CHECK (prediction_type IN (
    'subscribe', 'churn', 'register', 'ltv'
  )),
  score             NUMERIC(7,4) NOT NULL,
  confidence        NUMERIC(5,4),
  top_features      JSONB,
  model_version     TEXT        NOT NULL,
  expires_at        TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- TABLE: reader_personas
-- User-to-persona cluster mapping produced by the persona training pipeline.
-- One row per user (UNIQUE on user_id), re-computed on each training cycle.
-- ---------------------------------------------------------------------------
CREATE TABLE public.reader_personas (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID        UNIQUE REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  persona_name  TEXT        NOT NULL,
  persona_slug  TEXT        NOT NULL,
  cluster_id    INTEGER,
  confidence    NUMERIC(5,4),
  traits        JSONB       DEFAULT '{}',
  model_version TEXT        NOT NULL,
  computed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- =============================================================================
-- SECTION 2: ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE public.reader_events      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reader_features    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reader_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reader_personas    ENABLE ROW LEVEL SECURITY;

-- reader_events — service-role inserts; admin reads for analytics
CREATE POLICY "reader_events_admin_all"
  ON public.reader_events FOR ALL
  USING (public.is_admin());

-- reader_features — admin only (internal ML feature store)
CREATE POLICY "reader_features_admin_all"
  ON public.reader_features FOR ALL
  USING (public.is_admin());

-- reader_predictions — users can see their own; admins see all
CREATE POLICY "reader_predictions_select_own_or_admin"
  ON public.reader_predictions FOR SELECT
  USING (auth.uid() = user_id OR public.is_admin());

CREATE POLICY "reader_predictions_admin_write"
  ON public.reader_predictions FOR ALL
  USING (public.is_admin());

-- reader_personas — users can see their own; admins see all
CREATE POLICY "reader_personas_select_own_or_admin"
  ON public.reader_personas FOR SELECT
  USING (auth.uid() = user_id OR public.is_admin());

CREATE POLICY "reader_personas_admin_write"
  ON public.reader_personas FOR ALL
  USING (public.is_admin());


-- =============================================================================
-- SECTION 3: INDEXES
-- =============================================================================

-- reader_events
CREATE INDEX idx_reader_events_session_id
  ON public.reader_events (session_id);
CREATE INDEX idx_reader_events_user_id
  ON public.reader_events (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_reader_events_event_type
  ON public.reader_events (event_type);
CREATE INDEX idx_reader_events_topic_id
  ON public.reader_events (topic_id) WHERE topic_id IS NOT NULL;
CREATE INDEX idx_reader_events_created_at
  ON public.reader_events (created_at DESC);
CREATE INDEX idx_reader_events_user_created
  ON public.reader_events (user_id, created_at DESC) WHERE user_id IS NOT NULL;

-- reader_features
CREATE INDEX idx_reader_features_user_id
  ON public.reader_features (user_id);
CREATE INDEX idx_reader_features_computed_at
  ON public.reader_features (computed_at DESC);

-- reader_predictions
CREATE INDEX idx_reader_predictions_user_id
  ON public.reader_predictions (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_reader_predictions_session_id
  ON public.reader_predictions (session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_reader_predictions_type
  ON public.reader_predictions (prediction_type);
CREATE INDEX idx_reader_predictions_user_type
  ON public.reader_predictions (user_id, prediction_type, created_at DESC);
CREATE INDEX idx_reader_predictions_expires
  ON public.reader_predictions (expires_at) WHERE expires_at IS NOT NULL;

-- reader_personas
CREATE INDEX idx_reader_personas_user_id
  ON public.reader_personas (user_id);
CREATE INDEX idx_reader_personas_slug
  ON public.reader_personas (persona_slug);
CREATE INDEX idx_reader_personas_cluster
  ON public.reader_personas (cluster_id);


-- =============================================================================
-- SECTION 4: TRIGGERS (reuse existing set_updated_at function)
-- =============================================================================

CREATE TRIGGER trg_reader_features_updated_at
  BEFORE UPDATE ON public.reader_features
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_reader_personas_updated_at
  BEFORE UPDATE ON public.reader_personas
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =============================================================================
-- SECTION 5: DATA RETENTION (extend existing pg_cron pattern)
-- Purge reader_events older than 90 days; keep aggregated features.
-- =============================================================================
-- Uncomment and add via Dashboard → Database → Extensions → pg_cron:
/*
SELECT cron.schedule(
  'purge-reader-events-90d',
  '0 4 * * *',
  $$DELETE FROM public.reader_events WHERE created_at < NOW() - INTERVAL '90 days'$$
);

SELECT cron.schedule(
  'purge-expired-predictions',
  '0 4 * * *',
  $$DELETE FROM public.reader_predictions WHERE expires_at < NOW()$$
);
*/

COMMIT;
