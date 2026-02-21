'use strict';
// =============================================================================
// setup-supabase-storage.js
// Creates three Supabase Storage buckets (thumbnails, videos, avatars) and
// configures CORS via the Supabase Management API.
//
// Requires in .env:
//   SUPABASE_URL         — project URL
//   SUPABASE_SERVICE_KEY — service role JWT (creates buckets without RLS)
//   SUPABASE_ACCESS_TOKEN— personal access token (Management API for CORS)
//   PUBLICATION_DOMAIN   — e.g. thenewslane.com
// =============================================================================

const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const { createClient } = require('@supabase/supabase-js');

// ---------------------------------------------------------------------------
// Validate env
// ---------------------------------------------------------------------------
const {
  SUPABASE_URL,
  SUPABASE_SERVICE_KEY,
  SUPABASE_ACCESS_TOKEN,
  PUBLICATION_DOMAIN,
} = process.env;

const missing = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'PUBLICATION_DOMAIN'].filter(
  (k) => !process.env[k]?.trim(),
);
if (missing.length) {
  console.error(`\n❌  Missing required env vars: ${missing.join(', ')}`);
  process.exit(1);
}

const projectRef = new URL(SUPABASE_URL).hostname.split('.')[0];
const MANAGEMENT_API = 'https://api.supabase.com/v1';

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
  auth: { autoRefreshToken: false, persistSession: false },
});

// ---------------------------------------------------------------------------
// Bucket definitions
// ---------------------------------------------------------------------------
const BUCKETS = [
  {
    name: 'thumbnails',
    description: 'Flux 1.1 Pro AI-generated topic thumbnails (all tiers)',
    options: {
      public: true,
      allowedMimeTypes: ['image/jpeg', 'image/png', 'image/webp', 'image/gif'],
      fileSizeLimit: 10 * 1024 * 1024, // 10 MB
    },
  },
  {
    name: 'videos',
    description: 'Kling-generated + FFmpeg-assembled videos (Tier 1)',
    options: {
      public: true,
      allowedMimeTypes: ['video/mp4', 'video/webm', 'video/quicktime'],
      // fileSizeLimit is intentionally omitted: the Supabase free tier caps
      // individual uploads at 50 MB at the project level and rejects any
      // bucket-level limit higher than the plan allows. On Pro/Team, set this
      // to your desired cap (e.g. 500 * 1024 * 1024) via the Dashboard →
      // Storage → <bucket> → Configuration after upgrading.
    },
  },
  {
    name: 'avatars',
    description: 'User profile avatars',
    options: {
      public: true,
      allowedMimeTypes: ['image/jpeg', 'image/png', 'image/webp'],
      fileSizeLimit: 2 * 1024 * 1024, // 2 MB
    },
  },
];

// ---------------------------------------------------------------------------
// CORS origins
// localhost entries are stripped in production — include now for dev convenience.
// ---------------------------------------------------------------------------
const CORS_ORIGINS = [
  `https://${PUBLICATION_DOMAIN}`,
  `https://www.${PUBLICATION_DOMAIN}`,
  'http://localhost:3000',    // Next.js dev server
  'http://localhost:19006',   // Expo web dev
  'exp://localhost:8081',     // Expo Go
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
async function managementFetch(endpoint, method, body) {
  const res = await fetch(`${MANAGEMENT_API}${endpoint}`, {
    method,
    headers: {
      Authorization: `Bearer ${SUPABASE_ACCESS_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res;
}

// ---------------------------------------------------------------------------
// Create or update a single bucket
// ---------------------------------------------------------------------------
async function upsertBucket(bucket) {
  process.stdout.write(`  ${bucket.name.padEnd(14)} `);

  const { error } = await supabase.storage.createBucket(bucket.name, bucket.options);

  if (!error) {
    console.log(`✓ created  (${bucket.description})`);
    return;
  }

  // 409 = bucket already exists — update it instead
  const alreadyExists =
    error.message?.toLowerCase().includes('already exists') ||
    error.statusCode === '409' ||
    error.statusCode === 409;

  if (alreadyExists) {
    const { error: updateError } = await supabase.storage.updateBucket(
      bucket.name,
      bucket.options,
    );
    if (updateError) {
      throw new Error(`update failed: ${updateError.message}`);
    }
    console.log(`↻ updated  (already existed, config refreshed)`);
    return;
  }

  throw new Error(error.message);
}

// ---------------------------------------------------------------------------
// Configure CORS via Management API
// ---------------------------------------------------------------------------
async function configureCors() {
  if (!SUPABASE_ACCESS_TOKEN?.trim()) {
    console.log('\n  ⚠  SUPABASE_ACCESS_TOKEN not set — skipping Management API CORS config.');
    console.log('     To configure CORS manually:');
    console.log('     Dashboard → Storage → Configuration → Allowed CORS origins');
    console.log(`     Add: https://${PUBLICATION_DOMAIN}`);
    return;
  }

  process.stdout.write('\n  Configuring CORS allowed origins ... ');

  // The Management API storage config endpoint controls allowed CORS origins
  // for all storage requests originating from the listed domains.
  const res = await managementFetch(`/projects/${projectRef}/config/storage`, 'PATCH', {
    // Supabase Management API field for storage CORS:
    allowed_origins: CORS_ORIGINS,
  });

  if (res.ok) {
    console.log(`✓`);
    console.log('  Allowed origins:');
    CORS_ORIGINS.forEach((o) => console.log(`    • ${o}`));
    return;
  }

  // Non-fatal — surface the error but don't abort
  const body = await res.text().catch(() => '(unreadable body)');
  console.log(`⚠  (${res.status}) ${body}`);
  console.log('  Storage CORS must be configured manually in the Supabase Dashboard.');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log('\n┌─────────────────────────────────────────────┐');
  console.log('│  Supabase Storage — Bucket Setup             │');
  console.log('└─────────────────────────────────────────────┘');
  console.log(`  Project : ${projectRef}`);
  console.log(`  Domain  : ${PUBLICATION_DOMAIN}`);
  console.log('');

  for (const bucket of BUCKETS) {
    await upsertBucket(bucket);
  }

  await configureCors();

  console.log('\n✅  Storage setup complete.\n');
}

main().catch((err) => {
  console.error('\n❌  Storage setup failed:', err.message);
  process.exit(1);
});
