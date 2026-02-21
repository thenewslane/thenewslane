/**
 * Editorial Policy page — /editorial-policy  (server component, static)
 *
 * Covers:
 *   - Topic selection criteria
 *   - AI labeling standards
 *   - Brand safety exclusions
 *   - User submission process
 *   - Correction policy
 *   - Contact information
 */

import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';

const PUBLICATION_NAME   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const PUBLICATION_DOMAIN = process.env.PUBLICATION_DOMAIN ?? '';
const AUTHOR_NAME        = process.env.AUTHOR_NAME        ?? 'the editorial team';

export const metadata: Metadata = {
  title:       `Editorial Policy · ${PUBLICATION_NAME}`,
  description: `How ${PUBLICATION_NAME} selects, generates, and reviews trending content — AI standards, brand safety, and correction policy.`,
};

const h2Style: React.CSSProperties = {
  fontFamily:   'var(--font-heading)',
  fontSize:     'clamp(18px, 3vw, 22px)',
  fontWeight:   700,
  color:        'var(--color-text-primary-light)',
  margin:       '0 0 var(--spacing-3)',
};

const h3Style: React.CSSProperties = {
  fontFamily:  'var(--font-body)',
  fontSize:    '15px',
  fontWeight:  700,
  color:       'var(--color-text-primary-light)',
  margin:      '0 0 var(--spacing-2)',
};

const pStyle: React.CSSProperties = {
  fontFamily: 'var(--font-body)',
  fontSize:   '15px',
  lineHeight: 1.75,
  color:      'var(--color-text-secondary-light)',
  margin:     '0 0 var(--spacing-4)',
};

const liStyle: React.CSSProperties = {
  fontFamily: 'var(--font-body)',
  fontSize:   '15px',
  lineHeight: 1.7,
  color:      'var(--color-text-secondary-light)',
  marginBottom: 'var(--spacing-2)',
};

const dividerStyle: React.CSSProperties = {
  border:    'none',
  borderTop: '1px solid rgba(0,0,0,.08)',
  margin:    'var(--spacing-10) 0',
};

const lastUpdated = 'February 2026';

export default function EditorialPolicyPage() {
  return (
    <div
      style={{
        maxWidth: 720,
        margin:   '0 auto',
        padding:  'var(--spacing-12) var(--spacing-4) var(--spacing-16)',
      }}
    >
      {/* Header */}
      <h1
        style={{
          fontFamily:  'var(--font-heading)',
          fontSize:    'clamp(26px, 5vw, 40px)',
          fontWeight:  800,
          color:       'var(--color-text-primary-light)',
          margin:      '0 0 var(--spacing-2)',
        }}
      >
        Editorial Policy
      </h1>
      <p
        style={{
          fontFamily: 'var(--font-body)',
          fontSize:   '13px',
          color:      'var(--color-text-muted-light)',
          margin:     '0 0 var(--spacing-10)',
        }}
      >
        Last updated: {lastUpdated} · Published by {PUBLICATION_NAME}
      </p>

      {/* ── 1. Topic Selection ───────────────────────────────────────────── */}
      <section aria-labelledby="topic-selection">
        <h2 id="topic-selection" style={h2Style}>1. Topic Selection</h2>
        <p style={pStyle}>
          {PUBLICATION_NAME} uses an automated pipeline to identify topics that are
          genuinely gaining momentum across multiple platforms simultaneously. A topic
          must satisfy all of the following criteria before it is considered for
          publication:
        </p>
        <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
          {[
            'Cross-platform presence — the topic must be trending on at least two independent platforms (e.g. X/Twitter, Reddit, Google Trends, TikTok) to filter single-platform spikes.',
            'Velocity threshold — the topic must show a measurable rate of growth over the preceding two-hour window.',
            'Publication gap — preference is given to topics not already covered by major outlets, so we add genuine value.',
            'Viral score ≥ 0.40 — the weighted model score (combining cross-platform, velocity, acceleration, sentiment, and time-of-day factors) must exceed 0.40 on a 0–1 scale.',
            'Brand safety check — the topic must pass automated content screening (see Brand Safety below).',
          ].map((item, i) => (
            <li key={i} style={liStyle}>{item}</li>
          ))}
        </ul>
        <p style={pStyle}>
          Topics scoring between 0.40 and 0.60 also pass through an LLM validation
          step where a language model assesses whether the momentum reflects genuine
          public interest rather than coordinated manipulation or bot activity.
        </p>
      </section>

      <hr style={dividerStyle} />

      {/* ── 2. AI Labeling Standards ─────────────────────────────────────── */}
      <section aria-labelledby="ai-labeling">
        <h2 id="ai-labeling" style={h2Style}>2. AI Labeling Standards</h2>
        <p style={pStyle}>
          {PUBLICATION_NAME} is committed to transparency about the role of artificial
          intelligence in our content creation process. We follow these standards:
        </p>

        <h3 style={h3Style}>What AI generates</h3>
        <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
          {[
            'Article summaries and full text (Claude Sonnet by Anthropic)',
            'Social media copy (Facebook, Instagram, X, YouTube)',
            'Narration scripts for video companions',
            'Thumbnail images (Flux 1.1 Pro)',
          ].map((item, i) => (
            <li key={i} style={liStyle}>{item}</li>
          ))}
        </ul>

        <h3 style={h3Style}>Disclosure labeling</h3>
        <p style={pStyle}>
          Every AI-generated article on {PUBLICATION_NAME} carries a visible
          &ldquo;AI-assisted&rdquo; label in the article header. We do not hide,
          minimise, or mislead readers about the AI origin of content.
        </p>

        <h3 style={h3Style}>Factual accuracy</h3>
        <p style={pStyle}>
          AI models can hallucinate facts. Our pipeline instructs the model to
          cite only verifiable information and to express appropriate uncertainty
          when details are unclear. {AUTHOR_NAME} spot-checks published articles
          daily. If you identify a factual error, please report it using our
          Correction Policy below.
        </p>
      </section>

      <hr style={dividerStyle} />

      {/* ── 3. Brand Safety ──────────────────────────────────────────────── */}
      <section aria-labelledby="brand-safety">
        <h2 id="brand-safety" style={h2Style}>3. Brand Safety Exclusions</h2>
        <p style={pStyle}>
          The following categories of content are categorically excluded from
          publication, regardless of viral score:
        </p>
        <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
          {[
            'Sexually explicit or NSFW material',
            'Content depicting or promoting graphic violence or self-harm',
            'Hate speech, discrimination, or content targeting protected characteristics',
            'Demonstrably false or debunked health misinformation (e.g. anti-vaccine disinformation)',
            'Content that doxes, harasses, or threatens private individuals',
            'Content promoting illegal activity',
            'Advertising or sponsored content disguised as editorial',
            'AI-generated content that is indistinguishable from real persons making statements they did not make (deepfake text)',
          ].map((item, i) => (
            <li key={i} style={liStyle}>{item}</li>
          ))}
        </ul>
        <p style={pStyle}>
          Our automated filter applies keyword, entity, and sentiment signals.
          Topics flagged by the filter are reviewed before any content is
          generated. Topics are not re-queued after rejection.
        </p>
      </section>

      <hr style={dividerStyle} />

      {/* ── 4. User Submission Process ───────────────────────────────────── */}
      <section aria-labelledby="submissions">
        <h2 id="submissions" style={h2Style}>4. User Submission Process</h2>
        <p style={pStyle}>
          Registered users may suggest trending topics via the{' '}
          <Link href="/submit" style={{ color: 'var(--color-link)' }}>Submit</Link>{' '}
          page. Submissions are limited to one per user per 7-day rolling window to
          maintain quality.
        </p>
        <p style={pStyle}>
          All submissions are reviewed by {AUTHOR_NAME} within 48 hours. Approved
          submissions enter the standard pipeline; they are not published
          automatically and must still pass viral-score and brand-safety checks.
          We do not guarantee that any submission will be published, and we do not
          provide individual feedback on rejected submissions.
        </p>
      </section>

      <hr style={dividerStyle} />

      {/* ── 5. Correction Policy ─────────────────────────────────────────── */}
      <section aria-labelledby="corrections">
        <h2 id="corrections" style={h2Style}>5. Correction Policy</h2>
        <p style={pStyle}>
          We take accuracy seriously. If you believe a published article contains
          a factual error, please contact us using one of the methods below. Include:
        </p>
        <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
          {[
            'The URL of the article',
            'The specific claim you believe to be incorrect',
            'Supporting evidence or a credible source for the correction',
          ].map((item, i) => (
            <li key={i} style={liStyle}>{item}</li>
          ))}
        </ul>
        <p style={pStyle}>
          We will investigate all verified correction requests within 24 hours
          and, where warranted, update the article with a visible correction notice
          at the top of the page noting the original error and the change made.
          We do not silently edit published articles.
        </p>
      </section>

      <hr style={dividerStyle} />

      {/* ── 6. Contact ───────────────────────────────────────────────────── */}
      <section aria-labelledby="ep-contact">
        <h2 id="ep-contact" style={h2Style}>6. Contact</h2>
        <p style={pStyle}>
          For editorial questions, correction requests, or press enquiries:
        </p>
        <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
          <li style={liStyle}>
            <strong>Contact form:</strong>{' '}
            <Link href="/contact" style={{ color: 'var(--color-link)' }}>
              {PUBLICATION_DOMAIN ? `${PUBLICATION_DOMAIN}/contact` : '/contact'}
            </Link>
          </li>
          {PUBLICATION_DOMAIN && (
            <li style={liStyle}>
              <strong>Email:</strong>{' '}
              <a href={`mailto:editorial@${PUBLICATION_DOMAIN}`} style={{ color: 'var(--color-link)' }}>
                editorial@{PUBLICATION_DOMAIN}
              </a>
            </li>
          )}
        </ul>
        <p style={{ ...pStyle, margin: 0 }}>
          We aim to respond to all editorial enquiries within two business days.
        </p>
      </section>
    </div>
  );
}
