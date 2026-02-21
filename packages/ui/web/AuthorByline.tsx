import React from 'react';
import { formatTimeAgo } from './utils';

export interface AuthorBylineProps {
  authorName:  string;
  publishedAt: string; // ISO-8601
  aboutHref?:  string; // link to about/author page
}

export function AuthorByline({ authorName, publishedAt, aboutHref = '/about' }: AuthorBylineProps) {
  return (
    <div
      style={{
        display:    'flex',
        alignItems: 'center',
        gap:        'var(--spacing-2)',
        fontSize:   '13px',
        fontFamily: 'var(--font-body)',
        color:      'var(--color-text-secondary-light)',
      }}
    >
      <span>By&nbsp;
        <a
          href={aboutHref}
          style={{
            color:          'var(--color-link)',
            textDecoration: 'none',
            fontWeight:     500,
          }}
        >
          {authorName}
        </a>
      </span>

      <span
        aria-label="AI-assisted article"
        title="This article was written with AI assistance"
        style={{
          display:         'inline-flex',
          alignItems:      'center',
          gap:             '3px',
          padding:         '1px 6px',
          borderRadius:    'var(--radius-small)',
          backgroundColor: 'color-mix(in srgb, var(--color-accent) 12%, transparent)',
          color:           'var(--color-accent)',
          fontSize:        '10px',
          fontWeight:      700,
          letterSpacing:   '0.04em',
          textTransform:   'uppercase',
        }}
      >
        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <path d="M12 2a1 1 0 0 1 .894.553l2.382 4.764 5.298.77a1 1 0 0 1 .555 1.706l-3.834 3.735.905 5.276a1 1 0 0 1-1.451 1.054L12 17.347l-4.749 2.511a1 1 0 0 1-1.451-1.054l.905-5.276L2.871 9.793a1 1 0 0 1 .555-1.706l5.298-.77 2.382-4.764A1 1 0 0 1 12 2z"/>
        </svg>
        AI‑assisted
      </span>

      <span aria-hidden style={{ opacity: 0.35 }}>·</span>

      <time dateTime={publishedAt} style={{ opacity: 0.75 }}>
        {formatTimeAgo(publishedAt)}
      </time>
    </div>
  );
}
