// @ts-check

import bundleAnalyzer from '@next/bundle-analyzer';

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
});

// ---------------------------------------------------------------------------
// Derive hostname from an environment URL — never hardcode project-specific IDs.
// ---------------------------------------------------------------------------
function hostnameFrom(envUrl) {
  try {
    return new URL(envUrl ?? '').hostname;
  } catch {
    return '';
  }
}

const supabaseHostname = hostnameFrom(process.env.NEXT_PUBLIC_SUPABASE_URL);

// ---------------------------------------------------------------------------
// Security headers
// ---------------------------------------------------------------------------
const securityHeaders = [
  // Deny framing from other origins; same-origin iframes allowed (ad previews).
  { key: 'X-Frame-Options',          value: 'SAMEORIGIN' },
  // Prevent MIME-type sniffing.
  { key: 'X-Content-Type-Options',   value: 'nosniff' },
  // HSTS — 1 year, include subdomains, preload-ready.
  { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains; preload' },
  // Referrer — strip path on cross-origin, keep origin on same-origin HTTPS.
  { key: 'Referrer-Policy',          value: 'strict-origin-when-cross-origin' },
  // Disable browser APIs this site doesn't use.
  { key: 'Permissions-Policy',       value: 'camera=(), microphone=(), geolocation=()' },
  // DNS prefetch for performance.
  { key: 'X-DNS-Prefetch-Control',   value: 'on' },
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",

      // Scripts: Next.js runtime chunks + GA4 GTM tag + GPT ad manager
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'" +
        ' https://www.googletagmanager.com' +
        ' https://www.google-analytics.com' +
        ' https://securepubads.g.doubleclick.net' +
   	' https://static.cloudflareinsights.com' +
        ' https://pagead2.googlesyndication.com',

      // Frames: YouTube privacy-enhanced domain, Vimeo, Google ad iframes
      "frame-src 'self'" +
        ' https://www.youtube-nocookie.com' +
        ' https://player.vimeo.com' +
        ' https://tpc.googlesyndication.com' +
        ' https://www.google.com',

      // Images: supabase storage, YouTube/Vimeo thumbnails, favicons, data URIs
      "img-src 'self' data: blob: https:",

      // Fetch/XHR: Supabase API, GA4 beacon, analytics, Google Ad Manager (GPT)
      "connect-src 'self'" +
        (supabaseHostname ? ` https://${supabaseHostname}` : '') +
        ' https://www.google-analytics.com' +
        ' https://analytics.google.com' +
        ' https://region1.google-analytics.com' +
        ' https://cloudflareinsights.com' +
        ' https://securepubads.g.doubleclick.net' +
        ' https://pagead2.googlesyndication.com' +
        ' https://tpc.googlesyndication.com' +
        ' https://ep1.adtrafficquality.google',

      // Styles: Next.js injects inline <style> tags
      "style-src 'self' 'unsafe-inline'",

      // Fonts: self-hosted, data URIs, Google Fonts (layout uses Inter with display=swap)
      "font-src 'self' data: https://fonts.gstatic.com",

      // Media: self-hosted + Supabase Storage (videos / audio)
      "media-src 'self' blob:" + (supabaseHostname ? ` https://${supabaseHostname}` : ''),

      // Lock down everything else
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; '),
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  // ---------------------------------------------------------------------------
  // Workspace packages — Next.js transpiles them from TypeScript source.
  // ---------------------------------------------------------------------------
  transpilePackages: [
    '@platform/types',
    '@platform/theme',
    '@platform/ui',
    '@platform/supabase',
  ],

  // ---------------------------------------------------------------------------
  // Image optimisation — WebP for smaller payloads, allowed remote patterns
  // ---------------------------------------------------------------------------
  images: {
    formats: ['image/webp', 'image/avif'],
    remotePatterns: [
      // Supabase Storage — thumbnails, video posters, user avatars
      ...(supabaseHostname
        ? [{ protocol: 'https', hostname: supabaseHostname }]
        : []),

      // YouTube thumbnails (hqdefault, maxresdefault, etc.)
      { protocol: 'https', hostname: 'i.ytimg.com' },
      { protocol: 'https', hostname: 'img.youtube.com' },

      // Vimeo thumbnails
      { protocol: 'https', hostname: 'i.vimeocdn.com' },
      { protocol: 'https', hostname: 'vumbnail.com' },

      // Wikimedia / Wikipedia thumbnails (CC-licensed news imagery)
      { protocol: 'https', hostname: 'upload.wikimedia.org' },
      { protocol: 'https', hostname: 'commons.wikimedia.org' },

      // Copyright-free stock (pipeline thumbnails)
      { protocol: 'https', hostname: 'images.unsplash.com' },
      { protocol: 'https', hostname: 'images.pexels.com' },

      // Google S2 favicon service (used by SourceAttribution component)
      { protocol: 'https', hostname: 'www.google.com' },
    ],
  },

  // ---------------------------------------------------------------------------
  // Security headers applied to every route
  // ---------------------------------------------------------------------------
  async headers() {
    return [
      {
        source:  '/(.*)',
        headers: securityHeaders,
      },
    ];
  },

  // ---------------------------------------------------------------------------
  // ISR revalidation
  // The global default is set via `export const revalidate = 300` in
  // app/layout.tsx. Individual pages override this by exporting their own
  // `revalidate` value. On-demand revalidation uses revalidatePath() /
  // revalidateTag() called from Inngest pipeline Route Handlers.
  // ---------------------------------------------------------------------------
};

export default withBundleAnalyzer(nextConfig);
