'use strict';
// =============================================================================
// setup-supabase-functions.js
// Deploys the delete-user-data Supabase Edge Function.
//
// The TypeScript source lives at:
//   supabase/functions/delete-user-data/index.ts
//
// Deployment strategy (tried in order):
//   1. Supabase CLI  — `supabase functions deploy` (preferred; handles bundling)
//   2. Instructions  — prints the manual deployment command if CLI is absent
//
// Requires in .env:
//   SUPABASE_URL          — used to extract the project ref
//   SUPABASE_ACCESS_TOKEN — needed by the Supabase CLI for authentication
//
// Install Supabase CLI:
//   npm install -g supabase
//   brew install supabase/tap/supabase
// =============================================================================

const path = require('path');
const fs = require('fs');
const { execSync, spawnSync } = require('child_process');

require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const { SUPABASE_URL, SUPABASE_ACCESS_TOKEN } = process.env;

if (!SUPABASE_URL?.trim()) {
  console.error('\n❌  Missing required env var: SUPABASE_URL');
  process.exit(1);
}

const projectRef = new URL(SUPABASE_URL).hostname.split('.')[0];
const ROOT_DIR = path.resolve(__dirname, '..');
const FUNCTION_NAME = 'delete-user-data';
const FUNCTION_DIR = path.join(ROOT_DIR, 'supabase', 'functions', FUNCTION_NAME);
const FUNCTION_FILE = path.join(FUNCTION_DIR, 'index.ts');

// ---------------------------------------------------------------------------
// Verify the source file exists
// ---------------------------------------------------------------------------
function verifySource() {
  if (!fs.existsSync(FUNCTION_FILE)) {
    throw new Error(
      `Edge function source not found at:\n  ${FUNCTION_FILE}\n` +
      'Ensure supabase/functions/delete-user-data/index.ts exists.',
    );
  }
  const bytes = fs.statSync(FUNCTION_FILE).size;
  console.log(`  ✓ Source file found  (${bytes} bytes)`);
  console.log(`    ${FUNCTION_FILE}`);
}

// ---------------------------------------------------------------------------
// Check if the Supabase CLI is installed
// ---------------------------------------------------------------------------
function cliVersion() {
  const result = spawnSync('supabase', ['--version'], { encoding: 'utf8' });
  if (result.error || result.status !== 0) return null;
  return result.stdout.trim();
}

// ---------------------------------------------------------------------------
// Attempt deployment via CLI
// ---------------------------------------------------------------------------
function deployViaCli() {
  const version = cliVersion();
  if (!version) {
    console.log('\n  ⚠  Supabase CLI not found. Skipping automatic deployment.');
    console.log('');
    console.log('  To deploy manually, install the CLI and run:');
    console.log('');
    console.log('    npm install -g supabase          # or: brew install supabase/tap/supabase');
    console.log('    supabase login');
    console.log(`    supabase functions deploy ${FUNCTION_NAME} --project-ref ${projectRef}`);
    console.log('');
    console.log('  Edge function secrets (set these in the Supabase Dashboard or via CLI):');
    console.log(`    supabase secrets set SUPABASE_URL=${SUPABASE_URL} --project-ref ${projectRef}`);
    console.log(`    supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<your-service-key> --project-ref ${projectRef}`);
    return false;
  }

  console.log(`\n  Supabase CLI detected: ${version}`);
  console.log(`  Deploying '${FUNCTION_NAME}'...`);
  console.log('');

  // Build the deploy command
  // --no-verify-jwt is intentionally omitted so the function requires a valid JWT.
  const args = [
    'functions', 'deploy', FUNCTION_NAME,
    '--project-ref', projectRef,
  ];

  // If the access token is available, pass it so the CLI doesn't prompt
  const env = { ...process.env };
  if (SUPABASE_ACCESS_TOKEN?.trim()) {
    env.SUPABASE_ACCESS_TOKEN = SUPABASE_ACCESS_TOKEN.trim();
  }

  const result = spawnSync('supabase', args, {
    stdio: 'inherit',
    cwd: ROOT_DIR,
    env,
  });

  if (result.status !== 0) {
    throw new Error(`supabase functions deploy exited with code ${result.status}`);
  }

  console.log('');
  console.log(`  ✓ Function '${FUNCTION_NAME}' deployed to project ${projectRef}`);
  return true;
}

// ---------------------------------------------------------------------------
// Print the required Edge Function secrets reminder
// ---------------------------------------------------------------------------
function printSecretsReminder() {
  console.log('');
  console.log('  ─── Required Edge Function Secrets ───────────────────────────────');
  console.log('  The function reads these from Deno.env at runtime. Set them via:');
  console.log('  Dashboard → Edge Functions → delete-user-data → Secrets  OR');
  console.log(`  supabase secrets set <KEY>=<VALUE> --project-ref ${projectRef}`);
  console.log('');
  console.log('    SUPABASE_URL               (already set by Supabase automatically)');
  console.log('    SUPABASE_SERVICE_ROLE_KEY  (your service role JWT)');
  console.log('  ───────────────────────────────────────────────────────────────────');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log('\n┌─────────────────────────────────────────────┐');
  console.log('│  Supabase Edge Functions — Setup             │');
  console.log('└─────────────────────────────────────────────┘');
  console.log(`  Project  : ${projectRef}`);
  console.log(`  Function : ${FUNCTION_NAME}`);
  console.log('');

  verifySource();
  deployViaCli();
  printSecretsReminder();

  console.log('');
  console.log('✅  Functions setup complete.\n');
}

main().catch((err) => {
  console.error('\n❌  Functions setup failed:', err.message);
  process.exit(1);
});
