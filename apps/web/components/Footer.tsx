/**
 * Footer — server component.
 *
 * Compliance links: Privacy Policy, Terms of Service, Cookie Settings,
 * DMCA, About, Contact. "Cookie Settings" re-opens the ConsentBanner
 * via the CookieSettingsButton client component.
 *
 * Required env vars:
 *   PUBLICATION_NAME    — e.g. "theNewslane"
 *   AUTHOR_NAME         — e.g. "Aadi"
 *   PUBLICATION_DOMAIN  — e.g. "thenewslane.com"
 */

import Link                    from 'next/link';
import { CookieSettingsButton } from './CookieSettingsButton';

const PUBLICATION_NAME   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const AUTHOR_NAME        = process.env.AUTHOR_NAME        ?? '';
const PUBLICATION_DOMAIN = process.env.PUBLICATION_DOMAIN ?? '';

const COMPLIANCE_LINKS = [
  { href: '/privacy',        label: 'Privacy Policy' },
  { href: '/terms',          label: 'Terms of Service' },
  { href: '/dmca',           label: 'DMCA' },
  { href: '/about',          label: 'About' },
  { href: '/contact',        label: 'Contact' },
] as const;

const CATEGORY_LINKS = [
  { href: '/category/technology',      label: 'Technology' },
  { href: '/category/politics',        label: 'Politics' },
  { href: '/category/entertainment',   label: 'Entertainment' },
  { href: '/category/sports',          label: 'Sports' },
  { href: '/category/business-finance',label: 'Business & Finance' },
  { href: '/category/health-science',  label: 'Health & Science' },
  { href: '/category/world-news',      label: 'World News' },
  { href: '/category/lifestyle',       label: 'Lifestyle' },
  { href: '/category/culture-arts',    label: 'Culture & Arts' },
  { href: '/category/environment',     label: 'Environment' },
] as const;

const linkStyle: React.CSSProperties = {
  color:           'var(--color-text-secondary-light)',
  fontSize:        13,
  fontFamily:      'var(--font-body)',
  textDecoration:  'none',
  transition:      'color 0.15s',
};

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer
      style={{
        borderTop:       '1px solid rgba(0,0,0,.08)',
        backgroundColor: 'var(--color-card-light)',
        marginTop:       'var(--spacing-16)',
      }}
    >
      <div className="site-container">
        {/* ── Main footer content ─────────────────────────────────────── */}
        <div
          style={{
            display:             'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap:                 'var(--spacing-8)',
            padding:             'var(--spacing-12) 0',
          }}
        >
          {/* Brand column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-2)' }}>
              <span
                aria-hidden
                style={{
                  width:           24,
                  height:          24,
                  borderRadius:    'var(--radius-small)',
                  backgroundColor: 'var(--color-primary)',
                  display:         'block',
                  flexShrink:      0,
                }}
              />
              <span
                style={{
                  fontFamily:  'var(--font-heading)',
                  fontWeight:  700,
                  fontSize:    18,
                  color:       'var(--color-text-primary-light)',
                }}
              >
                {PUBLICATION_NAME}
              </span>
            </div>
            <p
              style={{
                fontSize:   13,
                lineHeight: 1.65,
                color:      'var(--color-text-secondary-light)',
                fontFamily: 'var(--font-body)',
                margin:     0,
              }}
            >
              AI-curated trending news.
              {PUBLICATION_DOMAIN && (
                <> Published at{' '}
                  <a
                    href={`https://${PUBLICATION_DOMAIN}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--color-link)' }}
                  >
                    {PUBLICATION_DOMAIN}
                  </a>
                </>
              )}
            </p>
            {/* AI disclosure */}
            <p
              style={{
                fontSize:        11,
                lineHeight:      1.5,
                color:           'var(--color-text-muted-light)',
                fontFamily:      'var(--font-body)',
                margin:          0,
                padding:         'var(--spacing-2) var(--spacing-3)',
                backgroundColor: 'rgba(0,0,0,.04)',
                borderRadius:    'var(--radius-small)',
              }}
            >
              Articles on this site are AI-assisted and reviewed for accuracy.
              Content may not reflect the views of editors.
            </p>
          </div>

          {/* Categories column */}
          <div>
            <h3
              style={{
                fontSize:     11,
                fontWeight:   700,
                fontFamily:   'var(--font-body)',
                color:        'var(--color-text-muted-light)',
                letterSpacing:'0.08em',
                textTransform:'uppercase',
                margin:       '0 0 var(--spacing-3)',
              }}
            >
              Categories
            </h3>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
              {CATEGORY_LINKS.map(({ href, label }) => (
                <li key={href}>
                  <Link href={href} style={linkStyle}>{label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal column */}
          <div>
            <h3
              style={{
                fontSize:     11,
                fontWeight:   700,
                fontFamily:   'var(--font-body)',
                color:        'var(--color-text-muted-light)',
                letterSpacing:'0.08em',
                textTransform:'uppercase',
                margin:       '0 0 var(--spacing-3)',
              }}
            >
              Legal
            </h3>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
              {COMPLIANCE_LINKS.map(({ href, label }) => (
                <li key={href}>
                  <Link href={href} style={linkStyle}>{label}</Link>
                </li>
              ))}
              <li>
                <span style={linkStyle}>
                  <CookieSettingsButton />
                </span>
              </li>
            </ul>
          </div>
        </div>

        {/* ── Bottom bar ──────────────────────────────────────────────── */}
        <div
          style={{
            borderTop:      '1px solid rgba(0,0,0,.07)',
            padding:        'var(--spacing-4) 0',
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'space-between',
            flexWrap:       'wrap',
            gap:            'var(--spacing-2)',
          }}
        >
          <p
            style={{
              margin:     0,
              fontSize:   12,
              fontFamily: 'var(--font-body)',
              color:      'var(--color-text-muted-light)',
            }}
          >
            &copy; {year} {PUBLICATION_NAME}
            {AUTHOR_NAME && ` · by ${AUTHOR_NAME}`}.
            All rights reserved.
          </p>
          <p
            style={{
              margin:     0,
              fontSize:   12,
              fontFamily: 'var(--font-body)',
              color:      'var(--color-text-muted-light)',
            }}
          >
            Powered by AI ·{' '}
            <Link
              href="/sitemap.xml"
              style={{ color: 'var(--color-text-muted-light)', textDecoration: 'underline' }}
            >
              Sitemap
            </Link>
          </p>
        </div>
      </div>
    </footer>
  );
}
