'use strict';
// =============================================================================
// setup-supabase-webhooks.js
// Registers a database webhook on INSERT to public.trending_topics using
// pg_net (pre-installed on every Supabase project).
//
// How it works:
//   Creates a Postgres trigger function that calls net.http_post() via pg_net,
//   then attaches that function as an AFTER INSERT trigger on trending_topics.
//   This is exactly what the Supabase Dashboard does under the hood.
//
// Execution strategy (tried in order):
//   1. Management API  POST /v1/projects/{ref}/database/query  (run DDL SQL)
//   2. Fallback        Print the SQL + Dashboard instructions for manual setup
//
// Requires in .env:
//   SUPABASE_URL          — project URL
//   SUPABASE_ACCESS_TOKEN — personal access token (Management API)
//   PUBLICATION_DOMAIN    — e.g. thenewslane.com
//   WEBHOOK_SECRET        — shared secret for x-webhook-secret header
// =============================================================================

const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const {
  SUPABASE_URL,
  SUPABASE_ACCESS_TOKEN,
  PUBLICATION_DOMAIN,
  WEBHOOK_SECRET,
} = process.env;

const missing = ['SUPABASE_URL', 'SUPABASE_ACCESS_TOKEN', 'PUBLICATION_DOMAIN'].filter(
  (k) => !process.env[k]?.trim(),
);
if (missing.length) {
  console.error(`\n❌  Missing required env vars: ${missing.join(', ')}`);
  process.exit(1);
}

const projectRef = new URL(SUPABASE_URL).hostname.split('.')[0];
const MANAGEMENT_API = 'https://api.supabase.com/v1';
const WEBHOOK_ENDPOINT = `https://${PUBLICATION_DOMAIN}/api/webhooks/new-topic`;

// ---------------------------------------------------------------------------
// Build the SQL that creates the pg_net webhook trigger.
// Using EXCEPTION block so a failed HTTP call never blocks an INSERT.
// The secret is embedded at SQL-generation time (not stored in Postgres config).
// ---------------------------------------------------------------------------
function buildWebhookSQL(endpoint, secret) {
  const secretHeader = secret?.trim()
    ? `, 'x-webhook-secret', '${secret.trim()}'`
    : '';

  return `
-- ── Step 1: Ensure pg_net extension is enabled ────────────────────────────
CREATE EXTENSION IF NOT EXISTS pg_net;

-- ── Step 2: Trigger function ───────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.handle_trending_topic_insert()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  PERFORM net.http_post(
    url     := '${endpoint}',
    body    := jsonb_build_object(
                 'type',   'INSERT',
                 'table',  'trending_topics',
                 'schema', 'public',
                 'record', row_to_json(NEW)
               )::text,
    headers := jsonb_build_object(
                 'Content-Type', 'application/json'
                 ${secretHeader}
               )
  );
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  -- Never let a webhook failure block the INSERT
  RAISE WARNING 'trending_topics webhook failed: %', SQLERRM;
  RETURN NEW;
END;
$$;

-- ── Step 3: Attach trigger (idempotent via DROP IF EXISTS) ─────────────────
DROP TRIGGER IF EXISTS trg_on_trending_topic_insert ON public.trending_topics;

CREATE TRIGGER trg_on_trending_topic_insert
  AFTER INSERT ON public.trending_topics
  FOR EACH ROW EXECUTE FUNCTION public.handle_trending_topic_insert();
`.trim();
}

// ---------------------------------------------------------------------------
// Strategy 1: Management API database query endpoint
// POST /v1/projects/{ref}/database/query
// ---------------------------------------------------------------------------
async function tryManagementApiQuery(sql) {
  process.stdout.write('  Strategy 1: Management API /database/query ... ');

  const res = await fetch(
    `${MANAGEMENT_API}/projects/${projectRef}/database/query`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${SUPABASE_ACCESS_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: sql }),
    },
  );

  if (res.ok) {
    console.log('✓');
    return true;
  }

  const body = await res.text().catch(() => '');
  console.log(`✗  (${res.status})`);
  if (body) console.log(`    ${body.slice(0, 120)}`);
  return false;
}

// ---------------------------------------------------------------------------
// Strategy 2: Print SQL + manual instructions
// ---------------------------------------------------------------------------
function printManualInstructions(sql) {
  console.log('');
  console.log('  ┌─────────────────────────────────────────────────────────┐');
  console.log('  │  Manual setup — copy the SQL below into the SQL Editor  │');
  console.log('  └─────────────────────────────────────────────────────────┘');
  console.log('');
  console.log('  Dashboard path:');
  console.log(`  https://supabase.com/dashboard/project/${projectRef}/sql/new`);
  console.log('');
  console.log('  ── SQL to run ────────────────────────────────────────────');
  console.log('');
  // Indent each SQL line for readability
  sql.split('\n').forEach((line) => console.log(`  ${line}`));
  console.log('');
  console.log('  ── Alternative: Dashboard → Database → Webhooks → Create ─');
  console.log('');
  console.log('  Name    : on_trending_topic_insert');
  console.log('  Table   : public.trending_topics');
  console.log('  Events  : INSERT');
  console.log('  Method  : POST');
  console.log(`  URL     : ${WEBHOOK_ENDPOINT}`);
  if (WEBHOOK_SECRET?.trim()) {
    console.log(`  Header  : x-webhook-secret: ${WEBHOOK_SECRET.trim()}`);
  }
  console.log('');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log('\n┌─────────────────────────────────────────────┐');
  console.log('│  Supabase Database Webhooks — Setup          │');
  console.log('└─────────────────────────────────────────────┘');
  console.log(`  Project  : ${projectRef}`);
  console.log(`  Endpoint : ${WEBHOOK_ENDPOINT}`);
  console.log(`  Secret   : ${WEBHOOK_SECRET?.trim() ? 'set ✓' : 'NOT SET ⚠ (set WEBHOOK_SECRET in .env)'}`);
  console.log('');

  if (!WEBHOOK_SECRET?.trim()) {
    console.warn('  ⚠  WEBHOOK_SECRET not set — the webhook will fire without');
    console.warn('     request verification. Generate one with:');
    console.warn('     openssl rand -hex 32');
    console.warn('');
  }

  const sql = buildWebhookSQL(WEBHOOK_ENDPOINT, WEBHOOK_SECRET);

  const success = await tryManagementApiQuery(sql);

  if (success) {
    console.log('');
    console.log('  ✓ Trigger function  public.handle_trending_topic_insert  created');
    console.log('  ✓ Trigger           trg_on_trending_topic_insert  attached');
    console.log(`  ✓ Fires on INSERT → trending_topics → POST ${WEBHOOK_ENDPOINT}`);
    console.log('');
    console.log('✅  Webhooks setup complete.\n');
    return;
  }

  // Management API query endpoint unavailable — print SQL for manual setup
  console.log('');
  console.log('  The Management API query endpoint is not available on this plan.');
  console.log('  The webhook SQL has been generated — run it using one of the');
  console.log('  two methods below (both take under 60 seconds):');
  printManualInstructions(sql);
  console.log('✅  Webhook SQL generated. Complete setup manually using the SQL above.\n');
  // Exit 0 — the script did everything it can; manual step is clearly documented
}

main().catch((err) => {
  console.error('\n❌  Webhooks setup failed:', err.message);
  process.exit(1);
});
