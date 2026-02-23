'use client';

/**
 * AdManager
 *
 * Context provider that tracks whether Google Publisher Tag (GPT) has
 * initialised its services.  GPT itself is loaded by AnalyticsScripts —
 * this component only waits for `googletag.pubads()` to become ready and
 * exposes that state via the `useAdManager()` hook.
 *
 * Network code: 23173092177
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
} from 'react';

export const GAM_NETWORK_CODE = '23173092177';

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface AdManagerContextValue {
  /** true once googletag.pubads() services have been enabled */
  gptReady: boolean;
}

const AdManagerContext = createContext<AdManagerContextValue>({ gptReady: false });

export function useAdManager(): AdManagerContextValue {
  return useContext(AdManagerContext);
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

interface AdManagerProviderProps {
  children: React.ReactNode;
}

export function AdManagerProvider({ children }: AdManagerProviderProps) {
  const [gptReady, setGptReady] = useState(false);

  useEffect(() => {
    // Poll until window.googletag.pubads is available (GPT loaded async)
    let attempts = 0;
    const MAX_ATTEMPTS = 40; // 40 × 250ms = 10s max wait

    const check = () => {
      const gt = (window as typeof window & { googletag?: { pubads?: () => unknown } }).googletag;
      if (gt?.pubads) {
        setGptReady(true);
        return;
      }
      if (++attempts < MAX_ATTEMPTS) {
        setTimeout(check, 250);
      }
    };

    check();
  }, []);

  return (
    <AdManagerContext.Provider value={{ gptReady }}>
      {children}
    </AdManagerContext.Provider>
  );
}
