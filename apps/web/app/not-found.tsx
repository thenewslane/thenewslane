/**
 * 404 Not Found — custom branded page.
 *
 * Shown automatically by Next.js when no route matches.
 * Server component — no 'use client' needed.
 */

import type { Metadata } from 'next';
import Link from 'next/link';

const PUBLICATION_NAME = process.env.PUBLICATION_NAME ?? 'theNewslane';

export const metadata: Metadata = {
  title: `Page Not Found · ${PUBLICATION_NAME}`,
};

export default function NotFound() {
  return (
    <div
      style={{
        minHeight:      '70vh',
        display:        'flex',
        flexDirection:  'column',
        alignItems:     'center',
        justifyContent: 'center',
        textAlign:      'center',
        padding:        'var(--spacing-12) var(--spacing-4)',
      }}
    >
      {/* Large 404 */}
      <p
        style={{
          fontFamily:  'var(--font-heading)',
          fontSize:    'clamp(72px, 15vw, 128px)',
          fontWeight:  800,
          color:       'var(--color-primary)',
          margin:      0,
          lineHeight:  1,
          opacity:     0.15,
          userSelect:  'none',
        }}
        aria-hidden
      >
        404
      </p>

      {/* Icon */}
      <div
        style={{
          marginTop:       '-var(--spacing-8)',
          marginBottom:    'var(--spacing-5)',
          display:         'flex',
          alignItems:      'center',
          justifyContent:  'center',
          width:           72,
          height:          72,
          borderRadius:    '50%',
          backgroundColor: 'color-mix(in srgb, var(--color-primary) 10%, transparent)',
        }}
      >
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
          <path d="M11 8v3M11 14h.01"/>
        </svg>
      </div>

      <h1
        style={{
          fontFamily:   'var(--font-heading)',
          fontSize:     'clamp(22px, 4vw, 30px)',
          fontWeight:   700,
          color:        'var(--color-text-primary-light)',
          margin:       '0 0 var(--spacing-3)',
        }}
      >
        This page doesn&apos;t exist
      </h1>

      <p
        style={{
          fontFamily:  'var(--font-body)',
          fontSize:    '15px',
          lineHeight:  1.65,
          color:       'var(--color-text-secondary-light)',
          maxWidth:    420,
          margin:      '0 0 var(--spacing-8)',
        }}
      >
        The article or page you&apos;re looking for may have been removed,
        renamed, or never existed. Check the URL or head back to the feed.
      </p>

      <div style={{ display: 'flex', gap: 'var(--spacing-3)', flexWrap: 'wrap', justifyContent: 'center' }}>
        <Link
          href="/"
          style={{
            display:         'inline-block',
            padding:         'var(--spacing-2) var(--spacing-6)',
            borderRadius:    'var(--radius-small)',
            border:          'none',
            backgroundColor: 'var(--color-primary)',
            color:           '#fff',
            fontFamily:      'var(--font-body)',
            fontWeight:      700,
            fontSize:        '15px',
            textDecoration:  'none',
          }}
        >
          Back to {PUBLICATION_NAME}
        </Link>
        <Link
          href="/contact"
          style={{
            display:         'inline-block',
            padding:         'var(--spacing-2) var(--spacing-6)',
            borderRadius:    'var(--radius-small)',
            border:          '1.5px solid rgba(0,0,0,.15)',
            backgroundColor: 'transparent',
            color:           'var(--color-text-secondary-light)',
            fontFamily:      'var(--font-body)',
            fontWeight:      600,
            fontSize:        '15px',
            textDecoration:  'none',
          }}
        >
          Report broken link
        </Link>
      </div>
    </div>
  );
}
