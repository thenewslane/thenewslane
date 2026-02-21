'use client';

/**
 * FaqAccordion
 *
 * Renders an FAQ section from schema_blocks that contain FAQPage schema entries.
 * Each question/answer pair is an accessible <details>/<summary> accordion.
 */

import React, { useState } from 'react';

export interface FaqItem {
  question: string;
  answer:   string;
}

export interface FaqAccordionProps {
  items: FaqItem[];
}

export function FaqAccordion({ items }: FaqAccordionProps) {
  if (!items.length) return null;

  return (
    <section aria-label="Frequently Asked Questions" style={{ marginTop: 'var(--spacing-8)' }}>
      <h2
        style={{
          fontFamily:   'var(--font-heading)',
          fontSize:     'clamp(18px, 3vw, 24px)',
          fontWeight:   700,
          color:        'var(--color-text-primary-light)',
          marginBottom: 'var(--spacing-4)',
        }}
      >
        Frequently Asked Questions
      </h2>

      <div
        style={{
          display:       'flex',
          flexDirection: 'column',
          gap:           'var(--spacing-2)',
        }}
      >
        {items.map((item, idx) => (
          <AccordionItem key={idx} item={item} />
        ))}
      </div>
    </section>
  );
}

function AccordionItem({ item }: { item: FaqItem }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      style={{
        border:       '1px solid rgba(0,0,0,.1)',
        borderRadius: 'var(--radius-medium)',
        overflow:     'hidden',
      }}
    >
      <button
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        style={{
          width:           '100%',
          display:         'flex',
          justifyContent:  'space-between',
          alignItems:      'center',
          padding:         'var(--spacing-3) var(--spacing-4)',
          backgroundColor: open ? 'color-mix(in srgb, var(--color-primary) 6%, transparent)' : 'var(--color-card-light)',
          border:          'none',
          cursor:          'pointer',
          textAlign:       'left',
          gap:             'var(--spacing-3)',
          transition:      'background-color 0.15s',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-body)',
            fontSize:   '15px',
            fontWeight: 600,
            color:      'var(--color-text-primary-light)',
            lineHeight: 1.4,
          }}
        >
          {item.question}
        </span>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--color-text-muted-light)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
          style={{
            flexShrink: 0,
            transform:  open ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div
          style={{
            padding:    'var(--spacing-3) var(--spacing-4) var(--spacing-4)',
            borderTop:  '1px solid rgba(0,0,0,.07)',
            backgroundColor: 'var(--color-card-light)',
          }}
        >
          <p
            style={{
              margin:     0,
              fontFamily: 'var(--font-body)',
              fontSize:   '14px',
              lineHeight: 1.7,
              color:      'var(--color-text-secondary-light)',
            }}
          >
            {item.answer}
          </p>
        </div>
      )}
    </div>
  );
}
