/**
 * @platform/types — Shared TypeScript interfaces for theNewslane platform.
 *
 * These types mirror the Supabase schema defined in docs/schema.sql.
 * Import from '@platform/types' in any app or package.
 */

// =============================================================================
// Primitives
// =============================================================================

export type UUID   = string;
export type ISODate = string; // ISO-8601 timestamp string from Supabase

// =============================================================================
// Category
// Mirrors: public.categories
// =============================================================================

export interface Category {
  id:          number;
  name:        string;
  slug:        string;
  color:       string | null;
  description: string | null;
  created_at:  ISODate;
  updated_at:  ISODate;
}

// =============================================================================
// BatchRun
// Mirrors: public.runs_log
// One record per Inngest CRON execution (every 4 hours).
// =============================================================================

export type BatchRunStatus = 'running' | 'completed' | 'failed' | 'partial';

export interface BatchRun {
  id:                UUID;
  batch_id:          string;
  status:            BatchRunStatus;
  started_at:        ISODate;
  completed_at:      ISODate | null;
  signals_collected: number;
  topics_processed:  number;
  topics_published:  number;
  topics_rejected:   number;
  error_message:     string | null;
  metadata:          Record<string, unknown> | null;
  created_at:        ISODate;
  updated_at:        ISODate;
}

// =============================================================================
// TrendingTopic
// Mirrors: public.trending_topics
// =============================================================================

export type TopicStatus =
  | 'pending'
  | 'predicting'
  | 'brand_checking'
  | 'generating'
  | 'published'
  | 'rejected';

export type VideoType =
  | 'kling_generated'
  | 'youtube_embed'
  | 'vimeo_embed';

export interface SocialCopy {
  facebook:  string | null;
  instagram: string | null;
  twitter:   string | null;
  youtube:   string | null;
}

export interface TrendingTopic {
  id:               UUID;
  batch_id:         string;
  category_id:      number | null;

  // Identity
  title:            string;
  slug:             string;

  // AI-generated content package (Claude Sonnet 4.5)
  summary:          string | null;
  article:          string | null;
  social_copy:      SocialCopy | null;
  script:           string | null;    // ElevenLabs narration input
  iab_tags:         string[] | null;
  // Stored as a single JSON object by the pipeline (keys: faq, seo_title, meta_description,
  // image_prompt, headline_cluster, embed_url, channel_name, video_id, video_url_portrait)
  schema_blocks:    Record<string, unknown> | null;

  // Media assets
  thumbnail_url:    string | null;    // Flux 1.1 Pro image
  video_url:        string | null;    // Assembled video
  video_type:       VideoType | null;

  // Viral scoring
  viral_tier:       1 | 2 | 3 | null;
  viral_score:      number | null;    // 0.0000–1.0000

  // Lifecycle
  status:           TopicStatus;
  rejection_reason: string | null;
  published_at:     ISODate | null;

  created_at:       ISODate;
  updated_at:       ISODate;

  // Joined relations (present when queried with select)
  category?:        Category;
}

// =============================================================================
// ViralPrediction
// Mirrors: public.viral_predictions
// =============================================================================

export interface ViralPrediction {
  id:       UUID;
  topic_id: UUID;
  batch_id: string;

  // Feature Engineering scores
  cross_platform_score:   number; // 0–1
  velocity_ratio:         number;
  acceleration_score:     number;
  publication_gap_score:  number;
  sentiment_polarity:     number; // VADER −1 to 1
  time_of_day_multiplier: number;
  category_multiplier:    number;

  // Weighted Linear Model output
  weighted_score: number; // 0–1

  // LLM Validator (Claude Haiku — 40–60% band only)
  llm_validated:  boolean | null;
  llm_confidence: number | null;
  llm_reasoning:  string | null;

  // Decision
  tier_assigned:    1 | 2 | 3 | null;
  rejected:         boolean;
  rejection_reason: string | null;

  // Learning loop (populated weekly)
  actual_virality_score:      number | null;
  actual_virality_updated_at: ISODate | null;

  created_at: ISODate;
  updated_at: ISODate;
}

// =============================================================================
// DistributionLog
// Mirrors: public.distribution_log
// =============================================================================

export type DistributionPlatform = 'facebook' | 'instagram' | 'twitter' | 'youtube';
export type DistributionStatus   = 'pending' | 'posted' | 'failed' | 'skipped';

export interface DistributionLog {
  id:       UUID;
  topic_id: UUID;

  platform:         DistributionPlatform;
  status:           DistributionStatus;
  platform_post_id: string | null;
  platform_url:     string | null;
  posted_at:        ISODate | null;
  error_message:    string | null;
  retry_count:      number;

  engagement_data:       Record<string, unknown> | null;
  engagement_updated_at: ISODate | null;

  created_at: ISODate;
  updated_at: ISODate;
}

// =============================================================================
// UserProfile
// Mirrors: public.user_profiles
// =============================================================================

export interface UserProfile {
  id:                        UUID;
  email:                     string;
  display_name:              string | null;
  avatar_url:                string | null;
  is_admin:                  boolean;
  is_minor:                  boolean;           // age 13–17 at registration
  is_active:                 boolean;
  ccpa_opt_out:              boolean;           // CCPA Do Not Sell flag
  weekly_submission_used_at: ISODate | null;    // 7-day submission cooldown
  last_seen_at:              ISODate | null;
  created_at:                ISODate;
  updated_at:                ISODate;
}

// =============================================================================
// UserPreferences
// Mirrors: public.user_preferences
// =============================================================================

export type DigestFrequency = 'daily' | 'weekly';

export interface UserPreferences {
  id:      UUID;
  user_id: UUID;

  preferred_categories:  number[] | null;     // category IDs
  preferred_viral_tiers: (1 | 2 | 3)[] | null;
  notification_enabled:  boolean;
  email_digest_enabled:  boolean;
  digest_frequency:      DigestFrequency | null;

  created_at: ISODate;
  updated_at: ISODate;
}

// =============================================================================
// UserSubmission
// Mirrors: public.user_submissions
// =============================================================================

export type SubmissionStatus = 'pending' | 'approved' | 'rejected';

export interface UserSubmission {
  id:          UUID;
  user_id:     UUID;
  category_id: number | null;

  title:           string;
  url:             string | null;
  description:     string | null;
  status:          SubmissionStatus;
  moderator_notes: string | null;
  reviewed_by:     UUID | null;
  reviewed_at:     ISODate | null;

  created_at: ISODate;
  updated_at: ISODate;

  // Joined relations
  category?: Category;
  user?:     UserProfile;
}

// =============================================================================
// Database — full typed schema (used by Supabase client generics)
// =============================================================================

export interface Database {
  public: {
    Tables: {
      categories: {
        Row:    Category;
        Insert: Omit<Category, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Category, 'id' | 'created_at' | 'updated_at'>>;
      };
      runs_log: {
        Row:    BatchRun;
        Insert: Omit<BatchRun, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<BatchRun, 'id' | 'created_at' | 'updated_at'>>;
      };
      trending_topics: {
        Row:    TrendingTopic;
        Insert: Omit<TrendingTopic, 'id' | 'created_at' | 'updated_at' | 'category'>;
        Update: Partial<Omit<TrendingTopic, 'id' | 'created_at' | 'updated_at' | 'category'>>;
      };
      viral_predictions: {
        Row:    ViralPrediction;
        Insert: Omit<ViralPrediction, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<ViralPrediction, 'id' | 'created_at' | 'updated_at'>>;
      };
      distribution_log: {
        Row:    DistributionLog;
        Insert: Omit<DistributionLog, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<DistributionLog, 'id' | 'created_at' | 'updated_at'>>;
      };
      user_profiles: {
        Row:    UserProfile;
        // id is required (must match auth.users.id); fields with DB defaults are optional.
        Insert: {
          id:                        UUID;
          email:                     string;
          display_name?:             string | null;
          avatar_url?:               string | null;
          is_admin?:                 boolean;
          is_minor?:                 boolean;
          is_active?:                boolean;
          ccpa_opt_out?:             boolean;
          weekly_submission_used_at?: ISODate | null;
          last_seen_at?:             ISODate | null;
        };
        Update: Partial<Omit<UserProfile, 'id' | 'created_at' | 'updated_at'>>;
      };
      user_preferences: {
        Row:    UserPreferences;
        // user_id is required; all other fields have DB defaults so are optional.
        Insert: {
          user_id:                UUID;
          id?:                    UUID;
          preferred_categories?:  number[] | null;
          preferred_viral_tiers?: (1 | 2 | 3)[] | null;
          notification_enabled?:  boolean;
          email_digest_enabled?:  boolean;
          digest_frequency?:      DigestFrequency | null;
        };
        Update: Partial<Omit<UserPreferences, 'id' | 'created_at' | 'updated_at'>>;
      };
      user_submissions: {
        Row:    UserSubmission;
        // user_id and title are required; everything else has defaults or is nullable.
        Insert: {
          user_id:          UUID;
          title:            string;
          category_id?:     number | null;
          url?:             string | null;
          description?:     string | null;
          status?:          SubmissionStatus;
          moderator_notes?: string | null;
          reviewed_by?:     UUID | null;
          reviewed_at?:     ISODate | null;
        };
        Update: Partial<Omit<UserSubmission, 'id' | 'created_at' | 'updated_at' | 'category' | 'user'>>;
      };
    };
  };
}
