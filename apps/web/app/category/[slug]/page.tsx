/**
 * Category page — /category/[slug]
 *
 * Server component. Renders the same feed as the homepage but filtered by
 * the given category slug (e.g. /category/entertainment).
 * 404 if the category does not exist.
 *
 * ISR: revalidate inherited from layout (300 s).
 */

import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getServerClient } from '@platform/supabase';
import type { TrendingTopic, Category } from '@platform/types';
import { TopicFeed } from '@/components/TopicFeed';

const PAGE_SIZE = 12;

// Slugs used in Header/Footer — pre-render these at build if DB available
const KNOWN_CATEGORY_SLUGS = [
  'technology', 'politics', 'entertainment', 'sports', 'business-finance',
  'health-science', 'world-news', 'lifestyle', 'culture-arts', 'environment',
];

const pubName   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const pubDomain = process.env.PUBLICATION_DOMAIN ?? '';
const baseUrl   = pubDomain ? `https://${pubDomain}` : 'https://thenewslane.com';

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------
async function getCategoryBySlug(slug: string): Promise<Category | null> {
  const supabase = getServerClient();
  const { data, error } = await supabase
    .from('categories')
    .select('*')
    .eq('slug', slug)
    .single();
  if (error || !data) return null;
  return data as Category;
}

async function getCategoryPageData(slug: string): Promise<{
  category: Category;
  topics: TrendingTopic[];
  categories: Category[];
} | null> {
  const supabase = getServerClient();
  const category = await getCategoryBySlug(slug);
  if (!category) return null;

  const [topicsResult, categoriesResult, countResult] = await Promise.all([
    supabase
      .from('trending_topics')
      .select('*, category:categories(id, name, slug, color, description)')
      .eq('status', 'published')
      .eq('category_id', category.id)
      .order('published_at', { ascending: false })
      .limit(PAGE_SIZE),
    supabase
      .from('categories')
      .select('*')
      .order('name', { ascending: true }),
    supabase
      .from('trending_topics')
      .select('category_id')
      .eq('status', 'published')
      .not('category_id', 'is', null),
  ]);

  const allCategories = (categoriesResult.data ?? []) as Category[];
  const topicRows = (countResult.data ?? []) as { category_id: number }[];
  const categoryIdsWithTopics = new Set(
    topicRows.map((r) => r.category_id).filter((id): id is number => id != null),
  );
  const categories = allCategories.filter((c) => categoryIdsWithTopics.has(c.id));

  return {
    category,
    topics: (topicsResult.data ?? []) as TrendingTopic[],
    categories,
  };
}

// ---------------------------------------------------------------------------
// Static params (optional — pre-render known category slugs at build)
// ---------------------------------------------------------------------------
export const dynamicParams = true;

export async function generateStaticParams(): Promise<{ slug: string }[]> {
  try {
    const supabase = getServerClient();
    const { data } = await supabase
      .from('categories')
      .select('slug')
      .in('slug', KNOWN_CATEGORY_SLUGS);
    return ((data ?? []) as { slug: string }[]).map((row) => ({ slug: row.slug }));
  } catch {
    return KNOWN_CATEGORY_SLUGS.map((slug) => ({ slug }));
  }
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------
export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const category = await getCategoryBySlug(params.slug);
  if (!category) return { title: 'Not Found' };

  const title = `${category.name} | ${pubName}`;
  const description = `Trending ${category.name.toLowerCase()} stories — AI-curated viral news.`;
  const url = `${baseUrl}/category/${category.slug}`;

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      type: 'website',
      siteName: pubName,
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default async function CategoryPage({
  params,
}: {
  params: { slug: string };
}) {
  const data = await getCategoryPageData(params.slug);
  if (!data) notFound();

  const { category, topics, categories } = data;

  return (
    <div
      className="site-container"
      style={{ padding: 'var(--spacing-8) var(--spacing-4) var(--spacing-16)' }}
    >
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
          {category.name}
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
          Trending {category.name.toLowerCase()} stories — AI-curated viral news.
        </p>
      </header>

      <TopicFeed
        initialTopics={topics}
        initialCategories={categories}
        initialCategorySlug={category.slug}
      />
    </div>
  );
}
