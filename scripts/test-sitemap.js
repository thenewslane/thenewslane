#!/usr/bin/env node
/**
 * test-sitemap.js
 *
 * Fetches /sitemap.xml from the deployed site and reports:
 *   • Total number of URLs
 *   • Most recent <lastmod> date
 *   • Any article URLs that return HTTP 404
 *
 * Usage:
 *   node scripts/test-sitemap.js [BASE_URL]
 *
 * Examples:
 *   node scripts/test-sitemap.js https://thenewslane.com
 *   node scripts/test-sitemap.js http://localhost:3000
 *
 * Exit code 0 = sitemap healthy; non-zero = issues detected.
 */

const https = require('https');
const http  = require('http');

const BASE_URL = process.argv[2] || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fetchUrl(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client.get(url, { timeout: 20000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => resolve({ status: res.statusCode, body }));
    }).on('error', reject);
  });
}

function headUrl(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    const parsedUrl = new URL(url);
    const options = {
      hostname: parsedUrl.hostname,
      port:     parsedUrl.port || (url.startsWith('https') ? 443 : 80),
      path:     parsedUrl.pathname + parsedUrl.search,
      method:   'HEAD',
      timeout:  10000,
    };
    const req = client.request(options, (res) => {
      resolve({ status: res.statusCode });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
    req.end();
  });
}

const { URL } = require('url');

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log(`\nSitemap Validator — ${BASE_URL}\n${'─'.repeat(50)}`);

  // Fetch sitemap
  const sitemapUrl = `${BASE_URL}/sitemap.xml`;
  let sitemapBody;
  try {
    const { status, body } = await fetchUrl(sitemapUrl);
    if (status !== 200) {
      console.error(`❌  /sitemap.xml returned HTTP ${status}`);
      process.exit(1);
    }
    sitemapBody = body;
    console.log(`✅  Fetched sitemap (${Math.round(body.length / 1024)} KB)`);
  } catch (e) {
    console.error(`❌  Could not fetch sitemap: ${e.message}`);
    process.exit(1);
  }

  // Parse <loc> and <lastmod>
  const locMatches     = [...sitemapBody.matchAll(/<loc>(.*?)<\/loc>/g)].map((m) => m[1].trim());
  const lastmodMatches = [...sitemapBody.matchAll(/<lastmod>(.*?)<\/lastmod>/g)].map((m) => m[1].trim());

  console.log(`\n📊  Total URLs in sitemap: ${locMatches.length}`);

  // Most recent lastmod
  if (lastmodMatches.length > 0) {
    const sorted = [...lastmodMatches]
      .filter(Boolean)
      .map((d) => new Date(d))
      .filter((d) => !isNaN(d.getTime()))
      .sort((a, b) => b - a);
    if (sorted.length > 0) {
      console.log(`📅  Most recent lastmod:  ${sorted[0].toISOString()}`);
    }
  }

  // Check for 404s — sample up to 20 URLs to keep runtime reasonable
  const articleUrls = locMatches.filter((u) => u.includes('/trending/'));
  const checkSample = articleUrls.slice(0, 20);

  if (checkSample.length === 0) {
    console.log('\n⏭️   No /trending/ URLs to spot-check.');
  } else {
    console.log(`\n🔍  Spot-checking ${checkSample.length} article URL(s) for 404s…\n`);
    const failures = [];

    await Promise.all(
      checkSample.map(async (url) => {
        try {
          const { status } = await headUrl(url);
          if (status === 404) {
            failures.push({ url, status });
            console.log(`   ❌  404 — ${url}`);
          } else {
            console.log(`   ✅  ${status} — ${url}`);
          }
        } catch (e) {
          failures.push({ url, status: 'error', error: e.message });
          console.log(`   ❌  ERROR — ${url} (${e.message})`);
        }
      }),
    );

    console.log(`\n${'─'.repeat(50)}`);
    if (failures.length === 0) {
      console.log(`✅  All ${checkSample.length} URLs returned non-404 responses.\n`);
      process.exit(0);
    } else {
      console.log(`❌  ${failures.length} URL(s) returned 404 or errors:\n`);
      failures.forEach(({ url, status, error }) =>
        console.log(`   • ${url}  →  ${status}${error ? ` (${error})` : ''}`),
      );
      console.log('');
      process.exit(1);
    }
  }

  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
