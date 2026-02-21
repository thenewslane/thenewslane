import React from 'react';
import { categoryColorVar } from './utils';

export interface CategoryBadgeProps {
  /** Category display name or slug (e.g. "Technology", "business-finance"). */
  category: string;
  style?: React.CSSProperties;
  className?: string;
}

export function CategoryBadge({ category, style, className }: CategoryBadgeProps) {
  return (
    <span
      className={className}
      style={{
        display:         'inline-block',
        padding:         '2px var(--spacing-2)',
        borderRadius:    'var(--radius-small)',
        backgroundColor: categoryColorVar(category),
        color:           '#fff',
        fontSize:        '10px',
        fontWeight:      700,
        fontFamily:      'var(--font-body)',
        letterSpacing:   '0.06em',
        textTransform:   'uppercase',
        lineHeight:      1.6,
        whiteSpace:      'nowrap',
        ...style,
      }}
    >
      {category}
    </span>
  );
}
