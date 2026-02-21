'use client';

import React, { useState } from 'react';
import type { ConsentState } from './AdSlot';

export { ConsentState };

export interface ConsentBannerProps {
  onConsent: (state: ConsentState) => void;
}

const PREFERENCES_INIT: Omit<ConsentState, 'necessary'> = {
  analytics:   false,
  advertising: false,
  functional:  false,
};

const toggleStyle = (checked: boolean): React.CSSProperties => ({
  display:         'inline-block',
  position:        'relative' as const,
  width:           36,
  height:          20,
  borderRadius:    10,
  backgroundColor: checked ? 'var(--color-primary)' : 'rgba(0,0,0,.2)',
  transition:      'background-color 0.2s',
  cursor:          'pointer',
  flexShrink:      0,
});

const knobStyle = (checked: boolean): React.CSSProperties => ({
  position:        'absolute' as const,
  top:             2,
  left:            checked ? 18 : 2,
  width:           16,
  height:          16,
  borderRadius:    8,
  backgroundColor: '#fff',
  boxShadow:       '0 1px 3px rgba(0,0,0,.2)',
  transition:      'left 0.2s',
});

const PREFERENCE_ITEMS: {
  key: keyof Omit<ConsentState, 'necessary'>;
  label: string;
  desc:  string;
}[] = [
  {
    key:   'analytics',
    label: 'Analytics',
    desc:  'Helps us understand how visitors use the site (Google Analytics 4).',
  },
  {
    key:   'advertising',
    label: 'Advertising',
    desc:  'Personalised ads and measurement via Google Ad Manager.',
  },
  {
    key:   'functional',
    label: 'Functional',
    desc:  'Remembers your preferences and personalises your experience.',
  },
];

export function ConsentBanner({ onConsent }: ConsentBannerProps) {
  const [managing, setManaging]     = useState(false);
  const [prefs,    setPrefs]        = useState(PREFERENCES_INIT);
  const [visible,  setVisible]      = useState(true);

  if (!visible) return null;

  function acceptAll() {
    const state: ConsentState = { necessary: true, analytics: true, advertising: true, functional: true };
    setVisible(false);
    onConsent(state);
  }

  function rejectAll() {
    const state: ConsentState = { necessary: true, analytics: false, advertising: false, functional: false };
    setVisible(false);
    onConsent(state);
  }

  function savePreferences() {
    const state: ConsentState = { necessary: true, ...prefs };
    setVisible(false);
    onConsent(state);
  }

  function togglePref(key: keyof typeof prefs) {
    setPrefs(p => ({ ...p, [key]: !p[key] }));
  }

  const btnBase: React.CSSProperties = {
    padding:      'var(--spacing-2) var(--spacing-4)',
    borderRadius: 'var(--radius-small)',
    fontSize:     '13px',
    fontWeight:   600,
    fontFamily:   'var(--font-body)',
    cursor:       'pointer',
    border:       'none',
    whiteSpace:   'nowrap' as const,
    transition:   'opacity 0.15s',
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Cookie consent"
      style={{
        position:        'fixed',
        bottom:          'var(--spacing-4)',
        left:            'var(--spacing-4)',
        right:           'var(--spacing-4)',
        maxWidth:        560,
        margin:          '0 auto',
        backgroundColor: 'var(--color-card-light)',
        borderRadius:    'var(--radius-large)',
        boxShadow:       '0 8px 40px rgba(0,0,0,.16), 0 2px 8px rgba(0,0,0,.08)',
        padding:         'var(--spacing-6)',
        fontFamily:      'var(--font-body)',
        zIndex:          9999,
      }}
    >
      {!managing ? (
        // ── Default view ────────────────────────────────────────────────────
        <>
          <p
            style={{
              margin:     '0 0 var(--spacing-4)',
              fontSize:   '13px',
              lineHeight: 1.65,
              color:      'var(--color-text-secondary-light)',
            }}
          >
            We use cookies to improve your experience, analyse traffic, and serve
            personalised ads. You can accept all, reject non-essential cookies, or
            manage your preferences.{' '}
            <a
              href="/privacy"
              style={{ color: 'var(--color-link)', textDecoration: 'underline' }}
            >
              Privacy policy
            </a>
          </p>

          <div style={{ display: 'flex', gap: 'var(--spacing-2)', flexWrap: 'wrap' }}>
            <button
              onClick={acceptAll}
              style={{
                ...btnBase,
                backgroundColor: 'var(--color-primary)',
                color:           '#fff',
                flexGrow:        1,
              }}
            >
              Accept All
            </button>
            <button
              onClick={rejectAll}
              style={{
                ...btnBase,
                backgroundColor: 'rgba(0,0,0,.06)',
                color:           'var(--color-text-primary-light)',
                flexGrow:        1,
              }}
            >
              Reject All
            </button>
            <button
              onClick={() => setManaging(true)}
              style={{
                ...btnBase,
                backgroundColor: 'transparent',
                color:           'var(--color-link)',
                textDecoration:  'underline',
              }}
            >
              Manage Preferences
            </button>
          </div>
        </>
      ) : (
        // ── Manage view ─────────────────────────────────────────────────────
        <>
          <h3
            style={{
              margin:     '0 0 var(--spacing-4)',
              fontSize:   '16px',
              fontFamily: 'var(--font-heading)',
              fontWeight: 700,
              color:      'var(--color-text-primary-light)',
            }}
          >
            Cookie Preferences
          </h3>

          <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 var(--spacing-4)' }}>
            {/* Necessary — always on */}
            <li
              style={{
                display:        'flex',
                alignItems:     'flex-start',
                gap:            'var(--spacing-3)',
                padding:        'var(--spacing-3) 0',
                borderBottom:   '1px solid rgba(0,0,0,.07)',
              }}
            >
              <span style={toggleStyle(true)} aria-hidden>
                <span style={knobStyle(true)} />
              </span>
              <div>
                <strong style={{ fontSize: '13px', color: 'var(--color-text-primary-light)' }}>
                  Necessary
                </strong>
                <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--color-text-muted-light)', lineHeight: 1.5 }}>
                  Required for the site to function. Cannot be disabled.
                </p>
              </div>
            </li>

            {PREFERENCE_ITEMS.map(({ key, label, desc }) => (
              <li
                key={key}
                style={{
                  display:      'flex',
                  alignItems:   'flex-start',
                  gap:          'var(--spacing-3)',
                  padding:      'var(--spacing-3) 0',
                  borderBottom: '1px solid rgba(0,0,0,.07)',
                  cursor:       'pointer',
                }}
                onClick={() => togglePref(key)}
              >
                <span style={toggleStyle(prefs[key])} aria-hidden>
                  <span style={knobStyle(prefs[key])} />
                </span>
                <div>
                  <strong style={{ fontSize: '13px', color: 'var(--color-text-primary-light)' }}>
                    {label}
                  </strong>
                  <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--color-text-muted-light)', lineHeight: 1.5 }}>
                    {desc}
                  </p>
                </div>
              </li>
            ))}
          </ul>

          <div style={{ display: 'flex', gap: 'var(--spacing-2)' }}>
            <button
              onClick={savePreferences}
              style={{
                ...btnBase,
                backgroundColor: 'var(--color-primary)',
                color:           '#fff',
                flexGrow:        1,
              }}
            >
              Save Preferences
            </button>
            <button
              onClick={() => setManaging(false)}
              style={{
                ...btnBase,
                backgroundColor: 'rgba(0,0,0,.06)',
                color:           'var(--color-text-primary-light)',
              }}
            >
              Back
            </button>
          </div>
        </>
      )}
    </div>
  );
}
