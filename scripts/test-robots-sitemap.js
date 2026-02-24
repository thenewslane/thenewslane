#!/usr/bin/env node
/**
 * Test sitemap.xml and robots.txt are accessible and correctly formatted.
 *
 * Usage: node scripts/test-robots-sitemap.js [BASE_URL]
 * Example: node scripts/test-robots-sitemap.js https://thenewslane.com
 *
 * Exit code 0 = both OK; 1 = fetch or format error.
 */

const http = require('http');
const https = require('https');

const BASE = process.argv[2] || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

function fetch(url, redirectCount = 0) {
  const maxRedirects = 3;
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    client.get(url, { timeout: 10000 }, (res) => {
      if ([301, 302, 307, 308].includes(res.statusCode) && res.headers.location && redirectCount < maxRedirects) {
        const next = new URL(res.headers.location, url).href;
        return fetch(next, redirectCount + 1).then(resolve).catch(reject);
      }
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => resolve({ status: res.statusCode, body }));
    }).on('error', reject);
  });
}

async function main() {
  console.log('\nSitemap & robots.txt — accessibility and format\n' + '─'.repeat(50));
  let failed = false;

  // robots.txt
  const robotsUrl = `${BASE}/robots.txt`;
  try {
    const { status, body } = await fetch(robotsUrl);
    if (status !== 200) {
      console.log(`robots.txt: ❌ HTTP ${status}`);
      failed = true;
    } else {
      const hasUserAgent = /User-agent:\s*\*/i.test(body);
      const hasSitemap = /Sitemap:\s*https?:\/\//i.test(body);
      console.log(`robots.txt: ✅ 200 OK`);
      if (!hasUserAgent) {
        console.log('           ⚠️  No "User-agent: *" rule found');
        failed = true;
      }
      if (!hasSitemap) {
        console.log('           ⚠️  No "Sitemap: <url>" line found');
        failed = true;
      }
    }
  } catch (e) {
    console.log(`robots.txt: ❌ ${e.message}`);
    failed = true;
  }

  // sitemap.xml
  const sitemapUrl = `${BASE}/sitemap.xml`;
  try {
    const { status, body } = await fetch(sitemapUrl);
    if (status !== 200) {
      console.log(`sitemap.xml: ❌ HTTP ${status}`);
      failed = true;
    } else {
      const hasUrlset = /<urlset[^>]*xmlns/i.test(body);
      const locCount = (body.match(/<loc>/g) || []).length;
      console.log(`sitemap.xml: ✅ 200 OK (${locCount} <loc> entries)`);
      if (!hasUrlset) {
        console.log('             ⚠️  Missing <urlset xmlns=...>');
        failed = true;
      }
    }
  } catch (e) {
    console.log(`sitemap.xml: ❌ ${e.message}`);
    failed = true;
  }

  console.log('');
  process.exit(failed ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
