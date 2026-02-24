#!/usr/bin/env node
/**
 * Run Lighthouse CI against 3 article pages from the sitemap.
 *
 * 1. Builds the web app
 * 2. Starts the server in the background
 * 3. Fetches sitemap, picks 3 article URLs
 * 4. Runs lhci collect (no server start) and reports scores
 *
 * Usage: from repo root: node scripts/run-lighthouse-ci.js
 * Requires: npm run build and lhci in apps/web (npm install -g @lhci/cli or npx)
 */

const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

const BASE = 'http://localhost:3000';
const WEB_DIR = path.join(__dirname, '..', 'apps', 'web');

function fetch(url) {
  return new Promise((resolve, reject) => {
    http.get(url, { timeout: 10000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => resolve({ status: res.statusCode, body }));
    }).on('error', reject);
  });
}

function waitForServer(maxAttempts = 30) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const tick = () => {
      attempts++;
      fetch(BASE)
        .then((r) => (r.status === 200 ? resolve() : tick()))
        .catch(() => {
          if (attempts >= maxAttempts) reject(new Error('Server did not become ready'));
          else setTimeout(tick, 1000);
        });
    };
    tick();
  });
}

function getArticleUrlsFromSitemap(body) {
  const urls = [];
  const urlBlocks = body.split(/<url>/i);
  for (const block of urlBlocks) {
    const loc = block.match(/<loc>([^<]+)<\/loc>/);
    if (loc && /\/trending\/[^/]+$/.test(loc[1])) urls.push(loc[1]);
  }
  return urls.slice(0, 3);
}

async function main() {
  console.log('\nLighthouse CI — build and run\n' + '─'.repeat(50));

  // 1. Build
  console.log('Building web app...');
  const build = spawn('npm', ['run', 'build'], {
    cwd: WEB_DIR,
    stdio: 'inherit',
    shell: true,
  });
  await new Promise((resolve, reject) => {
    build.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`build exited ${code}`))));
  });

  // 2. Start server
  const server = spawn('npm', ['run', 'start'], {
    cwd: WEB_DIR,
    stdio: 'pipe',
    shell: true,
  });
  let serverStderr = '';
  server.stderr.on('data', (d) => { serverStderr += d; });

  try {
    await waitForServer();
  } catch (e) {
    server.kill();
    console.error('Server failed to start. Stderr:', serverStderr.slice(-500));
    process.exit(1);
  }

  let urls = [BASE];
  try {
    const { status, body } = await fetch(`${BASE}/sitemap.xml`);
    if (status === 200) {
      const articleUrls = getArticleUrlsFromSitemap(body);
      if (articleUrls.length >= 1) urls = [BASE, ...articleUrls.slice(0, 2)];
      if (articleUrls.length >= 3) urls = [BASE, ...articleUrls.slice(0, 3)];
    }
  } catch (e) {
    console.warn('Could not fetch sitemap, using base URL only:', e.message);
  }

  // Use 3 article pages (no homepage) if we have 3 articles
  const articleOnly = urls.filter((u) => /\/trending\//.test(u));
  const toTest = articleOnly.length >= 3 ? articleOnly.slice(0, 3) : urls.slice(0, 3);
  console.log('URLs to test:', toTest.join(', '));

  const env = {
    ...process.env,
    LHCI_URLS: toTest.join(','),
    LHCI_SKIP_SERVER: '1',
    LHCI_BASE_URL: BASE,
  };

  const lhci = spawn('npx', ['lhci', 'autorun', '--config.path=./lighthouserc.js'], {
    cwd: WEB_DIR,
    env,
    stdio: 'inherit',
    shell: true,
  });

  const code = await new Promise((resolve) => lhci.on('close', resolve));
  server.kill();
  process.exit(code);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
