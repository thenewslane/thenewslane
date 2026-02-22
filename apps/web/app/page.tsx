/**
 * Homepage — server component.
 *
 * Server-fetches:
 *   • All active categories (for CategoryFilter)
 *   • First page of published trending topics (initial hydration)
 *
 * Then hands off to <TopicFeed> (client) for filtering + infinite scroll.
 *
 * ISR: revalidate inherited from root layout (300 s).
 */

import type { Metadata } from 'next';
import { getServerClient } from '@platform/supabase';
import type { TrendingTopic, Category } from '@platform/types';
import { TopicFeed } from '@/components/TopicFeed';

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------
const pubName = process.env.PUBLICATION_NAME ?? 'theNewslane';

export const metadata: Metadata = {
  title:       `Trending Now | ${pubName}`,
  description: `Today's most viral stories, AI-curated in real time. Breaking news across technology, politics, sports, entertainment, and more.`,
  openGraph: {
    title:       `Trending Now | ${pubName}`,
    description: `Today's most viral stories, AI-curated in real time.`,
    type:        'website',
  },
};

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------
async function getInitialData(): Promise<{
  topics:     TrendingTopic[];
  categories: Category[];
}> {
  try {
    const supabase = getServerClient();

    const [topicsResult, categoriesResult] = await Promise.all([
      supabase
        .from('trending_topics')
        .select('*, category:categories(id, name, slug, color, description)')
        .eq('status', 'published')
        .order('published_at', { ascending: false })
        .limit(12),
      supabase
        .from('categories')
        .select('*')
        .order('name', { ascending: true }),
    ]);

    return {
      topics:     (topicsResult.data ?? []) as TrendingTopic[],
      categories: (categoriesResult.data ?? []) as Category[],
    };
  } catch {
    // Supabase env vars not available at build time.
    return { topics: [], categories: [] };
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default async function HomePage() {
  const { topics, categories } = await getInitialData();

  return (
    <div
      className="site-container"
      style={{ padding: 'var(--spacing-8) var(--spacing-4) var(--spacing-16)' }}
    >
      {/* ── Page header ── */}
      <header style={{ marginBottom: 'var(--spacing-8)' }}>
        <h1
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     'clamp(28px, 5vw, 48px)',
            fontWeight:   700,
            color:        'var(--color-text-primary-light)',
            marginBottom: 'var(--spacing-2)',
            lineHeight:   1.15,
          }}
        >
          Trending Now
        </h1>
        <p
          style={{
            fontSize:   '16px',
            lineHeight: 1.65,
            color:      'var(--color-text-secondary-light)',
            fontFamily: 'var(--font-body)',
            maxWidth:   640,
            margin:     0,
          }}
        >
          AI-curated viral stories updated every 5 minutes — across technology,
          politics, sports, entertainment, and more.
        </p>
      </header>

      {/* ── Feed (client) ── */}
      <TopicFeed
        initialTopics={topics}
        initialCategories={categories}
      />
    </div>
  );
}
