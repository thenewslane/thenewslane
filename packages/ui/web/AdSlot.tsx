import React, { useEffect, useRef } from 'react';

export interface ConsentState {
  necessary:   boolean; // always true — required for the site to function
  analytics:   boolean; // GA4
  advertising: boolean; // Google Ad Manager / AdSense
  functional:  boolean; // personalisation, preferences
}

export interface AdSlotProps {
  /** Google Ad Manager unit path, e.g. "/1234567/homepage-leaderboard" */
  unitPath: string;
  /** Array of [width, height] size tuples, e.g. [[728, 90], [320, 50]] */
  sizes:    [number, number][];
  consentState: ConsentState;
  /** Optional stable DOM ID override. Defaults to a sanitised unitPath. */
  id?: string;
}

declare global {
  interface Window {
    googletag?: {
      cmd:   unknown[];
      defineSlot:  (unitPath: string, sizes: [number, number][], id: string) => unknown;
      enableServices: () => void;
      pubads: () => { refresh: (slots: unknown[]) => void; enableSingleRequest: () => void };
      display: (id: string) => void;
    };
  }
}

export function AdSlot({ unitPath, sizes, consentState, id }: AdSlotProps) {
  const slotId   = id ?? `ad-${unitPath.replace(/\//g, '-').replace(/^-/, '')}`;
  const slotRef  = useRef<unknown>(null);

  useEffect(() => {
    // Do not render ads without advertising consent (GDPR / CCPA).
    if (!consentState.advertising) return;

    const gt = window.googletag;
    if (!gt) {
      console.warn('[AdSlot] window.googletag not found. Make sure GPT script is loaded.');
      return;
    }

    (gt.cmd as (() => void)[]).push(() => {
      if (!slotRef.current) {
        slotRef.current = gt!.defineSlot(unitPath, sizes, slotId);
        gt!.enableServices();
      }
      gt!.display(slotId);
    });

    return () => {
      // Slots are not destroyed on unmount to avoid GPT double-definition errors
      // during React StrictMode double-invocations. The GPT slot registry persists
      // at the page level — apps should refresh slots on route change instead.
    };
  }, [consentState.advertising, unitPath, slotId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!consentState.advertising) {
    // Render a size-preserving placeholder so layout does not shift when
    // consent is later granted and the ad loads.
    const [w, h] = sizes[0] ?? [300, 250];
    return (
      <div
        aria-hidden
        style={{
          width:           `${w}px`,
          height:          `${h}px`,
          maxWidth:        '100%',
          backgroundColor: 'var(--color-ad-slot)',
          borderRadius:    'var(--radius-small)',
          display:         'flex',
          alignItems:      'center',
          justifyContent:  'center',
        }}
      >
        <span
          style={{
            fontSize:   '11px',
            fontFamily: 'var(--font-body)',
            color:      'var(--color-text-muted-light)',
            letterSpacing: '0.04em',
          }}
        >
          Advertisement
        </span>
      </div>
    );
  }

  return (
    <div
      id={slotId}
      style={{
        backgroundColor: 'var(--color-ad-slot)',
        borderRadius:    'var(--radius-small)',
        overflow:        'hidden',
        minWidth:        `${sizes[0]?.[0] ?? 300}px`,
        minHeight:       `${sizes[0]?.[1] ?? 250}px`,
      }}
    />
  );
}
