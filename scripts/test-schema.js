#!/usr/bin/env node
/**
 * test-schema.js
 *
 * Fetches 3 article pages from the published site and validates that each
 * contains the expected JSON-LD schema markup (NewsArticle + VideoObject).
 *
 * Usage:
 *   node scripts/test-schema.js [BASE_URL]
 *
 * Examples:
 *   node scripts/test-schema.js https://thenewslane.com
 *   node scripts/test-schema.js http://localhost:3000
 *
 * Exit code 0 = all checks passed; non-zero = failures detected.
 */

const https = require('https');
const http  = require('http');
const { URL } = require('url');

const BASE_URL = process.argv[2] || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fetchPage(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client.get(url, { timeout: 15000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => resolve({ status: res.statusCode, body }));
    }).on('error', reject);
  });
}

function extractJsonLd(html) {
  const schemas = [];
  const re = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match;
  while ((match = re.exec(html)) !== null) {
    try { schemas.push(JSON.parse(match[1])); } catch { /* ignore malformed */ }
  }
  return schemas;
}

function checkNewsArticle(schemas) {
  const article = schemas.find(
    (s) => s['@type'] === 'NewsArticle' || s['@type'] === 'Article',
  );
  if (!article) return { pass: false, reason: 'No NewsArticle/Article schema found' };

  const required = ['headline', 'datePublished', 'author', 'publisher'];
  const missing  = required.filter((k) => !article[k]);
  if (missing.length) return { pass: false, reason: `Missing fields: ${missing.join(', ')}` };

  return { pass: true };
}

function checkVideoObject(schemas) {
  const video = schemas.find((s) => s['@type'] === 'VideoObject');
  if (!video) return { pass: true, skip: 'No VideoObject (page may not have a video)' };

  const required = ['name', 'thumbnailUrl', 'uploadDate'];
  const missing  = required.filter((k) => !video[k]);
  if (missing.length) return { pass: false, reason: `VideoObject missing: ${missing.join(', ')}` };

  if (!video.contentUrl && !video.embedUrl) {
    return { pass: false, reason: 'VideoObject must have contentUrl or embedUrl' };
  }

  return { pass: true };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log(`\nSchema Markup Validator — ${BASE_URL}\n${'─'.repeat(50)}`);

  // Step 1: Fetch the sitemap to discover article slugs
  let slugs = [];
  try {
    const { status, body } = await fetchPage(`${BASE_URL}/sitemap.xml`);
    if (status === 200) {
      const matches = [...body.matchAll(/<loc>(https?:\/\/[^<]+\/trending\/([^<]+))<\/loc>/g)];
      slugs = matches.slice(0, 3).map((m) => ({ url: m[1], slug: m[2] }));
    }
  } catch (e) {
    console.warn('Could not fetch sitemap:', e.message);
  }

  if (slugs.length === 0) {
    console.warn('No article URLs found in sitemap — using homepage only.');
    slugs = [{ url: BASE_URL, slug: '(homepage)' }];
  }

  let totalPass = 0;
  let totalFail = 0;

  for (const { url, slug } of slugs) {
    console.log(`\n📄  ${slug}`);
    console.log(`    URL: ${url}`);

    let status, body;
    try {
      ({ status, body } = await fetchPage(url));
    } catch (e) {
      console.log(`    ❌  Fetch error: ${e.message}`);
      totalFail++;
      continue;
    }

    if (status !== 200) {
      console.log(`    ❌  HTTP ${status}`);
      totalFail++;
      continue;
    }

    const schemas = extractJsonLd(body);
    console.log(`    Found ${schemas.length} JSON-LD block(s)`);

    // NewsArticle check
    const articleResult = checkNewsArticle(schemas);
    if (articleResult.pass) {
      console.log('    ✅  NewsArticle schema — OK');
      totalPass++;
    } else {
      console.log(`    ❌  NewsArticle schema — ${articleResult.reason}`);
      totalFail++;
    }

    // VideoObject check
    const videoResult = checkVideoObject(schemas);
    if (videoResult.skip) {
      console.log(`    ⏭️   VideoObject — ${videoResult.skip}`);
    } else if (videoResult.pass) {
      console.log('    ✅  VideoObject schema — OK');
      totalPass++;
    } else {
      console.log(`    ❌  VideoObject schema — ${videoResult.reason}`);
      totalFail++;
    }
  }

  console.log(`\n${'─'.repeat(50)}`);
  console.log(`Results: ${totalPass} passed, ${totalFail} failed\n`);
  process.exit(totalFail > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
