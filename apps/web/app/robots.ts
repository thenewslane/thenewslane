/**
 * Dynamic robots.txt — /robots.txt
 *
 * Allows all well-behaved crawlers.
 * Blocks access to API routes, settings, and onboarding.
 * References the canonical sitemap URL.
 */

import type { MetadataRoute } from 'next';

const BASE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.PUBLICATION_DOMAIN
    ? `https://${process.env.PUBLICATION_DOMAIN}`
    : 'https://thenewslane.com');

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow:     '/',
        disallow:  [
          '/api/',
          '/settings',
          '/onboarding/',
          '/do-not-sell',
        ],
      },
    ],
    sitemap:    `${BASE_URL}/sitemap.xml`,
    host:       BASE_URL,
  };
}
