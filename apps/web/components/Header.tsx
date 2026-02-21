'use client';

/**
 * Header — site-wide navigation bar.
 *
 * Reads publication identity from environment variables — never hardcoded.
 * Required env vars:
 *   NEXT_PUBLIC_PUBLICATION_NAME  — display name  (e.g. "theNewslane")
 *   NEXT_PUBLIC_PUBLICATION_DOMAIN — canonical domain (e.g. "thenewslane.com")
 */

import React, { useState } from 'react';
import Link                 from 'next/link';
import { usePathname }      from 'next/navigation';

const PUBLICATION_NAME = process.env.NEXT_PUBLIC_PUBLICATION_NAME ?? 'theNewslane';

const NAV_LINKS = [
  { href: '/',                    label: 'Home' },
  { href: '/category/technology', label: 'Technology' },
  { href: '/category/politics',   label: 'Politics' },
  { href: '/category/sports',     label: 'Sports' },
  { href: '/trending',            label: 'Trending' },
  { href: '/about',               label: 'About' },
] as const;

export function Header() {
  const pathname    = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header
      style={{
        position:        'sticky',
        top:             0,
        zIndex:          50,
        backgroundColor: 'var(--color-card-light)',
        borderBottom:    '1px solid rgba(0,0,0,.08)',
        boxShadow:       '0 1px 4px rgba(0,0,0,.06)',
      }}
    >
      <div
        className="site-container"
        style={{
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'space-between',
          height:         60,
        }}
      >
        {/* ── Logo / wordmark ─────────────────────────────────────────── */}
        <Link
          href="/"
          aria-label={`${PUBLICATION_NAME} home`}
          style={{
            display:    'flex',
            alignItems: 'center',
            gap:        'var(--spacing-2)',
            textDecoration: 'none',
          }}
        >
          {/* Colour swatch acting as a simple logo mark */}
          <span
            aria-hidden
            style={{
              display:         'block',
              width:           28,
              height:          28,
              borderRadius:    'var(--radius-small)',
              backgroundColor: 'var(--color-primary)',
            }}
          />
          <span
            style={{
              fontFamily:  'var(--font-heading)',
              fontWeight:  700,
              fontSize:    20,
              color:       'var(--color-text-primary-light)',
              letterSpacing: '-0.02em',
            }}
          >
            {PUBLICATION_NAME}
          </span>
        </Link>

        {/* ── Desktop nav ─────────────────────────────────────────────── */}
        <nav aria-label="Main navigation" style={{ display: 'flex', gap: 'var(--spacing-1)' }}>
          {NAV_LINKS.map(({ href, label }) => {
            const isActive =
              href === '/'
                ? pathname === '/'
                : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                style={{
                  padding:         `var(--spacing-1) var(--spacing-3)`,
                  borderRadius:    'var(--radius-small)',
                  fontSize:        13,
                  fontWeight:      isActive ? 700 : 500,
                  fontFamily:      'var(--font-body)',
                  color:           isActive
                    ? 'var(--color-primary)'
                    : 'var(--color-text-secondary-light)',
                  textDecoration:  'none',
                  transition:      'color 0.15s, background-color 0.15s',
                  backgroundColor: isActive ? 'rgba(173,45,55,.08)' : 'transparent',
                  display:         'none', // hidden on mobile — overridden below
                }}
                className="md:inline-block hidden"
                aria-current={isActive ? 'page' : undefined}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        {/* ── Submit CTA ──────────────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-3)' }}>
          <Link
            href="/submit"
            style={{
              display:         'none', // hidden on mobile
              padding:         `var(--spacing-2) var(--spacing-4)`,
              borderRadius:    'var(--radius-small)',
              backgroundColor: 'var(--color-primary)',
              color:           '#fff',
              fontSize:        13,
              fontWeight:      700,
              fontFamily:      'var(--font-body)',
              textDecoration:  'none',
              whiteSpace:      'nowrap',
            }}
            className="sm:block hidden"
          >
            Submit Story
          </Link>

          {/* ── Mobile hamburger ──────────────────────────────────────── */}
          <button
            onClick={() => setMenuOpen(o => !o)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            style={{
              display:         'flex',
              flexDirection:   'column',
              gap:             5,
              padding:         'var(--spacing-2)',
              background:      'none',
              border:          'none',
              cursor:          'pointer',
              borderRadius:    'var(--radius-small)',
            }}
            className="md:hidden"
          >
            {[0, 1, 2].map(i => (
              <span
                key={i}
                aria-hidden
                style={{
                  display:         'block',
                  width:           20,
                  height:          2,
                  borderRadius:    1,
                  backgroundColor: 'var(--color-text-primary-light)',
                  transition:      'transform 0.2s, opacity 0.2s',
                  ...(menuOpen && i === 0 ? { transform: 'translateY(7px) rotate(45deg)' } : {}),
                  ...(menuOpen && i === 1 ? { opacity: 0 } : {}),
                  ...(menuOpen && i === 2 ? { transform: 'translateY(-7px) rotate(-45deg)' } : {}),
                }}
              />
            ))}
          </button>
        </div>
      </div>

      {/* ── Mobile nav drawer ─────────────────────────────────────────── */}
      {menuOpen && (
        <nav
          id="mobile-nav"
          aria-label="Mobile navigation"
          style={{
            borderTop:       '1px solid rgba(0,0,0,.08)',
            backgroundColor: 'var(--color-card-light)',
            padding:         'var(--spacing-3) var(--spacing-4)',
            display:         'flex',
            flexDirection:   'column',
            gap:             'var(--spacing-1)',
          }}
        >
          {NAV_LINKS.map(({ href, label }) => {
            const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setMenuOpen(false)}
                style={{
                  padding:         `var(--spacing-3) var(--spacing-3)`,
                  borderRadius:    'var(--radius-small)',
                  fontSize:        15,
                  fontWeight:      isActive ? 700 : 500,
                  fontFamily:      'var(--font-body)',
                  color:           isActive
                    ? 'var(--color-primary)'
                    : 'var(--color-text-primary-light)',
                  textDecoration:  'none',
                  backgroundColor: isActive ? 'rgba(173,45,55,.08)' : 'transparent',
                }}
                aria-current={isActive ? 'page' : undefined}
              >
                {label}
              </Link>
            );
          })}

          <Link
            href="/submit"
            onClick={() => setMenuOpen(false)}
            style={{
              marginTop:       'var(--spacing-2)',
              padding:         'var(--spacing-3)',
              borderRadius:    'var(--radius-small)',
              backgroundColor: 'var(--color-primary)',
              color:           '#fff',
              fontSize:        15,
              fontWeight:      700,
              fontFamily:      'var(--font-body)',
              textDecoration:  'none',
              textAlign:       'center',
            }}
          >
            Submit Story
          </Link>
        </nav>
      )}
    </header>
  );
}
