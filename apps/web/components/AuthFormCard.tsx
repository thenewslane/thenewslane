/**
 * AuthFormCard
 *
 * Shared centred card wrapper used by login, register,
 * and other single-focus auth / flow pages.
 */

import React from 'react';

interface AuthFormCardProps {
  title:     string;
  subtitle?: string;
  children:  React.ReactNode;
  /** Wider layout for multi-section pages. Default 440px. */
  maxWidth?: number;
}

export function AuthFormCard({
  title,
  subtitle,
  children,
  maxWidth = 440,
}: AuthFormCardProps) {
  return (
    <div
      style={{
        minHeight:      'calc(100vh - 120px)',
        display:        'flex',
        alignItems:     'center',
        justifyContent: 'center',
        padding:        'var(--spacing-8) var(--spacing-4)',
      }}
    >
      <div
        style={{
          width:           '100%',
          maxWidth,
          backgroundColor: 'var(--color-card-light)',
          borderRadius:    'var(--radius-large)',
          boxShadow:       '0 4px 32px rgba(0,0,0,.10), 0 1px 4px rgba(0,0,0,.06)',
          padding:         'var(--spacing-8)',
        }}
      >
        {/* Brand mark */}
        <div style={{ marginBottom: 'var(--spacing-6)', textAlign: 'center' }}>
          <span
            style={{
              fontFamily:    'var(--font-heading)',
              fontSize:      '22px',
              fontWeight:    700,
              color:         'var(--color-primary)',
              letterSpacing: '-0.01em',
            }}
          >
            {process.env.NEXT_PUBLIC_PUBLICATION_NAME ?? 'theNewslane'}
          </span>
        </div>

        <h1
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     'clamp(20px, 4vw, 26px)',
            fontWeight:   700,
            color:        'var(--color-text-primary-light)',
            margin:       '0 0 var(--spacing-1)',
            textAlign:    'center',
          }}
        >
          {title}
        </h1>

        {subtitle && (
          <p
            style={{
              fontFamily:   'var(--font-body)',
              fontSize:     '14px',
              lineHeight:   1.6,
              color:        'var(--color-text-secondary-light)',
              margin:       '0 0 var(--spacing-6)',
              textAlign:    'center',
            }}
          >
            {subtitle}
          </p>
        )}

        {!subtitle && <div style={{ marginBottom: 'var(--spacing-6)' }} />}

        {children}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared style helpers — used inline across auth pages
// ---------------------------------------------------------------------------

export const inputStyle: React.CSSProperties = {
  width:           '100%',
  padding:         'var(--spacing-2) var(--spacing-3)',
  borderRadius:    'var(--radius-small)',
  border:          '1.5px solid rgba(0,0,0,.15)',
  backgroundColor: 'var(--color-background-light)',
  color:           'var(--color-text-primary-light)',
  fontSize:        '15px',
  fontFamily:      'var(--font-body)',
  outline:         'none',
  boxSizing:       'border-box',
  transition:      'border-color 0.15s',
};

export const primaryBtnStyle: React.CSSProperties = {
  width:           '100%',
  padding:         'var(--spacing-3)',
  borderRadius:    'var(--radius-small)',
  border:          'none',
  backgroundColor: 'var(--color-primary)',
  color:           '#fff',
  fontSize:        '15px',
  fontWeight:      700,
  fontFamily:      'var(--font-body)',
  cursor:          'pointer',
  letterSpacing:   '0.02em',
  transition:      'opacity 0.15s',
};

export const labelStyle: React.CSSProperties = {
  display:      'block',
  fontSize:     '13px',
  fontWeight:   600,
  fontFamily:   'var(--font-body)',
  color:        'var(--color-text-primary-light)',
  marginBottom: 'var(--spacing-1)',
};

export const errorStyle: React.CSSProperties = {
  padding:         'var(--spacing-2) var(--spacing-3)',
  borderRadius:    'var(--radius-small)',
  backgroundColor: 'color-mix(in srgb, var(--color-primary) 10%, transparent)',
  border:          '1px solid color-mix(in srgb, var(--color-primary) 30%, transparent)',
  color:           'var(--color-primary)',
  fontSize:        '13px',
  fontFamily:      'var(--font-body)',
  marginBottom:    'var(--spacing-4)',
};
