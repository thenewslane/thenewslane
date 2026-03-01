/**
 * Root layout — server component.
 *
 * Wraps every page with:
 *   • Design tokens (globals.css → tokens.css → CSS custom properties)
 *   • Tailwind base styles
 *   • ConsentProvider (client) — mounts ConsentBanner + AnalyticsScripts
 *   • Header
 *   • <main> content slot
 *   • Footer
 *
 * ISR default: 5 minutes. Individual pages can override via
 *   `export const revalidate = <seconds>` in their own file.
 *
 * Required env vars (apps/web/.env.local):
 *   PUBLICATION_NAME            — display name
 *   PUBLICATION_DOMAIN          — canonical domain
 *   NEXT_PUBLIC_SUPABASE_URL    — Supabase project URL
 *   NEXT_PUBLIC_SUPABASE_ANON_KEY
 *   NEXT_PUBLIC_GA4_MEASUREMENT_ID
 *   NEXT_PUBLIC_PUBLICATION_NAME  — client-accessible copy of PUBLICATION_NAME
 *   NEXT_PUBLIC_ADSENSE_CLIENT_ID — optional; enables AdSense auto ads (e.g. ca-pub-2372260960415453)
 */

import type { Metadata, Viewport } from 'next';
import Script from 'next/script';
import './globals.css';
import { Providers }        from './providers';
import { Header }           from '@/components/Header';
import { Footer }           from '@/components/Footer';
import { SkipToContent }    from '@/components/SkipToContent';
import { AuthorSchema }     from '@/components/seo/AuthorSchema';
import { AdManagerProvider } from '@/components/ads/AdManager';

// ---------------------------------------------------------------------------
// Route segment config — ISR default for the entire app
// ---------------------------------------------------------------------------
export const revalidate = 300; // 5 minutes

// ---------------------------------------------------------------------------
// Metadata
// Reads from server-side env vars; no NEXT_PUBLIC_ prefix needed here.
// ---------------------------------------------------------------------------
const pubName   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const pubDomain = process.env.PUBLICATION_DOMAIN ?? '';
const baseUrl   = pubDomain ? `https://${pubDomain}` : 'http://localhost:3000';

export const metadata: Metadata = {
  title: {
    default:  pubName,
    template: `%s | ${pubName}`,
  },
  description:
    `${pubName} — AI-curated trending news. Real-time viral topics across technology, politics, sports, entertainment, and more.`,
  metadataBase: new URL(baseUrl),
  openGraph: {
    type:       'website',
    siteName:   pubName,
    locale:     'en_US',
  },
  twitter: {
    card: 'summary_large_image',
  },
  robots: {
    index:  true,
    follow: true,
    googleBot: {
      index:             true,
      follow:            true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet':       -1,
    },
  },
};

export const viewport: Viewport = {
  width:        'device-width',
  initialScale: 1,
  themeColor:   '#E8384F', // brand primary — matches --color-primary token
};

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Web fonts: preload CSS to start fetch early; display=swap avoids FOIT */}
        <link
          rel="preconnect"
          href="https://fonts.googleapis.com"
        />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        <link
          rel="preload"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap"
          as="style"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap"
          media="print"
          onLoad="this.media='all'"
        />
        <noscript>
          <link
            rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap"
          />
        </noscript>
        {/* Author entity markup — establishes E-E-A-T signals sitewide */}
        <AuthorSchema />
        {/* Google Publisher Tag — load after interactive to avoid blocking LCP */}
        <Script
          id="gpt-head-loader"
          src="https://securepubads.g.doubleclick.net/tag/js/gpt.js"
          strategy="afterInteractive"
          crossOrigin="anonymous"
        />
      </head>
      {/*
        suppressHydrationWarning on <body> is needed because browser extensions
        (e.g. Google Translate, password managers) inject attributes that cause
        React hydration mismatches.
      */}
      <body suppressHydrationWarning>
        <Providers>
          <AdManagerProvider>
            {/* Skip-to-content link for keyboard / screen-reader users */}
            <SkipToContent />

            <Header />

            <main id="main-content" tabIndex={-1}>
              {children}
            </main>

            <Footer />
          </AdManagerProvider>
        </Providers>
      </body>
    </html>
  );
}
