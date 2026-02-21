'use strict';
// =============================================================================
// setup-supabase-auth.js
// Configures Supabase Auth via the Management API:
//   • Enables email/password provider
//   • Sets minimum password length to 8
//   • Sets site_url and allowed redirect URLs from PUBLICATION_DOMAIN
//   • Configures session lifetime and security defaults
//
// Requires in .env:
//   SUPABASE_URL          — project URL
//   SUPABASE_ACCESS_TOKEN — personal access token (Management API)
//   PUBLICATION_DOMAIN    — e.g. thenewslane.com
// =============================================================================

const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

// ---------------------------------------------------------------------------
// Validate env
// ---------------------------------------------------------------------------
const {
  SUPABASE_URL,
  SUPABASE_ACCESS_TOKEN,
  PUBLICATION_DOMAIN,
} = process.env;

const missing = ['SUPABASE_URL', 'SUPABASE_ACCESS_TOKEN', 'PUBLICATION_DOMAIN'].filter(
  (k) => !process.env[k]?.trim(),
);
if (missing.length) {
  console.error(`\n❌  Missing required env vars: ${missing.join(', ')}`);
  if (missing.includes('SUPABASE_ACCESS_TOKEN')) {
    console.error('    Get your personal access token at:');
    console.error('    https://supabase.com/dashboard/account/tokens');
  }
  process.exit(1);
}

const projectRef = new URL(SUPABASE_URL).hostname.split('.')[0];
const MANAGEMENT_API = 'https://api.supabase.com/v1';

// ---------------------------------------------------------------------------
// Auth configuration payload
// Reference: https://api.supabase.com/v1#tag/projects/PATCH/v1/projects/{ref}/config/auth
// ---------------------------------------------------------------------------
const AUTH_CONFIG = {
  // ── Email provider ─────────────────────────────────────────────────────────
  external_email_enabled: true,
  mailer_autoconfirm: false,           // require email verification on signup

  // ── Password policy ────────────────────────────────────────────────────────
  password_min_length: 8,

  // ── Site URLs and redirect whitelist ───────────────────────────────────────
  // site_url is the primary URL for magic links and OAuth callbacks.
  // uri_allow_list controls which URLs auth redirects are permitted to use.
  site_url: `https://${PUBLICATION_DOMAIN}`,
  // The Management API expects a comma-separated string, not an array.
  uri_allow_list: [
    `https://${PUBLICATION_DOMAIN}`,
    `https://${PUBLICATION_DOMAIN}/**`,
    `https://www.${PUBLICATION_DOMAIN}`,
    `https://www.${PUBLICATION_DOMAIN}/**`,
    'http://localhost:3000',            // Next.js dev
    'http://localhost:3000/**',
    'http://localhost:19006',           // Expo web dev
    'http://localhost:19006/**',
    'exp://localhost:8081',             // Expo Go on device
    'exp://localhost:8081/**',
  ].join(','),

  // ── JWT lifetime ───────────────────────────────────────────────────────────
  jwt_exp: 3600,                        // access token: 1 hour (seconds)
  // sessions_timebox and sessions_inactivity_timeout are Pro plan features.
  // Configure them in Dashboard → Auth → Sessions after upgrading.

  // ── Disable anonymous sign-ins ─────────────────────────────────────────────
  // This is a content platform — users must register to personalise their feed.
  external_anonymous_users_enabled: false,

  // ── Disable unused OAuth providers (enable individually as needed) ─────────
  external_google_enabled: false,
  external_github_enabled: false,
  external_twitter_enabled: false,
  external_facebook_enabled: false,
  external_apple_enabled: false,

  // Note: rate_limit_email_sent and rate_limit_sms_sent require a custom SMTP
  // setup (paid plan). They are omitted here so the free-tier project accepts
  // this request. Configure them in Dashboard → Auth → Rate Limits once SMTP
  // is enabled.
};

// ---------------------------------------------------------------------------
// Pretty-print the settings we're applying
// ---------------------------------------------------------------------------
function summarise(config) {
  const lines = [
    ['Email provider',        config.external_email_enabled ? 'enabled' : 'disabled'],
    ['Email auto-confirm',    config.mailer_autoconfirm ? 'yes (insecure)' : 'no (requires verification)'],
    ['Min password length',   config.password_min_length],
    ['Site URL',              config.site_url],
    ['Redirect URLs',         `${config.uri_allow_list.split(',').length} entries`],
    ['JWT access expiry',     `${config.jwt_exp / 3600}h`],
    ['Anonymous sign-ins',    config.external_anonymous_users_enabled ? 'enabled' : 'disabled'],
  ];
  for (const [label, value] of lines) {
    console.log(`    ${label.padEnd(26)} ${value}`);
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log('\n┌─────────────────────────────────────────────┐');
  console.log('│  Supabase Auth — Configuration               │');
  console.log('└─────────────────────────────────────────────┘');
  console.log(`  Project : ${projectRef}`);
  console.log(`  Domain  : ${PUBLICATION_DOMAIN}`);
  console.log('');
  console.log('  Applying:');
  summarise(AUTH_CONFIG);
  console.log('');

  const res = await fetch(
    `${MANAGEMENT_API}/projects/${projectRef}/config/auth`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${SUPABASE_ACCESS_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(AUTH_CONFIG),
    },
  );

  if (!res.ok) {
    const body = await res.text().catch(() => '(unreadable body)');
    throw new Error(`Management API returned ${res.status}: ${body}`);
  }

  const result = await res.json();

  // Confirm what Supabase echoed back for the key fields
  console.log('  Confirmed by Supabase:');
  console.log(`    site_url             ${result.site_url ?? '(not returned)'}`);
  console.log(`    password_min_length  ${result.password_min_length ?? '(not returned)'}`);
  console.log('');
  console.log('✅  Auth configuration complete.\n');
}

main().catch((err) => {
  console.error('\n❌  Auth configuration failed:', err.message);
  if (err.message.includes('401') || err.message.includes('403')) {
    console.error('    Check that SUPABASE_ACCESS_TOKEN is valid and not expired.');
    console.error('    https://supabase.com/dashboard/account/tokens');
  }
  process.exit(1);
});
