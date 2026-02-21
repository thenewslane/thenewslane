import React from 'react';
import type { Category } from '@platform/types';
import { categoryColorVar } from './utils';

export interface CategoryPickerProps {
  categories:    Category[];
  selected:      number[];        // selected category IDs
  onChange:      (ids: number[]) => void;
  maxSelections?: number;         // default 3
}

export function CategoryPicker({
  categories,
  selected,
  onChange,
  maxSelections = 3,
}: CategoryPickerProps) {
  function toggle(id: number) {
    if (selected.includes(id)) {
      onChange(selected.filter(s => s !== id));
    } else if (selected.length < maxSelections) {
      onChange([...selected, id]);
    }
  }

  const atMax = selected.length >= maxSelections;

  return (
    <div role="group" aria-label={`Select up to ${maxSelections} categories`}>
      {/* Hint */}
      <p
        style={{
          margin:     '0 0 var(--spacing-3)',
          fontSize:   '13px',
          fontFamily: 'var(--font-body)',
          color:      'var(--color-text-secondary-light)',
        }}
      >
        {selected.length}/{maxSelections} selected
      </p>

      {/* Grid */}
      <div
        style={{
          display:             'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
          gap:                 'var(--spacing-2)',
        }}
      >
        {categories.map(cat => {
          const isSelected = selected.includes(cat.id);
          const isDisabled = !isSelected && atMax;
          const accentColor = categoryColorVar(cat.slug);

          return (
            <button
              key={cat.id}
              role="checkbox"
              aria-checked={isSelected}
              aria-disabled={isDisabled}
              disabled={isDisabled}
              onClick={() => toggle(cat.id)}
              style={{
                display:         'flex',
                flexDirection:   'column',
                alignItems:      'flex-start',
                gap:             'var(--spacing-1)',
                padding:         'var(--spacing-3)',
                borderRadius:    'var(--radius-medium)',
                border:          `2px solid ${isSelected ? accentColor : 'transparent'}`,
                backgroundColor: isSelected
                  ? `color-mix(in srgb, ${accentColor} 12%, var(--color-card-light))`
                  : 'var(--color-card-light)',
                boxShadow:       '0 1px 3px rgba(0,0,0,.07)',
                cursor:          isDisabled ? 'not-allowed' : 'pointer',
                opacity:         isDisabled ? 0.45 : 1,
                transition:      'border-color 0.15s, background-color 0.15s, opacity 0.15s',
                textAlign:       'left',
                // Reset button styles
                font:            'inherit',
              }}
            >
              {/* Category colour swatch */}
              <span
                aria-hidden
                style={{
                  width:           28,
                  height:          4,
                  borderRadius:    2,
                  backgroundColor: accentColor,
                  display:         'block',
                }}
              />

              <span
                style={{
                  fontSize:   '13px',
                  fontWeight: isSelected ? 700 : 500,
                  fontFamily: 'var(--font-body)',
                  color:      isSelected
                    ? 'var(--color-text-primary-light)'
                    : 'var(--color-text-secondary-light)',
                  lineHeight: 1.3,
                }}
              >
                {cat.name}
              </span>

              {/* Checkmark */}
              {isSelected && (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden
                  style={{
                    color:     accentColor,
                    alignSelf: 'flex-end',
                    marginTop: 'auto',
                  }}
                >
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
