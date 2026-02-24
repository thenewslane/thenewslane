#!/usr/bin/env node
/**
 * test-sitemap.js
 *
 * Fetches the sitemap and reports:
 *   • Total URLs
 *   • Most recent article date
 *   • Any URLs that return 404
 *
 * Usage:
 *   node scripts/test-sitemap.js [BASE_URL]
 *
 * Examples:
 *   node scripts/test-sitemap.js https://thenewslane.com
 *   node scripts/test-sitemap.js http://localhost:3000
 *
 * Exit code 0 = no 404s; non-zero = one or more URLs returned 404.
 */

const https = require('https');
const http  = require('http');

const BASE_URL = process.argv[2] || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

function fetch(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client.get(url, { timeout: 15000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => resolve({ status: res.statusCode, body }));
    }).on('error', reject);
  });
}

function head(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    const u = new URL(url);
    const opts = { hostname: u.hostname, path: u.pathname + u.search, method: 'HEAD', timeout: 10000 };
    const req = client.request(opts, (res) => resolve(res.statusCode));
    req.on('error', reject);
    req.end();
  });
}

async function main() {
  console.log(`\nSitemap Test — ${BASE_URL}\n${'─'.repeat(50)}`);

  let body;
  try {
    const res = await fetch(`${BASE_URL}/sitemap.xml`);
    if (res.status !== 200) {
      console.error(`Failed to fetch sitemap: HTTP ${res.status}`);
      process.exit(1);
    }
    body = res.body;
  } catch (e) {
    console.error('Fetch sitemap error:', e.message);
    process.exit(1);
  }

  const urlMatches = [...body.matchAll(/<loc>([^<]+)<\/loc>/g)];
  const urls = urlMatches.map((m) => m[1]);
  const total = urls.length;
  console.log(`Total URLs: ${total}`);

  const articleDates = [];
  const urlBlocks = body.split(/<url>/i);
  for (const block of urlBlocks) {
    const loc = block.match(/<loc>([^<]+)<\/loc>/);
    const lastmod = block.match(/<lastmod>([^<]+)<\/lastmod>/);
    if (loc && loc[1] && /\/trending\/[^/]+$/.test(loc[1])) {
      articleDates.push({ url: loc[1], lastmod: lastmod ? lastmod[1] : '' });
    }
  }
  if (articleDates.length > 0) {
    const withDate = articleDates.filter((a) => a.lastmod);
    const sorted = withDate.sort((a, b) => new Date(b.lastmod) - new Date(a.lastmod));
    const mostRecent = sorted[0];
    console.log(`Most recent article date: ${mostRecent.lastmod} (${mostRecent.url})`);
  } else {
    console.log('Most recent article date: (no article URLs in sitemap)');
  }

  console.log('\nChecking for 404s...');
  const notFounds = [];
  for (const url of urls) {
    try {
      const status = await head(url);
      if (status === 404) notFounds.push(url);
    } catch {
      notFounds.push(url);
    }
  }

  if (notFounds.length > 0) {
    console.log(`\n❌ URLs returning 404 (${notFounds.length}):`);
    notFounds.forEach((u) => console.log(`   ${u}`));
    console.log('');
    process.exit(1);
  }

  console.log('✅ No 404s detected.\n');
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
