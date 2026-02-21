-- =============================================================================
-- VIDEO-FIRST AI-CURATED TRENDING NEWS PLATFORM
-- Supabase Seed File
-- =============================================================================
-- Run this file AFTER schema.sql on a fresh Supabase project.
-- All inserts use ON CONFLICT ... DO NOTHING so the file is safe to re-run.
--
-- Sections:
--   1. Content categories (10 verticals)
--   2. Default config values (viral weights, tiers, blocklist, etc.)
--   3. Admin user placeholder
-- =============================================================================


-- =============================================================================
-- 1. CONTENT CATEGORIES
-- Ten verticals used for classification, personalisation, and feed filtering.
-- The slug matches the category_multipliers keys in the config table.
-- =============================================================================
INSERT INTO public.categories (name, slug, description) VALUES
  (
    'Technology',
    'technology',
    'AI, software, hardware, gadgets, cybersecurity, and digital innovation'
  ),
  (
    'Entertainment',
    'entertainment',
    'Movies, TV shows, music, gaming, streaming, and celebrity news'
  ),
  (
    'Sports',
    'sports',
    'Live scores, match analysis, athlete news, and sporting events'
  ),
  (
    'Politics',
    'politics',
    'Government, elections, legislation, policy debates, and geopolitical affairs'
  ),
  (
    'Business & Finance',
    'business-finance',
    'Stock markets, startups, economy, mergers, and corporate strategy'
  ),
  (
    'Health & Science',
    'health-science',
    'Medical research, wellness trends, scientific discoveries, and public health'
  ),
  (
    'Lifestyle',
    'lifestyle',
    'Fashion, food, travel, relationships, personal development, and home'
  ),
  (
    'World News',
    'world-news',
    'International events, diplomacy, conflicts, and global affairs'
  ),
  (
    'Culture & Arts',
    'culture-arts',
    'Literature, visual arts, theatre, film festivals, and cultural movements'
  ),
  (
    'Environment',
    'environment',
    'Climate change, conservation, sustainability, renewable energy, and ecology'
  )
ON CONFLICT (slug) DO NOTHING;


-- =============================================================================
-- 2. DEFAULT CONFIG
-- All tunable runtime values for the pipeline.
-- Admins can adjust these via the admin panel without a code deploy.
-- =============================================================================

INSERT INTO public.config (key, value, description) VALUES

  -- -------------------------------------------------------------------------
  -- Viral Prediction: feature weights for the Weighted Linear Scoring Model.
  -- Values MUST sum to exactly 1.0.
  -- After 30 days of labelled data, replace with XGBoost and update this key
  -- to 'xgboost_feature_importance' for reference only.
  -- -------------------------------------------------------------------------
  (
    'viral_prediction_weights',
    '{
      "cross_platform":    0.25,
      "velocity_ratio":    0.20,
      "acceleration":      0.15,
      "publication_gap":   0.10,
      "sentiment_polarity":0.10,
      "time_of_day":       0.10,
      "category":          0.10
    }'::jsonb,
    'Feature weights for the weighted linear viral scoring model. Must sum to 1.0. Tune weekly using the Learning Loop report.'
  ),

  -- -------------------------------------------------------------------------
  -- Viral Tier Thresholds
  -- weighted_score >= tier1_min  → Tier 1 (Kling video + ElevenLabs)
  -- weighted_score >= tier2_min  → Tier 2 (YouTube/Vimeo embed)
  -- weighted_score >= tier3_min  → Tier 3 (YouTube/Vimeo embed, lower priority)
  -- weighted_score <  tier3_min  → Rejected
  -- -------------------------------------------------------------------------
  (
    'viral_tier_thresholds',
    '{
      "tier1_min": 0.80,
      "tier2_min": 0.60,
      "tier3_min": 0.40
    }'::jsonb,
    'Minimum weighted_score required for Tier 1 / 2 / 3 assignment. Topics scoring below tier3_min are rejected from the pipeline.'
  ),

  -- -------------------------------------------------------------------------
  -- LLM Validation Band
  -- Claude Haiku is invoked ONLY when weighted_score falls inside this band
  -- (ambiguous cases).  Outside the band the score alone determines the tier.
  -- -------------------------------------------------------------------------
  (
    'llm_validation_band',
    '{
      "min": 0.40,
      "max": 0.60
    }'::jsonb,
    'Score band (inclusive) where Claude Haiku LLM validation is triggered. Scores clearly above max or below min skip the LLM call to save cost.'
  ),

  -- -------------------------------------------------------------------------
  -- Category Multipliers
  -- Applied to the raw category feature score during viral prediction.
  -- Values > 1.0 boost categories with historically higher engagement;
  -- values < 1.0 dampen lower-performing verticals.
  -- -------------------------------------------------------------------------
  (
    'category_multipliers',
    '{
      "technology":       1.20,
      "entertainment":    1.15,
      "sports":           1.10,
      "health-science":   1.10,
      "politics":         1.05,
      "business-finance": 1.05,
      "world-news":       1.00,
      "environment":      1.00,
      "lifestyle":        0.95,
      "culture-arts":     0.90
    }'::jsonb,
    'Per-category multiplier applied during viral scoring. Tune based on 30-day engagement data from the Learning Loop.'
  ),

  -- -------------------------------------------------------------------------
  -- Time-of-Day Multipliers
  -- Applied based on UTC hour of signal collection.  Peak hours get a boost;
  -- overnight hours are dampened.  Keys are UTC hour strings "0"–"23".
  -- -------------------------------------------------------------------------
  (
    'time_of_day_multipliers',
    '{
      "0":  0.75, "1":  0.70, "2":  0.70, "3":  0.70, "4":  0.75, "5":  0.80,
      "6":  0.90, "7":  1.00, "8":  1.10, "9":  1.20, "10": 1.25, "11": 1.25,
      "12": 1.20, "13": 1.15, "14": 1.10, "15": 1.15, "16": 1.20, "17": 1.25,
      "18": 1.30, "19": 1.30, "20": 1.25, "21": 1.15, "22": 1.00, "23": 0.85
    }'::jsonb,
    'UTC-hour multipliers applied to the time_of_day feature. Peak engagement windows (08-11, 18-20) receive the highest boosts.'
  ),

  -- -------------------------------------------------------------------------
  -- Brand Safety Blocklist
  -- Hard-stop keywords checked BEFORE Llama Guard and Claude Haiku.
  -- Any exact or substring match immediately rejects the topic.
  -- Extend this list via the admin panel — no code deploy required.
  -- -------------------------------------------------------------------------
  (
    'brand_safety_blocklist',
    '[
      "gore",
      "beheading",
      "terrorism",
      "terrorist",
      "suicide",
      "self-harm",
      "self harm",
      "child abuse",
      "child exploitation",
      "csam",
      "hate speech",
      "explicit nudity",
      "pornography",
      "drug trafficking",
      "weapons trafficking",
      "genocide",
      "ethnic cleansing",
      "snuff",
      "doxxing",
      "swatting"
    ]'::jsonb,
    'Hard-stop keyword blocklist. Topics containing any of these strings (case-insensitive substring match) are immediately rejected without LLM evaluation.'
  ),

  -- -------------------------------------------------------------------------
  -- Distribution Platform Rules
  -- Controls which platforms receive content by viral tier.
  -- -------------------------------------------------------------------------
  (
    'distribution_platforms',
    '{
      "all_enabled":   ["facebook", "instagram", "twitter", "youtube"],
      "tier1":         ["facebook", "instagram", "twitter", "youtube"],
      "tier2":         ["facebook", "instagram", "twitter"],
      "tier3":         ["twitter"],
      "retry_limit":   3,
      "retry_delay_s": 300
    }'::jsonb,
    'Distribution rules per viral tier. Tier 1 posts everywhere; Tier 3 posts to Twitter only. retry_limit and retry_delay_s govern the Distribution Agent retry loop.'
  ),

  -- -------------------------------------------------------------------------
  -- Learning Loop Configuration
  -- Controls the weekly async job that compares predicted vs actual virality
  -- and generates a weight-adjustment report via Claude Haiku → Resend email.
  -- -------------------------------------------------------------------------
  (
    'learning_loop',
    '{
      "enabled":               true,
      "run_day_of_week":       "sunday",
      "run_hour_utc":          2,
      "observation_window_days": 7,
      "min_samples_for_update":  30,
      "report_email":          "admin@yourplatform.com"
    }'::jsonb,
    'Weekly learning loop settings. After min_samples_for_update labelled topics are available, the Haiku weight-adjustment report is generated and emailed via Resend.'
  ),

  -- -------------------------------------------------------------------------
  -- Media Generation Settings
  -- Tier 1 uses Kling (video) + ElevenLabs (audio) + FFmpeg (assembly).
  -- All tiers use Flux 1.1 Pro for the thumbnail.
  -- -------------------------------------------------------------------------
  (
    'media_generation',
    '{
      "thumbnail_model":      "flux-1.1-pro",
      "thumbnail_width":      1280,
      "thumbnail_height":     720,
      "tier1_video_model":    "kling-v1",
      "tier1_tts_voice":      "elevenlabs-default",
      "tier1_video_duration": 60,
      "embed_search_order":   ["youtube", "vimeo"],
      "ffmpeg_preset":        "fast",
      "storage_bucket":       "media"
    }'::jsonb,
    'Media generation parameters for the tiered video pipeline. thumbnail_model and tier1_video_model map to API model identifiers.'
  )

ON CONFLICT (key) DO NOTHING;


-- =============================================================================
-- 3. ADMIN USER PLACEHOLDER
-- =============================================================================
-- IMPORTANT: This row cannot be inserted until a matching row exists in
-- auth.users (Supabase Auth).  Follow these steps:
--
--   Step 1 — Create the admin account in Supabase Dashboard:
--             Authentication → Users → Invite user (or Add user)
--             Use the email: admin@yourplatform.com
--
--   Step 2 — Copy the UUID assigned by Supabase Auth.
--
--   Step 3 — Replace '00000000-0000-0000-0000-000000000001' below with
--             the real UUID, then run this INSERT.
--
--   Alternatively, if you set up the handle_new_user() trigger from schema.sql,
--   the user_profiles row is created automatically on sign-up — then just
--   run an UPDATE to set is_admin = TRUE:
--
--     UPDATE public.user_profiles
--     SET    is_admin = TRUE
--     WHERE  email    = 'admin@yourplatform.com';
--
-- The INSERT below is provided as a convenience for fresh environments where
-- the trigger has not yet been applied and the UUID is known in advance.
-- =============================================================================

/*  Uncomment and replace UUID after creating the auth user:

INSERT INTO public.user_profiles (id, email, display_name, is_admin)
VALUES (
  '00000000-0000-0000-0000-000000000001',  -- ← replace with real auth.users.id
  'admin@yourplatform.com',                -- ← replace with real admin email
  'Platform Admin',
  TRUE
)
ON CONFLICT (id) DO UPDATE
  SET is_admin     = TRUE,
      display_name = EXCLUDED.display_name,
      updated_at   = NOW();

*/


-- =============================================================================
-- VERIFY SEED
-- Run these queries to confirm the seed was applied correctly.
-- =============================================================================
/*
SELECT count(*) AS category_count FROM public.categories;        -- expect 10
SELECT key      FROM public.config ORDER BY key;                  -- expect 8 rows
*/
