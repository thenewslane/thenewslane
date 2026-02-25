/**
 * Homepage — server component.
 *
 * Fetches topics for each section of the vibrant home feed:
 *   • Hero (top 5 topics — featured carousel)
 *   • Breaking News (next 10 — horizontal scroll)
 *   • Top Stories (next 6 — grid)
 *   • Quick Reads (next 12 — compact list)
 *   • Active categories for the category picker
 *
 * ISR: revalidate inherited from root layout (300 s).
 */

import type { Metadata } from 'next';
import { getServerClient } from '@platform/supabase';
import type { TrendingTopic, Category } from '@platform/types';
import { HomeFeed } from '@/components/HomeFeed';

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------
const pubName   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const pubDomain = process.env.PUBLICATION_DOMAIN ?? '';
const baseUrl   = pubDomain ? `https://${pubDomain}` : 'https://thenewslane.com';

const _desc = `Today's most viral stories, AI-curated in real time. Breaking news across technology, politics, sports, entertainment, and more.`;

export const metadata: Metadata = {
  title:       `Trending Now | ${pubName}`,
  description: _desc,
  alternates:  { canonical: baseUrl },
  openGraph: {
    title:       `Trending Now | ${pubName}`,
    description: _desc,
    url:         baseUrl,
    type:        'website',
    siteName:    pubName,
  },
  twitter: {
    card:        'summary_large_image',
    title:       `Trending Now | ${pubName}`,
    description: _desc,
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
        .eq('fact_check', 'yes')
        .order('published_at', { ascending: false })
        .limit(33),          // hero(5) + breaking(10) + topStories(6) + quickReads(12)
      supabase
        .from('categories')
        .select('*')
        .order('name', { ascending: true }),
    ]);

    const allTopics = (topicsResult.data ?? []) as TrendingTopic[];
    const allCats   = (categoriesResult.data ?? []) as Category[];

    // Only show categories that have at least one published topic
    const usedCatIds = new Set(allTopics.map(t => (t as any).category_id).filter(Boolean));
    const categories = allCats.filter(c => usedCatIds.has(c.id));

    return { topics: allTopics, categories };
  } catch {
    return { topics: [], categories: [] };
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default async function HomePage() {
  const { topics, categories } = await getInitialData();

  return <HomeFeed initialTopics={topics} initialCategories={categories} />;
}
