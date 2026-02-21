'use client';

/**
 * CategoryFilter
 *
 * Horizontally scrollable pill tabs for filtering topics by category.
 * "All" is always the first pill. Active pill highlights with brand primary.
 */

import React from 'react';
import type { Category } from '@platform/types';

export interface CategoryFilterProps {
  categories:       Category[];
  activeCategory:   string | null; // null = "All"
  onSelect:         (slug: string | null) => void;
}

export function CategoryFilter({ categories, activeCategory, onSelect }: CategoryFilterProps) {
  const pills: { label: string; slug: string | null }[] = [
    { label: 'All', slug: null },
    ...categories.map(c => ({ label: c.name, slug: c.slug })),
  ];

  return (
    <nav
      aria-label="Filter by category"
      style={{
        overflowX:    'auto',
        overflowY:    'hidden',
        display:      'flex',
        gap:          'var(--spacing-2)',
        paddingBottom: 'var(--spacing-1)',
        // hide scrollbar visually but keep it functional
        scrollbarWidth: 'none',
        msOverflowStyle: 'none' as React.CSSProperties['msOverflowStyle'],
      }}
    >
      {pills.map(({ label, slug }) => {
        const isActive = activeCategory === slug;
        return (
          <button
            key={slug ?? '__all__'}
            onClick={() => onSelect(slug)}
            aria-pressed={isActive}
            style={{
              flexShrink:      0,
              padding:         'var(--spacing-1) var(--spacing-4)',
              borderRadius:    '999px',
              border:          isActive
                ? '1.5px solid var(--color-primary)'
                : '1.5px solid rgba(0,0,0,.12)',
              backgroundColor: isActive ? 'var(--color-primary)' : 'transparent',
              color:           isActive ? '#fff' : 'var(--color-text-secondary-light)',
              fontSize:        '13px',
              fontWeight:      isActive ? 700 : 500,
              fontFamily:      'var(--font-body)',
              cursor:          'pointer',
              whiteSpace:      'nowrap',
              transition:      'background-color 0.15s, color 0.15s, border-color 0.15s',
            }}
          >
            {label}
          </button>
        );
      })}
    </nav>
  );
}
