'use client';

import React, { useCallback } from 'react';
import type { TrendingTopic } from '@platform/types';
import { CategoryBadge }    from './CategoryBadge';
import { ViralIndicator }   from './ViralIndicator';
import { SourceAttribution } from './SourceAttribution';
import { truncateWords }    from './utils';

export interface TopicCardProps {
  topic:   TrendingTopic;
  onPress: (topic: TrendingTopic) => void;
  /** Disable the card link (e.g. while navigating). */
  disabled?: boolean;
}

export function TopicCard({ topic, onPress, disabled = false }: TopicCardProps) {
  const summary = topic.summary ? truncateWords(topic.summary, 80) : null;
  const categoryName = topic.category?.name ?? null;
  const categorySlug = topic.category?.slug ?? null;

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      if (!disabled) onPress(topic);
    },
    [disabled, onPress, topic],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
        e.preventDefault();
        onPress(topic);
      }
    },
    [disabled, onPress, topic],
  );

  return (
    <article
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label={topic.title}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      style={{
        display:         'flex',
        flexDirection:   'column',
        borderRadius:    'var(--radius-medium)',
        overflow:        'hidden',
        backgroundColor: 'var(--color-card-light)',
        boxShadow:       '0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06)',
        cursor:          disabled ? 'default' : 'pointer',
        transition:      'box-shadow 0.15s ease, transform 0.15s ease',
        outline:         'none',
      }}
      onMouseEnter={e => {
        if (!disabled) {
          (e.currentTarget as HTMLElement).style.boxShadow =
            '0 4px 12px rgba(0,0,0,.12), 0 2px 4px rgba(0,0,0,.08)';
          (e.currentTarget as HTMLElement).style.transform = 'translateY(-1px)';
        }
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLElement).style.boxShadow =
          '0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06)';
        (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
      }}
      onFocus={e => {
        (e.currentTarget as HTMLElement).style.outline =
          '2px solid var(--color-primary)';
      }}
      onBlur={e => {
        (e.currentTarget as HTMLElement).style.outline = 'none';
      }}
    >
      {/* Thumbnail */}
      {topic.thumbnail_url && (
        <div
          style={{
            position:       'relative',
            width:          '100%',
            paddingTop:     '52.5%', // 16:8.4 aspect ratio
            backgroundColor: 'var(--color-background-dark)',
            overflow:       'hidden',
          }}
        >
          <img
            src={topic.thumbnail_url}
            alt={topic.title}
            loading="lazy"
            style={{
              position:   'absolute',
              inset:      0,
              width:      '100%',
              height:     '100%',
              objectFit:  'cover',
            }}
          />
        </div>
      )}

      {/* Content */}
      <div
        style={{
          display:        'flex',
          flexDirection:  'column',
          gap:            'var(--spacing-2)',
          padding:        'var(--spacing-3)',
          flexGrow:       1,
        }}
      >
        {/* Badges row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-2)', flexWrap: 'wrap' }}>
          {topic.viral_tier != null && topic.viral_score != null && (
            <ViralIndicator tier={topic.viral_tier} score={topic.viral_score} />
          )}
          {categoryName && categorySlug && (
            <CategoryBadge category={categorySlug} />
          )}
        </div>

        {/* Title */}
        <h2
          style={{
            margin:      0,
            fontSize:    '16px',
            fontWeight:  700,
            fontFamily:  'var(--font-heading)',
            color:       'var(--color-text-primary-light)',
            lineHeight:  1.35,
            // 2-line clamp
            display:            '-webkit-box',
            WebkitLineClamp:    2,
            WebkitBoxOrient:    'vertical' as const,
            overflow:           'hidden',
          }}
        >
          {topic.title}
        </h2>

        {/* Summary — 3-line clamp */}
        {summary && (
          <p
            style={{
              margin:      0,
              fontSize:    '13px',
              lineHeight:  1.55,
              fontFamily:  'var(--font-body)',
              color:       'var(--color-text-secondary-light)',
              // 3-line clamp
              display:            '-webkit-box',
              WebkitLineClamp:    3,
              WebkitBoxOrient:    'vertical' as const,
              overflow:           'hidden',
            }}
          >
            {summary}
          </p>
        )}

        {/* Footer */}
        <div style={{ marginTop: 'auto', paddingTop: 'var(--spacing-1)' }}>
          <SourceAttribution
            sourceName="theNewslane"
            publishedAt={topic.published_at ?? topic.created_at}
          />
        </div>
      </div>
    </article>
  );
}
