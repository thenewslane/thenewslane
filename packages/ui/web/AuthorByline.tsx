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

      <span aria-hidden style={{ opacity: 0.35 }}>·</span>

      <time dateTime={publishedAt} style={{ opacity: 0.75 }}>
        {formatTimeAgo(publishedAt)}
      </time>
    </div>
  );
}
