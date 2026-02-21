'use client';

/**
 * ArticleAdSlot
 *
 * Consent-aware wrapper around the shared AdSlot component.
 * Reads consent state from ConsentContext (Providers) so article pages
 * don't need to thread consent props manually.
 */

import { AdSlot } from '@platform/ui/web';
import { useConsent } from '@/app/providers';

const DEFAULT_CONSENT = {
  necessary:   true,
  analytics:   false,
  advertising: false,
  functional:  false,
};

interface ArticleAdSlotProps {
  unitPath: string;
  sizes:    [number, number][];
  id?:      string;
}

export function ArticleAdSlot({ unitPath, sizes, id }: ArticleAdSlotProps) {
  const { consent } = useConsent();
  const consentState = consent ?? DEFAULT_CONSENT;

  return (
    <div
      style={{
        display:        'flex',
        justifyContent: 'center',
        margin:         'var(--spacing-8) 0',
      }}
    >
      <AdSlot
        unitPath={unitPath}
        sizes={sizes}
        consentState={consentState}
        id={id}
      />
    </div>
  );
}
