'use client';

/**
 * AdSlot
 *
 * App-level ad slot component that wraps Google Publisher Tag slot lifecycle.
 * Reads consent from ConsentContext — no prop-threading required.
 *
 * Props:
 *   unitPath  — full GAM unit path, e.g. /23173092177/in_content
 *   sizes     — array of [w, h] size tuples
 *   targeting — optional key-value pairs passed to setTargeting (e.g. iab_categories)
 *   id        — optional DOM id override
 */

import React, { useEffect, useRef } from 'react';
import { useConsent }     from '@/app/providers';
import { useAdManager }   from './AdManager';

type AdSize = [number, number];

interface AdSlotProps {
  unitPath:   string;
  sizes:      AdSize[];
  targeting?: Record<string, string | string[]>;
  id?:        string;
}

type GoogleTag = {
  cmd:       (() => void)[];
  defineSlot: (path: string, sizes: AdSize[], id: string) => GoogleSlot | null;
  enableServices: () => void;
  display:   (id: string) => void;
  destroySlots: (slots: GoogleSlot[]) => void;
  pubads: () => {
    setTargeting: (key: string, value: string | string[]) => void;
    enableSingleRequest: () => void;
    refresh: (slots?: GoogleSlot[]) => void;
  };
};

type GoogleSlot = {
  setTargeting: (key: string, value: string | string[]) => GoogleSlot;
};

declare global {
  interface Window { googletag?: GoogleTag; }
}

export function AdSlot({ unitPath, sizes, targeting = {}, id }: AdSlotProps) {
  const { consent, isMinor } = useConsent();
  const { gptReady }         = useAdManager();
  const slotRef              = useRef<GoogleSlot | null>(null);
  const divId                = id ?? `gam-${unitPath.replace(/\//g, '-').replace(/^-/, '')}`;

  // Advertising is allowed only with explicit consent and not for minors (COPPA)
  const adsAllowed = Boolean(consent?.advertising) && !isMinor;

  useEffect(() => {
    if (!gptReady || !adsAllowed) return;

    const gt = window.googletag;
    if (!gt) return;

    gt.cmd.push(() => {
      if (!slotRef.current) {
        const slot = gt.defineSlot(unitPath, sizes, divId);
        if (!slot) return;
        slotRef.current = slot;

        // Apply article-level IAB category targeting for contextual relevance
        Object.entries(targeting).forEach(([k, v]) => {
          slotRef.current!.setTargeting(k, v);
        });

        gt.enableServices();
      }
      gt.display(divId);
    });

    return () => {
      if (slotRef.current && gt) {
        gt.cmd.push(() => {
          gt.destroySlots([slotRef.current!]);
          slotRef.current = null;
        });
      }
    };
    // Sizes and unitPath are stable; only re-run if gptReady or consent changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gptReady, adsAllowed, divId]);

  if (!adsAllowed) {
    // Size-preserving placeholder — prevents layout shift when consent is later granted
    const [w, h] = sizes[0] ?? [300, 250];
    return (
      <div
        aria-hidden
        style={{
          width:           `${w}px`,
          height:          `${h}px`,
          maxWidth:        '100%',
          backgroundColor: 'var(--color-ad-slot, #f5f5f5)',
          borderRadius:    'var(--radius-small, 4px)',
          display:         'flex',
          alignItems:      'center',
          justifyContent:  'center',
        }}
      >
        <span
          style={{
            fontSize:      '11px',
            color:         'var(--color-text-muted-light, #aaa)',
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
      id={divId}
      style={{
        backgroundColor: 'var(--color-ad-slot, #f5f5f5)',
        borderRadius:    'var(--radius-small, 4px)',
        overflow:        'hidden',
        minWidth:        `${sizes[0]?.[0] ?? 300}px`,
        minHeight:       `${sizes[0]?.[1] ?? 250}px`,
      }}
    />
  );
}
