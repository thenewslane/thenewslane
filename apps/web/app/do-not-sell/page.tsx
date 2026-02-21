'use client';

/**
 * Do Not Sell or Share My Personal Information — /do-not-sell
 * CCPA opt-out page.
 *
 * On click:
 *   1. Sets `nl_ccpa_opt_out` key in localStorage.
 *   2. If user is authenticated, updates user_profiles.ccpa_opt_out = true in Supabase.
 *   3. Shows confirmation message.
 */

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getBrowserClient } from '@platform/supabase';

const PUBLICATION_NAME   = process.env.NEXT_PUBLIC_PUBLICATION_NAME ?? 'theNewslane';
const PUBLICATION_DOMAIN = process.env.NEXT_PUBLIC_PUBLICATION_DOMAIN ?? '';
const LS_KEY             = 'nl_ccpa_opt_out';

export default function DoNotSellPage() {
  const [optedOut,  setOptedOut]  = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  // Check existing opt-out on mount
  useEffect(() => {
    try {
      if (localStorage.getItem(LS_KEY) === 'true') {
        setOptedOut(true);
        setConfirmed(true);
      }
    } catch {
      // localStorage unavailable (SSR guard)
    }
  }, []);

  async function handleOptOut() {
    setLoading(true);

    // 1. Set in localStorage
    try {
      localStorage.setItem(LS_KEY, 'true');
    } catch {
      // ignore
    }

    // 2. Update Supabase if logged in
    try {
      const supabase = getBrowserClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        await supabase
          .from('user_profiles')
          .update({ ccpa_opt_out: true } as never)
          .eq('id', user.id);
      }
    } catch {
      // Non-fatal — localStorage opt-out already recorded
    }

    setOptedOut(true);
    setLoading(false);
    setConfirmed(true);
  }

  async function handleOptIn() {
    setLoading(true);

    try {
      localStorage.removeItem(LS_KEY);
    } catch {
      // ignore
    }

    try {
      const supabase = getBrowserClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        await supabase
          .from('user_profiles')
          .update({ ccpa_opt_out: false } as never)
          .eq('id', user.id);
      }
    } catch {
      // Non-fatal
    }

    setOptedOut(false);
    setLoading(false);
    setConfirmed(false);
  }

  return (
    <div
      style={{
        maxWidth: 680,
        margin:   '0 auto',
        padding:  'var(--spacing-12) var(--spacing-4) var(--spacing-16)',
      }}
    >
      <h1
        style={{
          fontFamily:  'var(--font-heading)',
          fontSize:    'clamp(22px, 4vw, 34px)',
          fontWeight:  800,
          color:       'var(--color-text-primary-light)',
          margin:      '0 0 var(--spacing-3)',
          lineHeight:  1.2,
        }}
      >
        Do Not Sell or Share My Personal Information
      </h1>
      <p
        style={{
          fontFamily: 'var(--font-body)',
          fontSize:   '13px',
          color:      'var(--color-text-muted-light)',
          margin:     '0 0 var(--spacing-8)',
        }}
      >
        California Consumer Privacy Act (CCPA / CPRA) Opt-Out
      </p>

      {/* Explanation */}
      <div
        style={{
          padding:         'var(--spacing-5)',
          borderRadius:    'var(--radius-small)',
          backgroundColor: 'rgba(0,0,0,.03)',
          border:          '1px solid rgba(0,0,0,.07)',
          marginBottom:    'var(--spacing-8)',
        }}
      >
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontSize:   '15px',
            lineHeight: 1.75,
            color:      'var(--color-text-secondary-light)',
            margin:     '0 0 var(--spacing-3)',
          }}
        >
          Under the California Consumer Privacy Act (CCPA) as amended by the
          California Privacy Rights Act (CPRA), California residents have the right
          to opt out of the sale or sharing of their personal information.
        </p>
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontSize:   '15px',
            lineHeight: 1.75,
            color:      'var(--color-text-secondary-light)',
            margin:     '0 0 var(--spacing-3)',
          }}
        >
          {PUBLICATION_NAME} does not sell personal information to third parties
          for money. However, certain sharing of data for targeted advertising or
          analytics may qualify as &ldquo;selling or sharing&rdquo; under the CCPA.
          By opting out below, you direct us to stop any such sharing.
        </p>
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontSize:   '15px',
            lineHeight: 1.75,
            color:      'var(--color-text-secondary-light)',
            margin:     0,
          }}
        >
          This opt-out applies to this browser. If you are logged in, it will
          also be saved to your account so it persists across devices.
        </p>
      </div>

      {/* Status + Action */}
      {confirmed ? (
        <div
          style={{
            padding:         'var(--spacing-6)',
            borderRadius:    'var(--radius-small)',
            backgroundColor: 'color-mix(in srgb, var(--color-viral-tier-3) 12%, transparent)',
            border:          '1px solid color-mix(in srgb, var(--color-viral-tier-3) 30%, transparent)',
            marginBottom:    'var(--spacing-8)',
            textAlign:       'center',
          }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="var(--color-viral-tier-3)"
            aria-hidden
            style={{ marginBottom: 'var(--spacing-3)' }}
          >
            <path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/>
          </svg>
          <p
            style={{
              fontFamily:  'var(--font-body)',
              fontSize:    '16px',
              fontWeight:  700,
              color:       'var(--color-text-primary-light)',
              margin:      '0 0 var(--spacing-2)',
            }}
          >
            Your opt-out has been recorded
          </p>
          <p
            style={{
              fontFamily: 'var(--font-body)',
              fontSize:   '14px',
              lineHeight: 1.6,
              color:      'var(--color-text-secondary-light)',
              margin:     '0 0 var(--spacing-4)',
            }}
          >
            We will no longer sell or share your personal information for
            advertising purposes on this browser.
          </p>
          <button
            onClick={handleOptIn}
            disabled={loading}
            style={{
              background:   'none',
              border:       'none',
              fontFamily:   'var(--font-body)',
              fontSize:     '13px',
              color:        'var(--color-text-muted-light)',
              textDecoration: 'underline',
              cursor:       'pointer',
              padding:      0,
              opacity:      loading ? 0.5 : 1,
            }}
          >
            {loading ? 'Processing…' : 'Withdraw opt-out (opt back in)'}
          </button>
        </div>
      ) : (
        <div style={{ marginBottom: 'var(--spacing-8)' }}>
          <button
            onClick={handleOptOut}
            disabled={loading}
            style={{
              display:         'block',
              width:           '100%',
              maxWidth:        400,
              padding:         'var(--spacing-3) var(--spacing-6)',
              borderRadius:    'var(--radius-small)',
              border:          'none',
              backgroundColor: 'var(--color-secondary)',
              color:           '#fff',
              fontFamily:      'var(--font-body)',
              fontWeight:      700,
              fontSize:        '16px',
              cursor:          loading ? 'not-allowed' : 'pointer',
              opacity:         loading ? 0.7 : 1,
              textAlign:       'center',
            }}
          >
            {loading ? 'Processing…' : 'Opt Out of Sale / Sharing'}
          </button>
          <p
            style={{
              fontFamily: 'var(--font-body)',
              fontSize:   '12px',
              color:      'var(--color-text-muted-light)',
              marginTop:  'var(--spacing-2)',
            }}
          >
            Your choice will be saved to this browser immediately.
          </p>
        </div>
      )}

      {/* Additional rights */}
      <div
        style={{
          borderTop:  '1px solid rgba(0,0,0,.08)',
          paddingTop: 'var(--spacing-6)',
        }}
      >
        <h2
          style={{
            fontFamily:   'var(--font-body)',
            fontSize:     '15px',
            fontWeight:   700,
            color:        'var(--color-text-primary-light)',
            margin:       '0 0 var(--spacing-3)',
          }}
        >
          Additional CCPA Rights
        </h2>
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontSize:   '14px',
            lineHeight: 1.7,
            color:      'var(--color-text-secondary-light)',
            margin:     '0 0 var(--spacing-3)',
          }}
        >
          California residents also have the right to know, delete, and correct
          personal information. To exercise these rights, submit a request via our{' '}
          <Link href="/contact" style={{ color: 'var(--color-link)' }}>
            contact page
          </Link>
          {PUBLICATION_DOMAIN && (
            <> (select &ldquo;Privacy Request&rdquo;) or email{' '}
              <a href={`mailto:privacy@${PUBLICATION_DOMAIN}`} style={{ color: 'var(--color-link)' }}>
                privacy@{PUBLICATION_DOMAIN}
              </a>
            </>
          )}
          .
        </p>
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontSize:   '14px',
            lineHeight: 1.7,
            color:      'var(--color-text-secondary-light)',
            margin:     0,
          }}
        >
          For the full details of our privacy practices, see our{' '}
          <Link href="/privacy" style={{ color: 'var(--color-link)' }}>
            Privacy Policy
          </Link>.
        </p>
      </div>
    </div>
  );
}
