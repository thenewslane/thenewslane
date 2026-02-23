'use client';

/**
 * Providers
 *
 * Client-side context providers rendered inside the root layout's <body>.
 * Responsibilities:
 *   • Read / persist consent state to localStorage.
 *   • Expose ConsentContext so any component can read consent or reset the banner.
 *   • Fetch authenticated user profile to get the is_minor flag (COPPA compliance).
 *   • Expose isMinor in ConsentContext and force advertising=false for minors.
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
import { ConsentBanner }     from '@platform/ui/web';
import type { ConsentState } from '@platform/ui/web';
import { getBrowserClient }  from '@platform/supabase';
import { AnalyticsScripts }  from '@/components/AnalyticsScripts';

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
  /** true when the authenticated user's profile has is_minor = true (COPPA) */
  isMinor:      boolean;
}

const ConsentContext = createContext<ConsentContextValue>({
  consent:      null,
  setConsent:   () => {},
  resetConsent: () => {},
  isMinor:      false,
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
  const [isMinor,    setIsMinor]      = useState(false);
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

  // Fetch user profile to check is_minor flag (COPPA compliance).
  useEffect(() => {
    const supabase = getBrowserClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return;
      supabase
        .from('user_profiles')
        .select('is_minor')
        .eq('id', user.id)
        .single()
        .then(({ data }): { data: { is_minor: boolean } | null }) => {
          if (data?.is_minor) {
            setIsMinor(true);
            // Force advertising off for minors (COPPA)
            setConsentState((prev) =>
              prev ? { ...prev, advertising: false } : prev
            );
          }
        });
    });
  }, []);

  const setConsent = useCallback(
    (s: ConsentState) => {
      // Never grant advertising consent to minors (COPPA)
      const effective = isMinor ? { ...s, advertising: false } : s;
      setConsentState(effective);
      setShowBanner(false);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(effective));
      } catch {
        // Private browsing — consent is session-only; acceptable fallback.
      }
    },
    [isMinor],
  );

  const resetConsent = useCallback(() => {
    setShowBanner(true);
  }, []);

  return (
    <ConsentContext.Provider value={{ consent, setConsent, resetConsent, isMinor }}>
      {children}

      {/*
        Mount analytics scripts only after we know consent state.
        Re-mounts whenever consent changes (e.g. user updates preferences).
      */}
      {hydrated && consent && (
        <AnalyticsScripts consent={consent} isMinor={isMinor} />
      )}

      {/* ConsentBanner floats over the page; shown until user responds. */}
      {hydrated && showBanner && (
        <ConsentBanner onConsent={setConsent} />
      )}
    </ConsentContext.Provider>
  );
}
