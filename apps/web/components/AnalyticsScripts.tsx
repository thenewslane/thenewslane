'use client';

/**
 * AnalyticsScripts
 *
 * Loads third-party scripts with the correct consent signals:
 *
 *  GA4  — only loaded when consent.analytics = true (GDPR gating)
 *         Requires NEXT_PUBLIC_GA4_MEASUREMENT_ID (e.g. G-XXXXXXXXXX) in env.
 *  GPT  — ALWAYS loaded regardless of consent state (better fill rate)
 *         but with NPA(1) + restrictDataProcessing when consent is denied
 *         or the user has CCPA opted out.
 *
 * GDPR  — NPA mode when !consent.advertising
 * CCPA  — restrictDataProcessing when localStorage.nl_ccpa_opt_out === 'true'
 * COPPA — NPA mode when isMinor === true (set by Providers via user_profiles.is_minor)
 */

import Script from 'next/script';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import type { ConsentState } from '@platform/ui/web';

interface Props {
  consent: ConsentState;
  isMinor: boolean;
}

/** Sends GA4 page_view on client-side route changes (Next.js SPA navigation). */
function GA4RouteTracker({ ga4Id }: { ga4Id: string }) {
  const pathname = usePathname();
  useEffect(() => {
    if (!pathname || typeof window.gtag !== 'function') return;
    window.gtag('event', 'page_view', {
      page_path: pathname,
      page_title: typeof document !== 'undefined' ? document.title : '',
    });
  }, [pathname, ga4Id]);
  return null;
}

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

export function AnalyticsScripts({ consent, isMinor }: Props) {
  const ga4Id = process.env.NEXT_PUBLIC_GA4_MEASUREMENT_ID ?? '';
  const adsenseClientId = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID;

  // CCPA opt-out and minor check must be evaluated client-side
  const ccpaOptOut =
    typeof window !== 'undefined' &&
    localStorage.getItem('nl_ccpa_opt_out') === 'true';

  // Non-personalised ads: no advertising consent, CCPA opt-out, or minor
  const useNpa = !consent.advertising || ccpaOptOut || isMinor;

  const adGranted = consent.advertising && !ccpaOptOut && !isMinor;
  const consentUpdate = {
    ad_storage: adGranted ? 'granted' : 'denied',
    ad_user_data: adGranted ? 'granted' : 'denied',
    ad_personalization: adGranted ? 'granted' : 'denied',
    analytics_storage: 'granted',
  };

  return (
    <>
      {/* ── Google Analytics 4 — analytics consent required ─────────────── */}
      {consent.analytics && ga4Id && (
        <>
          <Script
            id="ga4-loader"
            src={`https://www.googletagmanager.com/gtag/js?id=${ga4Id}`}
            strategy="afterInteractive"
            onLoad={() => {
              window.dataLayer = window.dataLayer || [];
              window.gtag = window.gtag || ((...args: unknown[]) => window.dataLayer?.push(args));
              window.gtag('js', new Date());
              window.gtag('config', ga4Id, {
                anonymize_ip: true,
                cookie_flags: 'SameSite=None;Secure',
              });
              window.gtag('consent', 'update', consentUpdate);
            }}
          />
          <GA4RouteTracker ga4Id={ga4Id} />
        </>
      )}

      {/* ── Google AdSense Auto Ads — when client ID set and user consented ─── */}
      {consent.advertising && !isMinor && adsenseClientId && (
        <Script
          id="adsense-auto"
          src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${adsenseClientId}`}
          strategy="afterInteractive"
          crossOrigin="anonymous"
        />
      )}

      {/* ── Google Ad Manager GPT — always loaded, NPA mode when needed ─── */}
      <Script
        id="gpt-loader"
        src="https://securepubads.g.doubleclick.net/tag/js/gpt.js"
        strategy="afterInteractive"
        crossOrigin="anonymous"
      />
      <Script
        id="gpt-init"
        strategy="afterInteractive"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{
          __html: `
            window.googletag = window.googletag || { cmd: [] };
            googletag.cmd.push(function() {
              googletag.defineSlot('/23173092177/newslane/Newslane_300x250_ATF', [300, 250], 'div-gpt-ad-1772035422456-0').addService(googletag.pubads());
              googletag.pubads().setRequestNonPersonalizedAds(${useNpa ? 1 : 0});
              ${ccpaOptOut ? "googletag.pubads().setPrivacySettingsForAll({ restrictDataProcessing: true });" : ''}
              googletag.pubads().enableSingleRequest();
              googletag.enableServices();
            });
          `,
        }}
      />
    </>
  );
}
