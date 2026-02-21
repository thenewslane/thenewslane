/**
 * About page — /about  (server component, static)
 *
 * Sections:
 *   1. Author profile (photo, name, title, bio)
 *   2. Publication mission statement
 *   3. How AI curation works (editorial process)
 *   4. Link to editorial policy
 */

import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';

const PUBLICATION_NAME   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const AUTHOR_NAME        = process.env.AUTHOR_NAME        ?? 'The Editor';
const PUBLICATION_DOMAIN = process.env.PUBLICATION_DOMAIN ?? '';
const AUTHOR_PHOTO_URL   = process.env.AUTHOR_PHOTO_URL   ?? '';

export const metadata: Metadata = {
  title:       `About · ${PUBLICATION_NAME}`,
  description: `Meet the team behind ${PUBLICATION_NAME} and learn how we curate trending news with AI.`,
};

const sectionHeadingStyle: React.CSSProperties = {
  fontFamily:   'var(--font-heading)',
  fontSize:     'clamp(18px, 3vw, 24px)',
  fontWeight:   700,
  color:        'var(--color-text-primary-light)',
  margin:       '0 0 var(--spacing-3)',
};

const bodyStyle: React.CSSProperties = {
  fontFamily: 'var(--font-body)',
  fontSize:   '15px',
  lineHeight: 1.75,
  color:      'var(--color-text-secondary-light)',
  margin:     '0 0 var(--spacing-4)',
};

const dividerStyle: React.CSSProperties = {
  border:     'none',
  borderTop:  '1px solid rgba(0,0,0,.08)',
  margin:     'var(--spacing-10) 0',
};

export default function AboutPage() {
  return (
    <div
      style={{
        maxWidth: 680,
        margin:   '0 auto',
        padding:  'var(--spacing-12) var(--spacing-4) var(--spacing-16)',
      }}
    >
      {/* ── Page title ──────────────────────────────────────────────────── */}
      <h1
        style={{
          fontFamily:   'var(--font-heading)',
          fontSize:     'clamp(28px, 5vw, 42px)',
          fontWeight:   800,
          color:        'var(--color-text-primary-light)',
          margin:       '0 0 var(--spacing-2)',
          lineHeight:   1.15,
        }}
      >
        About {PUBLICATION_NAME}
      </h1>
      <p
        style={{
          fontFamily: 'var(--font-body)',
          fontSize:   '17px',
          lineHeight: 1.6,
          color:      'var(--color-text-secondary-light)',
          margin:     '0 0 var(--spacing-10)',
        }}
      >
        AI-powered trend intelligence, delivered with editorial integrity.
      </p>

      {/* ── Author profile ───────────────────────────────────────────────── */}
      <section aria-labelledby="author-heading">
        <h2 id="author-heading" style={sectionHeadingStyle}>Meet the Editor</h2>
        <div
          style={{
            display:       'flex',
            gap:           'var(--spacing-6)',
            alignItems:    'flex-start',
            flexWrap:      'wrap',
            marginBottom:  'var(--spacing-6)',
          }}
        >
          {/* Author photo */}
          <div
            style={{
              flexShrink: 0,
              width:      112,
              height:     112,
              borderRadius: '50%',
              overflow:   'hidden',
              backgroundColor: 'rgba(0,0,0,.08)',
              border:     '3px solid var(--color-primary)',
            }}
          >
            {AUTHOR_PHOTO_URL ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={AUTHOR_PHOTO_URL}
                alt={`${AUTHOR_NAME} — Editor`}
                width={112}
                height={112}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            ) : (
              /* Placeholder initials */
              <div
                style={{
                  width:           '100%',
                  height:          '100%',
                  display:         'flex',
                  alignItems:      'center',
                  justifyContent:  'center',
                  backgroundColor: 'var(--color-primary)',
                  color:           '#fff',
                  fontSize:        36,
                  fontWeight:      700,
                  fontFamily:      'var(--font-heading)',
                }}
              >
                {AUTHOR_NAME.charAt(0).toUpperCase()}
              </div>
            )}
          </div>

          {/* Author details */}
          <div style={{ flex: 1, minWidth: 200 }}>
            <p
              style={{
                fontFamily:  'var(--font-heading)',
                fontSize:    '20px',
                fontWeight:  700,
                color:       'var(--color-text-primary-light)',
                margin:      '0 0 var(--spacing-1)',
              }}
            >
              {AUTHOR_NAME}
            </p>
            <p
              style={{
                fontFamily: 'var(--font-body)',
                fontSize:   '13px',
                fontWeight: 600,
                color:      'var(--color-primary)',
                margin:     '0 0 var(--spacing-3)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              Founder &amp; Editor-in-Chief
            </p>
            <p style={{ ...bodyStyle, margin: 0 }}>
              {AUTHOR_NAME} founded {PUBLICATION_NAME} to prove that AI and editorial
              craftsmanship can coexist. With a background in digital media and machine
              learning, {AUTHOR_NAME} designed the platform&apos;s viral-prediction
              engine and oversees all editorial decisions — from the categories we cover
              to the stories that make the front page.
            </p>
          </div>
        </div>
      </section>

      <hr style={dividerStyle} />

      {/* ── Mission ──────────────────────────────────────────────────────── */}
      <section aria-labelledby="mission-heading">
        <h2 id="mission-heading" style={sectionHeadingStyle}>Our Mission</h2>
        <p style={bodyStyle}>
          {PUBLICATION_NAME} exists to surface the stories that matter before they
          saturate your feed. Every four hours, our pipeline scans thousands of signals
          across social platforms, news wires, and search trends — then applies a
          purpose-built viral-prediction model to identify what is genuinely gaining
          momentum right now.
        </p>
        <p style={bodyStyle}>
          We believe readers deserve to know <em>why</em> something is trending, not
          just <em>that</em> it is. That is why every article pairs AI-generated context
          with a clear signal breakdown and, where applicable, expert commentary.
        </p>
        <p style={bodyStyle}>
          Our goal is not traffic maximisation — it is trust. We reject sensational or
          harmful content regardless of its viral score, and we label AI-generated
          material clearly so you always know what you are reading.
        </p>
      </section>

      <hr style={dividerStyle} />

      {/* ── Editorial process ────────────────────────────────────────────── */}
      <section aria-labelledby="process-heading">
        <h2 id="process-heading" style={sectionHeadingStyle}>How AI Curation Works</h2>
        <p style={bodyStyle}>
          Our editorial pipeline runs automatically every four hours and follows a
          strict, multi-stage process:
        </p>

        {/* Steps */}
        {[
          {
            n:    '01',
            title:'Signal Collection',
            body: `We aggregate trending signals from social media platforms, search-trend APIs,
                   and news-wire feeds. Each signal is scored for velocity (how fast it is growing)
                   and cross-platform spread (how many independent communities are discussing it).`,
          },
          {
            n:    '02',
            title:'Viral Prediction',
            body: `A weighted linear model combines cross-platform score, velocity ratio,
                   acceleration, publication gap, sentiment polarity, time-of-day, and
                   category multipliers into a single viral score between 0 and 1.
                   Topics scoring 40–60% are further validated by a Claude Haiku LLM judge
                   to reduce false positives.`,
          },
          {
            n:    '03',
            title:'Brand Safety & Rejection',
            body: `Every candidate passes through an automated brand-safety filter that
                   screens for NSFW content, hate speech, graphic violence, and
                   misinformation signals. Topics that fail are rejected before any
                   content is generated. Rejection reasons are logged for transparency.`,
          },
          {
            n:    '04',
            title:'AI Content Generation',
            body: `Approved topics are passed to Claude Sonnet — Anthropic's latest model —
                   which writes a concise summary, a full article, and platform-specific
                   social copy. The AI is explicitly instructed to be factual, balanced,
                   and to surface multiple perspectives where relevant.`,
          },
          {
            n:    '05',
            title:'Editorial Review & Publication',
            body: `${AUTHOR_NAME} reviews flagged topics daily and spot-checks the pipeline
                   output. Published articles carry an AI-content disclosure label.
                   Corrections are addressed within 24 hours of a verified report.`,
          },
        ].map(({ n, title, body }) => (
          <div
            key={n}
            style={{
              display:      'flex',
              gap:          'var(--spacing-4)',
              marginBottom: 'var(--spacing-6)',
            }}
          >
            <div
              style={{
                flexShrink:      0,
                width:           36,
                height:          36,
                borderRadius:    'var(--radius-small)',
                backgroundColor: 'var(--color-primary)',
                color:           '#fff',
                fontFamily:      'var(--font-heading)',
                fontWeight:      700,
                fontSize:        '12px',
                display:         'flex',
                alignItems:      'center',
                justifyContent:  'center',
              }}
            >
              {n}
            </div>
            <div style={{ flex: 1 }}>
              <p
                style={{
                  fontFamily:   'var(--font-body)',
                  fontSize:     '15px',
                  fontWeight:   700,
                  color:        'var(--color-text-primary-light)',
                  margin:       '0 0 var(--spacing-1)',
                }}
              >
                {title}
              </p>
              <p style={{ ...bodyStyle, margin: 0 }}>{body}</p>
            </div>
          </div>
        ))}
      </section>

      <hr style={dividerStyle} />

      {/* ── CTA to editorial policy ──────────────────────────────────────── */}
      <section aria-labelledby="policy-heading">
        <h2 id="policy-heading" style={sectionHeadingStyle}>Editorial Standards</h2>
        <p style={bodyStyle}>
          We hold our AI pipeline to the same standards we would apply to any
          human editorial team. For the full details — including our correction
          policy, brand safety exclusions, and user submission guidelines — see
          our Editorial Policy.
        </p>
        <Link
          href="/editorial-policy"
          style={{
            display:         'inline-block',
            padding:         'var(--spacing-2) var(--spacing-5)',
            borderRadius:    'var(--radius-small)',
            border:          '1.5px solid var(--color-primary)',
            color:           'var(--color-primary)',
            fontFamily:      'var(--font-body)',
            fontWeight:      700,
            fontSize:        '14px',
            textDecoration:  'none',
          }}
        >
          Read our Editorial Policy →
        </Link>
      </section>

      {/* ── Contact ──────────────────────────────────────────────────────── */}
      <hr style={dividerStyle} />
      <p
        style={{
          fontFamily: 'var(--font-body)',
          fontSize:   '13px',
          color:      'var(--color-text-muted-light)',
          margin:     0,
        }}
      >
        Questions or feedback?{' '}
        <Link href="/contact" style={{ color: 'var(--color-link)' }}>
          Get in touch
        </Link>
        {PUBLICATION_DOMAIN && (
          <> or email us at{' '}
            <a
              href={`mailto:editorial@${PUBLICATION_DOMAIN}`}
              style={{ color: 'var(--color-link)' }}
            >
              editorial@{PUBLICATION_DOMAIN}
            </a>
          </>
        )}
        .
      </p>
    </div>
  );
}
