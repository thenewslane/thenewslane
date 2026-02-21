'use client';

/**
 * CookieSettingsButton
 *
 * A client component used in the Footer to re-open the ConsentBanner.
 * Lives in its own file so Footer can remain a server component.
 */

import { useConsent } from '@/app/providers';

export function CookieSettingsButton() {
  const { resetConsent } = useConsent();

  return (
    <button
      onClick={resetConsent}
      style={{
        background:      'none',
        border:          'none',
        padding:         0,
        cursor:          'pointer',
        fontSize:        'inherit',
        fontFamily:      'inherit',
        color:           'var(--color-text-secondary-light)',
        textDecoration:  'underline',
        textUnderlineOffset: '2px',
      }}
    >
      Cookie Settings
    </button>
  );
}
