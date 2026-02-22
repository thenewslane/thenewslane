'use client';

import React, { useCallback } from 'react';
import type { TrendingTopic } from '@platform/types';
import { CategoryBadge }     from './CategoryBadge';
import { ViralIndicator }    from './ViralIndicator';
import { SourceAttribution } from './SourceAttribution';
import { truncateWords }     from './utils';

export interface TopicCardProps {
  topic:    TrendingTopic;
  onPress:  (topic: TrendingTopic) => void;
  disabled?: boolean;
}

/** Deterministic pastel-dark gradient from a string seed (category / title). */
function seedGradient(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash |= 0;
  }
  const palettes = [
    ['#0f3460', '#16213e'],
    ['#1a1a2e', '#533483'],
    ['#1b262c', '#0f4c75'],
    ['#1a1a2e', '#16213e'],
    ['#2d132c', '#ee4540'],
    ['#1b1b2f', '#162447'],
    ['#0a3d62', '#0c2461'],
    ['#130f40', '#30336b'],
  ];
  const [a, b] = palettes[Math.abs(hash) % palettes.length];
  return `linear-gradient(135deg, ${a} 0%, ${b} 100%)`;
}

export function TopicCard({ topic, onPress, disabled = false }: TopicCardProps) {
  const summary      = topic.summary ? truncateWords(topic.summary, 80) : null;
  const categoryName = topic.category?.name ?? null;
  const categorySlug = topic.category?.slug ?? null;
  const initial      = (topic.title ?? '?').charAt(0).toUpperCase();
  const gradient     = seedGradient(categorySlug ?? topic.title ?? '');

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
        (e.currentTarget as HTMLElement).style.outline = '2px solid var(--color-primary)';
      }}
      onBlur={e => {
        (e.currentTarget as HTMLElement).style.outline = 'none';
      }}
    >
      {/* ── Thumbnail / placeholder ── */}
      <div
        style={{
          position:        'relative',
          width:           '100%',
          paddingTop:      '52.5%',
          overflow:        'hidden',
          background:      gradient,
          flexShrink:      0,
        }}
      >
        {topic.thumbnail_url ? (
          <img
            src={topic.thumbnail_url}
            alt={topic.title}
            loading="lazy"
            style={{
              position:  'absolute',
              inset:     0,
              width:     '100%',
              height:    '100%',
              objectFit: 'cover',
            }}
          />
        ) : (
          /* Placeholder: big initial letter centred over gradient */
          <span
            aria-hidden
            style={{
              position:      'absolute',
              inset:         0,
              display:       'flex',
              alignItems:    'center',
              justifyContent:'center',
              fontSize:      'clamp(40px, 8vw, 64px)',
              fontWeight:    800,
              fontFamily:    'var(--font-heading)',
              color:         'rgba(255,255,255,0.18)',
              userSelect:    'none',
              letterSpacing: '-2px',
            }}
          >
            {initial}
          </span>
        )}

        {/* Category badge overlay on thumbnail */}
        {categoryName && categorySlug && (
          <div
            style={{
              position: 'absolute',
              bottom:   'var(--spacing-2)',
              left:     'var(--spacing-2)',
            }}
          >
            <CategoryBadge category={categorySlug} />
          </div>
        )}
      </div>

      {/* ── Text content ── */}
      <div
        style={{
          display:       'flex',
          flexDirection: 'column',
          gap:           'var(--spacing-2)',
          padding:       'var(--spacing-3)',
          flexGrow:      1,
        }}
      >
        {/* Viral indicator */}
        {topic.viral_tier != null && topic.viral_score != null && (
          <div>
            <ViralIndicator tier={topic.viral_tier} score={topic.viral_score} />
          </div>
        )}

        {/* Title */}
        <h2
          style={{
            margin:             0,
            fontSize:           '15px',
            fontWeight:         700,
            fontFamily:         'var(--font-heading)',
            color:              'var(--color-text-primary-light)',
            lineHeight:         1.35,
            display:            '-webkit-box',
            WebkitLineClamp:    2,
            WebkitBoxOrient:    'vertical' as const,
            overflow:           'hidden',
          }}
        >
          {topic.title}
        </h2>

        {/* Summary */}
        {summary && (
          <p
            style={{
              margin:          0,
              fontSize:        '13px',
              lineHeight:      1.55,
              fontFamily:      'var(--font-body)',
              color:           'var(--color-text-secondary-light)',
              display:         '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical' as const,
              overflow:        'hidden',
            }}
          >
            {summary}
          </p>
        )}

        {/* Footer */}
        <div
          style={{
            marginTop:      'auto',
            paddingTop:     'var(--spacing-2)',
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'space-between',
            gap:            'var(--spacing-2)',
          }}
        >
          <SourceAttribution
            sourceName="theNewslane"
            publishedAt={topic.published_at ?? topic.created_at}
          />
          <span
            aria-hidden
            style={{
              fontSize:      '12px',
              fontWeight:    600,
              fontFamily:    'var(--font-body)',
              color:         'var(--color-primary)',
              whiteSpace:    'nowrap',
              letterSpacing: '0.01em',
            }}
          >
            Read more →
          </span>
        </div>
      </div>
    </article>
  );
}
