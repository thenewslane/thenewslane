'use client';

/**
 * AnalyticsScripts
 *
 * Loads third-party scripts ONLY after the user grants the relevant consent
 * category via the ConsentBanner. Rendered inside <Providers> so it re-renders
 * whenever consent state changes.
 *
 * Required env vars (set in apps/web/.env.local):
 *   NEXT_PUBLIC_GA4_MEASUREMENT_ID  — e.g. G-NBMQ66M04S
 */

import Script from 'next/script';
import type { ConsentState } from '@platform/ui/web';

interface Props {
  consent: ConsentState;
}

export function AnalyticsScripts({ consent }: Props) {
  const ga4Id = process.env.NEXT_PUBLIC_GA4_MEASUREMENT_ID;

  return (
    <>
      {/* ── Google Analytics 4 — analytics consent required ─────────────── */}
      {consent.analytics && ga4Id && (
        <>
          <Script
            id="ga4-loader"
            src={`https://www.googletagmanager.com/gtag/js?id=${ga4Id}`}
            strategy="afterInteractive"
          />
          <Script
            id="ga4-init"
            strategy="afterInteractive"
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: `
                window.dataLayer = window.dataLayer || [];
                function gtag(){window.dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${ga4Id}', {
                  anonymize_ip: true,
                  cookie_flags: 'SameSite=None;Secure',
                });
                ${
                  !consent.advertising
                    ? `gtag('consent', 'update', {
                        ad_storage:            'denied',
                        ad_user_data:          'denied',
                        ad_personalization:    'denied',
                        analytics_storage:     'granted',
                      });`
                    : `gtag('consent', 'update', {
                        ad_storage:            'granted',
                        ad_user_data:          'granted',
                        ad_personalization:    'granted',
                        analytics_storage:     'granted',
                      });`
                }
              `,
            }}
          />
        </>
      )}

      {/* ── Google Ad Manager GPT — advertising consent required ──────────── */}
      {consent.advertising && (
        <Script
          id="gpt-loader"
          src="https://securepubads.g.doubleclick.net/tag/js/gpt.js"
          strategy="afterInteractive"
        />
      )}
    </>
  );
}
