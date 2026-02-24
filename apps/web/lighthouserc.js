/**
 * Lighthouse CI configuration.
 *
 * Tests 3 article pages when LHCI_URLS is set (e.g. by scripts/run-lighthouse-ci.js).
 * Otherwise tests the base URL only (e.g. for quick "lhci autorun").
 *
 * Run 3 article pages: node ../scripts/run-lighthouse-ci.js
 * Run single URL:      npm run build && lhci autorun
 */

const BASE = process.env.LHCI_BASE_URL || 'http://localhost:3000';

// Optional: comma-separated list of article URLs (set by run-lighthouse-ci.js)
const urlList = process.env.LHCI_URLS;
const urls = urlList ? urlList.split(',').map((u) => u.trim()).filter(Boolean) : [BASE];

module.exports = {
  ci: {
    collect: {
      numberOfRuns: 1,
      url: urls,
      ...(process.env.LHCI_SKIP_SERVER
        ? {}
        : {
            startServerCommand: 'npm run start',
            startServerReadyPattern: 'Ready in',
            startServerReadyTimeout: 120000,
          }),
    },
    assert: {
      preset: 'lighthouse:no-pwa',
      assertions: {
        'categories:performance': ['warn', { minScore: 0.5 }],
        'categories:accessibility': ['warn', { minScore: 0.8 }],
        'categories:best-practices': ['warn', { minScore: 0.8 }],
        'categories:seo': ['warn', { minScore: 0.8 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
