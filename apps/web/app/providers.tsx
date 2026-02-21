'use client';

/**
 * Providers
 *
 * Client-side context providers rendered inside the root layout's <body>.
 * Responsibilities:
 *   • Read / persist consent state to localStorage.
 *   • Expose ConsentContext so any component can read consent or reset the banner.
 *   • Render <ConsentBanner> when no consent has been recorded yet.
 *   • Mount <AnalyticsScripts> only after consent is known.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { ConsentBanner }   from '@platform/ui/web';
import type { ConsentState } from '@platform/ui/web';
import { AnalyticsScripts } from '@/components/AnalyticsScripts';

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'nl_consent_v1';

interface ConsentContextValue {
  /** null = not yet loaded from storage; don't gate renders on this. */
  consent:      ConsentState | null;
  setConsent:   (s: ConsentState) => void;
  /** Re-open the consent banner (e.g. from the footer's "Cookie Settings" link). */
  resetConsent: () => void;
}

const ConsentContext = createContext<ConsentContextValue>({
  consent:      null,
  setConsent:   () => {},
  resetConsent: () => {},
});

export function useConsent(): ConsentContextValue {
  return useContext(ConsentContext);
}

// ---------------------------------------------------------------------------
// Provider component
// ---------------------------------------------------------------------------

export function Providers({ children }: { children: React.ReactNode }) {
  const [consent,    setConsentState] = useState<ConsentState | null>(null);
  const [showBanner, setShowBanner]   = useState(false);
  // Tracks localStorage hydration — avoids a server/client mismatch flash.
  const [hydrated,   setHydrated]     = useState(false);

  // Hydrate from localStorage on mount (client only).
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as ConsentState;
        setConsentState(parsed);
        setShowBanner(false);
      } else {
        setShowBanner(true);
      }
    } catch {
      setShowBanner(true);
    }
    setHydrated(true);
  }, []);

  const setConsent = useCallback((s: ConsentState) => {
    setConsentState(s);
    setShowBanner(false);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    } catch {
      // Private browsing — consent is session-only; acceptable fallback.
    }
  }, []);

  const resetConsent = useCallback(() => {
    setShowBanner(true);
  }, []);

  return (
    <ConsentContext.Provider value={{ consent, setConsent, resetConsent }}>
      {children}

      {/*
        Mount analytics scripts only after we know consent state.
        Re-mounts whenever consent changes (e.g. user updates preferences).
      */}
      {hydrated && consent && (
        <AnalyticsScripts consent={consent} />
      )}

      {/* ConsentBanner floats over the page; shown until user responds. */}
      {hydrated && showBanner && (
        <ConsentBanner onConsent={setConsent} />
      )}
    </ConsentContext.Provider>
  );
}
