import React from 'react';
import { formatTimeAgo } from './utils';

export interface SourceAttributionProps {
  sourceName:  string;
  sourceUrl?:  string;
  publishedAt: string; // ISO-8601
}

export function SourceAttribution({ sourceName, sourceUrl, publishedAt }: SourceAttributionProps) {
  const hostname = sourceUrl
    ? (() => { try { return new URL(sourceUrl).hostname; } catch { return null; } })()
    : null;

  const faviconSrc = hostname
    ? `https://www.google.com/s2/favicons?sz=16&domain=${hostname}`
    : null;

  const timeLabel = formatTimeAgo(publishedAt);

  return (
    <span
      style={{
        display:    'inline-flex',
        alignItems: 'center',
        gap:        'var(--spacing-1)',
        fontSize:   '12px',
        fontFamily: 'var(--font-body)',
        color:      'var(--color-text-secondary-light)',
      }}
    >
      {faviconSrc && (
        <img
          src={faviconSrc}
          alt=""
          width={14}
          height={14}
          style={{ borderRadius: '2px', flexShrink: 0 }}
        />
      )}
      {sourceUrl ? (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color:          'inherit',
            textDecoration: 'none',
            fontWeight:     500,
          }}
        >
          {sourceName}
        </a>
      ) : (
        <span style={{ fontWeight: 500 }}>{sourceName}</span>
      )}
      <span aria-hidden style={{ opacity: 0.4 }}>·</span>
      <time dateTime={publishedAt} style={{ opacity: 0.75 }}>
        {timeLabel}
      </time>
    </span>
  );
}
