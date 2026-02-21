'use strict';
// =============================================================================
// setup-all.js
// Master setup runner — executes all four Supabase setup scripts in sequence.
//
// Usage:
//   node scripts/setup-all.js          (from project root)
//   npm run setup                      (from scripts/ directory)
//
// Pre-flight checks performed before running any script:
//   • Node.js >= 18 (required for built-in fetch)
//   • .env file exists and is readable
//   • SUPABASE_URL and SUPABASE_SERVICE_KEY are present
//   • SUPABASE_ACCESS_TOKEN is present (Management API)
// =============================================================================

const path = require('path');
const fs = require('fs');
const { spawnSync } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '..');
const ENV_FILE = path.join(ROOT_DIR, '.env');

// ---------------------------------------------------------------------------
// ANSI colour helpers (degrade gracefully if stdout is not a TTY)
// ---------------------------------------------------------------------------
const isTTY = process.stdout.isTTY;
const c = {
  reset:  isTTY ? '\x1b[0m'  : '',
  bold:   isTTY ? '\x1b[1m'  : '',
  green:  isTTY ? '\x1b[32m' : '',
  red:    isTTY ? '\x1b[31m' : '',
  yellow: isTTY ? '\x1b[33m' : '',
  cyan:   isTTY ? '\x1b[36m' : '',
  grey:   isTTY ? '\x1b[90m' : '',
};

function ok(msg)   { console.log(`  ${c.green}✓${c.reset}  ${msg}`); }
function warn(msg) { console.log(`  ${c.yellow}⚠${c.reset}  ${msg}`); }
function fail(msg) { console.log(`  ${c.red}✗${c.reset}  ${msg}`); }

// ---------------------------------------------------------------------------
// Pre-flight checks
// ---------------------------------------------------------------------------
function preflight() {
  console.log(`${c.bold}Pre-flight checks${c.reset}`);
  console.log('─'.repeat(54));

  let allPassed = true;

  // Node version
  const [major] = process.versions.node.split('.').map(Number);
  if (major >= 18) {
    ok(`Node.js ${process.version}  (native fetch available)`);
  } else {
    fail(`Node.js ${process.version} — requires >= 18.0.0`);
    allPassed = false;
  }

  // .env file
  if (fs.existsSync(ENV_FILE)) {
    ok(`.env found at ${ENV_FILE}`);
  } else {
    fail(`.env not found at ${ENV_FILE}`);
    console.error('     Create it by copying docs/.env.template and filling in your values.');
    allPassed = false;
  }

  // Load .env for the remaining checks
  try {
    require('dotenv').config({ path: ENV_FILE });
  } catch {
    warn('dotenv not installed — env var checks skipped');
  }

  // Required env vars
  const REQUIRED = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY'];
  for (const key of REQUIRED) {
    if (process.env[key]?.trim()) {
      ok(`${key}  set`);
    } else {
      fail(`${key}  MISSING`);
      allPassed = false;
    }
  }

  // Access token — Management API only; warn rather than abort
  if (process.env.SUPABASE_ACCESS_TOKEN?.trim()) {
    ok('SUPABASE_ACCESS_TOKEN  set  (Management API ready)');
  } else {
    warn(
      'SUPABASE_ACCESS_TOKEN  not set — Auth config, CORS, and Webhook ' +
      'setup require this. Get it at supabase.com/dashboard/account/tokens',
    );
  }

  if (!allPassed) {
    console.error(`\n${c.red}Pre-flight failed. Fix the issues above then re-run.${c.reset}\n`);
    process.exit(1);
  }

  console.log('');
}

// ---------------------------------------------------------------------------
// Script pipeline
// ---------------------------------------------------------------------------
const SCRIPTS = [
  {
    label: 'Storage Buckets',
    file:  'setup-supabase-storage.js',
    desc:  'Creates thumbnails, videos, avatars buckets + CORS',
  },
  {
    label: 'Auth Settings',
    file:  'setup-supabase-auth.js',
    desc:  'Email provider, password policy, redirect URLs, sessions',
  },
  {
    label: 'Edge Functions',
    file:  'setup-supabase-functions.js',
    desc:  'Deploys delete-user-data (GDPR right to erasure)',
  },
  {
    label: 'DB Webhooks',
    file:  'setup-supabase-webhooks.js',
    desc:  'Registers INSERT hook on trending_topics → push notifications',
  },
];

// ---------------------------------------------------------------------------
// Run a single script and capture its outcome
// ---------------------------------------------------------------------------
function runScript(script, index) {
  const n = `[${index + 1}/${SCRIPTS.length}]`;
  console.log(`${c.bold}${n} ${script.label}${c.reset}  ${c.grey}${script.desc}${c.reset}`);
  console.log('─'.repeat(54));

  const scriptPath = path.join(__dirname, script.file);
  const start = Date.now();

  const result = spawnSync(process.execPath, [scriptPath], {
    stdio: 'inherit',
    cwd: ROOT_DIR,
    env: process.env,
  });

  const elapsed = ((Date.now() - start) / 1000).toFixed(1);

  if (result.status === 0) {
    console.log(`${c.green}  ✓ Passed${c.reset}  ${c.grey}(${elapsed}s)${c.reset}`);
    console.log('');
    return { ...script, status: 'passed', elapsed };
  }

  console.log(`${c.red}  ✗ Failed${c.reset}  ${c.grey}(${elapsed}s, exit code ${result.status})${c.reset}`);
  console.log('');
  return { ...script, status: 'failed', elapsed };
}

// ---------------------------------------------------------------------------
// Summary table
// ---------------------------------------------------------------------------
function printSummary(results) {
  const passed = results.filter((r) => r.status === 'passed').length;
  const failed = results.filter((r) => r.status === 'failed').length;

  console.log('═'.repeat(54));
  console.log(`${c.bold}SETUP SUMMARY${c.reset}`);
  console.log('═'.repeat(54));

  for (const r of results) {
    const icon = r.status === 'passed'
      ? `${c.green}✓${c.reset}`
      : `${c.red}✗${c.reset}`;
    console.log(`  ${icon}  ${r.label.padEnd(22)} ${c.grey}${r.elapsed}s${c.reset}`);
  }

  console.log('─'.repeat(54));
  console.log(`  ${c.bold}Passed:${c.reset} ${passed}/${SCRIPTS.length}`);

  if (failed > 0) {
    console.log(`  ${c.red}${c.bold}Failed:${c.reset} ${failed}/${SCRIPTS.length}`);
    console.log('');
    console.log('  Common causes:');
    console.log('  • SUPABASE_ACCESS_TOKEN missing or expired');
    console.log('  • Supabase CLI not installed (Edge Functions only)');
    console.log('  • Network timeout reaching api.supabase.com');
    console.log('  • Project ref mismatch (check SUPABASE_URL)');
    console.log('');
    console.log('  Re-run a single step with:');
    console.log('  node scripts/setup-supabase-<name>.js');
    console.log('');
    process.exit(1);
  }

  console.log('');
  console.log(`  ${c.green}${c.bold}All setup steps completed successfully!${c.reset}`);
  console.log('');
  console.log('  Next steps:');
  console.log('  1. Fill in SUPABASE_ACCESS_TOKEN in .env if you haven\'t already');
  console.log('  2. Run  node scripts/seed.js  (once schema.sql is applied)');
  console.log('  3. Deploy the Next.js app and update PUBLICATION_DOMAIN webhooks');
  console.log('  4. Set Edge Function secrets in the Supabase Dashboard');
  console.log('');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
function main() {
  console.log('');
  console.log('╔══════════════════════════════════════════════════════╗');
  console.log('║   Trending News Platform — Supabase Setup Runner     ║');
  console.log('╚══════════════════════════════════════════════════════╝');
  console.log('');

  preflight();

  const results = [];
  for (let i = 0; i < SCRIPTS.length; i++) {
    results.push(runScript(SCRIPTS[i], i));
  }

  printSummary(results);
}

main();
