'use client';

/**
 * TopicFeed
 *
 * Client component powering the homepage feed.
 *
 * Features:
 *  • Category filter tabs
 *  • Viral tier toggle (All / Tier 1 / Tier 2 / Tier 3)
 *  • Responsive 1 → 2 → 3 column grid
 *  • Infinite scroll via IntersectionObserver
 *  • Shimmer skeleton while loading
 *  • Supabase browser client for data fetching
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getBrowserClient } from '@platform/supabase';
import type { TrendingTopic, Category } from '@platform/types';
import { TopicCard } from '@platform/ui/web';
import { CategoryFilter } from './CategoryFilter';
import { TopicSkeleton } from './TopicSkeleton';

const PAGE_SIZE = 12;

const TIER_OPTIONS: { label: string; value: 1 | 2 | 3 | null }[] = [
  { label: 'All Tiers', value: null },
  { label: '🔥 Tier 1',  value: 1 },
  { label: '📈 Tier 2',  value: 2 },
  { label: '🌱 Tier 3',  value: 3 },
];

interface TopicFeedProps {
  initialTopics:     TrendingTopic[];
  initialCategories: Category[];
}

export function TopicFeed({ initialTopics, initialCategories }: TopicFeedProps) {
  const router = useRouter();

  const [topics,    setTopics]    = useState<TrendingTopic[]>(initialTopics);
  const [category,  setCategory]  = useState<string | null>(null);
  const [tier,      setTier]      = useState<1 | 2 | 3 | null>(null);
  const [page,      setPage]      = useState(1);
  const [loading,   setLoading]   = useState(false);
  const [hasMore,   setHasMore]   = useState(initialTopics.length === PAGE_SIZE);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // ── Fetch topics from Supabase ─────────────────────────────────────────────
  const fetchTopics = useCallback(async (
    pageNum:     number,
    categorySlug: string | null,
    viralTier:   1 | 2 | 3 | null,
    append:      boolean,
  ) => {
    setLoading(true);
    try {
      const supabase = getBrowserClient();
      let query = supabase
        .from('trending_topics')
        .select('*, category:categories(id, name, slug, color, description)')
        .eq('status', 'published')
        .order('published_at', { ascending: false })
        .range((pageNum - 1) * PAGE_SIZE, pageNum * PAGE_SIZE - 1);

      if (categorySlug) {
        // Join through categories table
        const { data: cat } = await supabase
          .from('categories')
          .select('id')
          .eq('slug', categorySlug)
          .single();
        const catRow = cat as { id: number } | null;
        if (catRow) query = query.eq('category_id', catRow.id);
      }

      if (viralTier !== null) {
        query = query.eq('viral_tier', viralTier);
      }

      const { data, error } = await query;
      if (error) throw error;

      const rows = (data ?? []) as TrendingTopic[];
      setTopics(prev => append ? [...prev, ...rows] : rows);
      setHasMore(rows.length === PAGE_SIZE);
    } catch (err) {
      console.error('[TopicFeed] fetch error', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Re-fetch when filters change ───────────────────────────────────────────
  useEffect(() => {
    setPage(1);
    fetchTopics(1, category, tier, false);
  }, [category, tier, fetchTopics]);

  // ── Infinite scroll sentinel ───────────────────────────────────────────────
  useEffect(() => {
    if (!sentinelRef.current) return;
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0]?.isIntersecting && hasMore && !loading) {
          const next = page + 1;
          setPage(next);
          fetchTopics(next, category, tier, true);
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasMore, loading, page, category, tier, fetchTopics]);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div>
      {/* ── Filters ── */}
      <div
        style={{
          display:       'flex',
          flexDirection: 'column',
          gap:           'var(--spacing-3)',
          marginBottom:  'var(--spacing-6)',
        }}
      >
        <CategoryFilter
          categories={initialCategories}
          activeCategory={category}
          onSelect={slug => { setCategory(slug); }}
        />

        {/* Tier filter */}
        <div
          style={{
            display:  'flex',
            gap:      'var(--spacing-2)',
            flexWrap: 'wrap',
          }}
        >
          {TIER_OPTIONS.map(opt => {
            const isActive = tier === opt.value;
            return (
              <button
                key={String(opt.value)}
                onClick={() => setTier(opt.value)}
                aria-pressed={isActive}
                style={{
                  padding:         'var(--spacing-1) var(--spacing-3)',
                  borderRadius:    '999px',
                  border:          isActive
                    ? '1.5px solid var(--color-secondary)'
                    : '1.5px solid rgba(0,0,0,.1)',
                  backgroundColor: isActive ? 'var(--color-secondary)' : 'transparent',
                  color:           isActive ? '#fff' : 'var(--color-text-secondary-light)',
                  fontSize:        '12px',
                  fontWeight:      isActive ? 700 : 500,
                  fontFamily:      'var(--font-body)',
                  cursor:          'pointer',
                  whiteSpace:      'nowrap',
                  transition:      'all 0.15s',
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Grid ── */}
      <div
        style={{
          display:             'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))',
          gap:                 'var(--spacing-4)',
        }}
      >
        {topics.map(topic => (
          <TopicCard
            key={topic.id}
            topic={topic}
            onPress={t => router.push(`/trending/${t.slug}`)}
          />
        ))}

        {/* Skeleton cards while loading next page */}
        {loading && Array.from({ length: PAGE_SIZE }).map((_, i) => (
          <TopicSkeleton key={`skeleton-${i}`} />
        ))}
      </div>

      {/* ── Empty state ── */}
      {!loading && topics.length === 0 && (
        <div
          style={{
            textAlign:       'center',
            padding:         'var(--spacing-16) var(--spacing-4)',
            color:           'var(--color-text-muted-light)',
            fontFamily:      'var(--font-body)',
            fontSize:        '15px',
          }}
        >
          No trending topics found for this filter.
        </div>
      )}

      {/* ── Infinite scroll sentinel ── */}
      <div ref={sentinelRef} style={{ height: 1 }} aria-hidden />

      {/* ── End of feed message ── */}
      {!hasMore && topics.length > 0 && !loading && (
        <p
          style={{
            textAlign:   'center',
            marginTop:   'var(--spacing-8)',
            fontSize:    '13px',
            fontFamily:  'var(--font-body)',
            color:       'var(--color-text-muted-light)',
          }}
        >
          You&apos;ve reached the end of the feed.
        </p>
      )}
    </div>
  );
}
