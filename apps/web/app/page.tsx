/**
 * Home page — server component.
 *
 * Placeholder until the trending topics feed is wired up.
 * ISR inherited from root layout (300 s); override here if needed:
 *   export const revalidate = 60;
 */

import type { Metadata } from 'next';

const pubName = process.env.PUBLICATION_NAME ?? 'theNewslane';

export const metadata: Metadata = {
  title:       `Trending Now | ${pubName}`,
  description: `Today's most viral stories, AI-curated in real time.`,
};

export default function HomePage() {
  return (
    <div className="site-container" style={{ padding: 'var(--spacing-12) var(--spacing-4)' }}>
      <h1
        style={{
          fontFamily:  'var(--font-heading)',
          fontSize:    'clamp(28px, 5vw, 48px)',
          fontWeight:  700,
          color:       'var(--color-text-primary-light)',
          marginBottom: 'var(--spacing-4)',
        }}
      >
        Trending Now
      </h1>
      <p
        style={{
          fontSize:    16,
          lineHeight:  1.65,
          color:       'var(--color-text-secondary-light)',
          fontFamily:  'var(--font-body)',
          maxWidth:    640,
          marginBottom: 'var(--spacing-8)',
        }}
      >
        AI-curated viral stories updated every 4 hours. Sign up for real-time
        alerts on the topics that matter to you.
      </p>

      {/* Trending feed will be rendered here */}
      <div
        style={{
          padding:         'var(--spacing-12)',
          textAlign:       'center',
          backgroundColor: 'var(--color-card-light)',
          borderRadius:    'var(--radius-large)',
          border:          '2px dashed rgba(0,0,0,.1)',
          color:           'var(--color-text-muted-light)',
          fontSize:        14,
          fontFamily:      'var(--font-body)',
        }}
      >
        Topic feed coming soon
      </div>
    </div>
  );
}
