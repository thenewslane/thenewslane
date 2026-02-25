'use client';

/**
 * HomeFeed — vibrant home page layout inspired by ABP Live.
 *
 * Sections (in order):
 *   1. Hero Carousel        — top 5 topics, auto-rotates every 5 s
 *   2. Breaking News Bar    — horizontal scroll, topics 5–14
 *   3. Category Chip Picker — filter by category
 *   4. Top Stories Grid     — 1 hero card + 2-column grid (5 topics)
 *   5. Quick Reads          — compact list (remaining topics)
 *   6. Load More button     — fetches next page from Supabase
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getBrowserClient } from '@platform/supabase';
import type { TrendingTopic, Category } from '@platform/types';

const BRAND_RED    = '#AD2D37';
const BRAND_NAVY   = '#1E3A5F';
const BRAND_ORANGE = '#E05A1E';

// ── helpers ────────────────────────────────────────────────────────────────

function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600)  return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

function catName(topic: TrendingTopic): string {
  return (topic as any).category?.name ?? '';
}

function thumb(topic: TrendingTopic): string | null {
  return (topic as any).thumbnail_url ?? null;
}

// ── Category chip bar ─────────────────────────────────────────────────────

function CategoryChips({
  categories,
  active,
  onSelect,
}: {
  categories: Category[];
  active: string | null;
  onSelect: (slug: string | null) => void;
}) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        overflowX: 'auto',
        paddingBottom: 4,
        scrollbarWidth: 'none',
      }}
    >
      {[{ label: '/ All', slug: null }, ...categories.map(c => ({ label: `/ ${c.name}`, slug: c.slug }))].map(
        ({ label, slug }) => {
          const on = active === slug;
          return (
            <button
              key={slug ?? '__all__'}
              onClick={() => onSelect(slug)}
              style={{
                flexShrink: 0,
                padding: '6px 16px',
                borderRadius: 999,
                border: `1.5px solid ${on ? BRAND_RED : 'rgba(173,45,55,0.25)'}`,
                background: on ? BRAND_RED : 'rgba(173,45,55,0.06)',
                color: on ? '#fff' : BRAND_RED,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                letterSpacing: '0.02em',
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
              }}
            >
              {label}
            </button>
          );
        },
      )}
    </div>
  );
}

// ── Hero Carousel ─────────────────────────────────────────────────────────

function HeroCarousel({ topics }: { topics: TrendingTopic[] }) {
  const router = useRouter();
  const [idx, setIdx] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const restart = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(() => setIdx(i => (i + 1) % topics.length), 5000);
  }, [topics.length]);

  useEffect(() => {
    restart();
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [restart]);

  if (!topics.length) return null;
  const topic = topics[idx];

  return (
    <div
      style={{
        position: 'relative',
        borderRadius: 16,
        overflow: 'hidden',
        cursor: 'pointer',
        height: 'clamp(240px, 40vw, 480px)',
        background: BRAND_NAVY,
        marginBottom: 24,
      }}
      onClick={() => router.push(`/trending/${topic.slug}`)}
    >
      {/* Background image */}
      {thumb(topic) ? (
        <img
          src={thumb(topic)!}
          alt=""
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
        />
      ) : (
        <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(135deg, ${BRAND_NAVY} 0%, #0a1628 100%)` }} />
      )}

      {/* Gradient overlay */}
      <div
        style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(to top, rgba(0,0,0,.92) 0%, rgba(0,0,0,.55) 50%, rgba(0,0,0,.1) 100%)',
        }}
      />

      {/* LIVE badge */}
      <div style={{ position: 'absolute', top: 16, left: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ background: BRAND_RED, color: '#fff', fontSize: 10, fontWeight: 800, padding: '3px 8px', borderRadius: 4, letterSpacing: 1 }}>LIVE</span>
        {catName(topic) && (
          <span style={{ background: 'rgba(255,255,255,.15)', backdropFilter: 'blur(8px)', color: '#fff', fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 20, border: '1px solid rgba(255,255,255,.2)' }}>
            {catName(topic)}
          </span>
        )}
      </div>

      {/* Content */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '20px 20px 16px' }}>
        <h2 style={{ fontSize: 'clamp(18px, 3vw, 28px)', fontWeight: 800, color: '#fff', lineHeight: 1.25, marginBottom: 8, fontFamily: 'var(--font-heading)' }}>
          {topic.title}
        </h2>
        {(topic as any).summary && (
          <p style={{ fontSize: 13, color: 'rgba(255,255,255,.75)', lineHeight: 1.5, margin: '0 0 12px', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {(topic as any).summary}
          </p>
        )}

        {/* Pagination dots */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {topics.map((_, i) => (
            <button
              key={i}
              onClick={e => { e.stopPropagation(); setIdx(i); restart(); }}
              style={{
                width: i === idx ? 20 : 6, height: 6, borderRadius: 3,
                background: i === idx ? BRAND_RED : 'rgba(255,255,255,.4)',
                border: 'none', cursor: 'pointer', padding: 0,
                transition: 'all 0.3s',
              }}
            />
          ))}
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,.5)', marginLeft: 8 }}>{timeAgo(topic.published_at)}</span>
        </div>
      </div>
    </div>
  );
}

// ── Breaking News Bar ─────────────────────────────────────────────────────

function BreakingNewsBar({ topics }: { topics: TrendingTopic[] }) {
  const router = useRouter();
  if (!topics.length) return null;

  return (
    <div style={{ marginBottom: 32 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <div style={{ width: 4, height: 20, background: BRAND_RED, borderRadius: 2, flexShrink: 0 }} />
        <h2 style={{ fontSize: 15, fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--color-text-primary-light)', fontFamily: 'var(--font-heading)', margin: 0 }}>
          Breaking News
        </h2>
        <div style={{ flex: 1, height: 1, background: 'rgba(173,45,55,0.15)' }} />
      </div>

      {/* Horizontal scroll */}
      <div style={{ display: 'flex', gap: 14, overflowX: 'auto', paddingBottom: 8, scrollbarWidth: 'none' }}>
        {topics.map(topic => (
          <div
            key={topic.id}
            onClick={() => router.push(`/trending/${topic.slug}`)}
            style={{
              flexShrink: 0, width: 180, cursor: 'pointer',
              borderRadius: 10, overflow: 'hidden',
              background: 'var(--color-surface-light, #f7f7f9)',
              border: '1px solid rgba(0,0,0,.07)',
              transition: 'transform 0.15s, box-shadow 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 6px 20px rgba(0,0,0,.12)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = ''; (e.currentTarget as HTMLElement).style.boxShadow = ''; }}
          >
            {/* Thumbnail */}
            <div style={{ height: 96, background: BRAND_NAVY, position: 'relative', overflow: 'hidden' }}>
              {thumb(topic)
                ? <img src={thumb(topic)!} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                : <div style={{ width: '100%', height: '100%', background: `linear-gradient(135deg, ${BRAND_NAVY}, #0a1628)` }} />
              }
              {/* Red accent bar */}
              <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: BRAND_RED }} />
            </div>
            {/* Text */}
            <div style={{ padding: '10px 10px 12px' }}>
              {catName(topic) && (
                <div style={{ fontSize: 10, fontWeight: 700, color: BRAND_RED, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
                  {catName(topic)}
                </div>
              )}
              <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.4, color: 'var(--color-text-primary-light)', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {topic.title}
              </div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted-light, #888)', marginTop: 6 }}>{timeAgo(topic.published_at)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Top Stories Grid ──────────────────────────────────────────────────────

function TopStoriesGrid({ topics }: { topics: TrendingTopic[] }) {
  const router = useRouter();
  if (!topics.length) return null;

  const [hero, ...rest] = topics;

  return (
    <div style={{ marginBottom: 32 }}>
      {/* Section header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{ width: 4, height: 20, background: BRAND_ORANGE, borderRadius: 2 }} />
        <h2 style={{ fontSize: 15, fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--color-text-primary-light)', fontFamily: 'var(--font-heading)', margin: 0 }}>
          Top Stories
        </h2>
        <div style={{ flex: 1, height: 1, background: 'rgba(224,90,30,0.15)' }} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {/* Large hero card */}
        <div
          onClick={() => router.push(`/trending/${hero.slug}`)}
          style={{
            gridRow: '1 / span 2', borderRadius: 12, overflow: 'hidden', cursor: 'pointer',
            background: BRAND_NAVY, position: 'relative', minHeight: 280,
            border: '1px solid rgba(0,0,0,.07)',
            transition: 'transform 0.15s, box-shadow 0.15s',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 24px rgba(0,0,0,.15)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = ''; (e.currentTarget as HTMLElement).style.boxShadow = ''; }}
        >
          {thumb(hero)
            ? <img src={thumb(hero)!} alt="" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
            : <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(135deg, ${BRAND_NAVY} 0%, #0a1628 100%)` }} />
          }
          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(0,0,0,.88) 0%, rgba(0,0,0,.2) 60%)' }} />
          <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16 }}>
            {catName(hero) && (
              <div style={{ fontSize: 10, fontWeight: 700, color: BRAND_ORANGE, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>
                {catName(hero)}
              </div>
            )}
            <h3 style={{ fontSize: 'clamp(15px, 2.5vw, 20px)', fontWeight: 800, color: '#fff', lineHeight: 1.3, margin: '0 0 6px', fontFamily: 'var(--font-heading)' }}>
              {hero.title}
            </h3>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.55)' }}>{timeAgo(hero.published_at)}</div>
          </div>
        </div>

        {/* Small grid cards */}
        {rest.slice(0, 4).map(topic => (
          <div
            key={topic.id}
            onClick={() => router.push(`/trending/${topic.slug}`)}
            style={{
              borderRadius: 10, overflow: 'hidden', cursor: 'pointer',
              background: 'var(--color-surface-light, #f7f7f9)',
              border: '1px solid rgba(0,0,0,.07)',
              display: 'flex', gap: 10, alignItems: 'stretch',
              transition: 'box-shadow 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 16px rgba(0,0,0,.1)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = ''; }}
          >
            {/* Thumb */}
            <div style={{ width: 80, flexShrink: 0, background: BRAND_NAVY, position: 'relative', overflow: 'hidden' }}>
              {thumb(topic)
                ? <img src={thumb(topic)!} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                : <div style={{ width: '100%', height: '100%', background: `linear-gradient(135deg, ${BRAND_NAVY}, #0a1628)` }} />
              }
            </div>
            {/* Text */}
            <div style={{ flex: 1, padding: '10px 12px 10px 0' }}>
              {catName(topic) && (
                <div style={{ fontSize: 9, fontWeight: 700, color: BRAND_RED, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
                  {catName(topic)}
                </div>
              )}
              <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.4, color: 'var(--color-text-primary-light)', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {topic.title}
              </div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted-light, #888)', marginTop: 4 }}>{timeAgo(topic.published_at)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Quick Reads ────────────────────────────────────────────────────────────

function QuickReads({ topics }: { topics: TrendingTopic[] }) {
  const router = useRouter();
  if (!topics.length) return null;

  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <div style={{ width: 4, height: 20, background: BRAND_NAVY, borderRadius: 2 }} />
        <h2 style={{ fontSize: 15, fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--color-text-primary-light)', fontFamily: 'var(--font-heading)', margin: 0 }}>
          Quick Reads
        </h2>
        <div style={{ flex: 1, height: 1, background: 'rgba(30,58,95,0.15)' }} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))', gap: 12 }}>
        {topics.map(topic => (
          <div
            key={topic.id}
            onClick={() => router.push(`/trending/${topic.slug}`)}
            style={{
              display: 'flex', gap: 12, alignItems: 'center',
              padding: '10px 12px', borderRadius: 10, cursor: 'pointer',
              background: 'var(--color-surface-light, #f7f7f9)',
              border: '1px solid rgba(0,0,0,.07)',
              transition: 'background 0.15s, box-shadow 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#fff'; (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 14px rgba(0,0,0,.09)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = ''; (e.currentTarget as HTMLElement).style.boxShadow = ''; }}
          >
            {/* Thumbnail */}
            <div style={{ width: 64, height: 64, flexShrink: 0, borderRadius: 8, overflow: 'hidden', background: BRAND_NAVY, position: 'relative' }}>
              {thumb(topic)
                ? <img src={thumb(topic)!} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                : <div style={{ width: '100%', height: '100%', background: `linear-gradient(135deg, ${BRAND_NAVY}, #0a1628)` }} />
              }
            </div>
            {/* Text */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                {catName(topic) && (
                  <span style={{ fontSize: 9, fontWeight: 700, color: '#fff', background: BRAND_RED, padding: '2px 7px', borderRadius: 4, textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0 }}>
                    {catName(topic)}
                  </span>
                )}
                <span style={{ fontSize: 10, color: 'var(--color-text-muted-light, #999)', whiteSpace: 'nowrap' }}>{timeAgo(topic.published_at)}</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.4, color: 'var(--color-text-primary-light)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {topic.title}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main HomeFeed ──────────────────────────────────────────────────────────

const PAGE_SIZE = 12;

export function HomeFeed({
  initialTopics,
  initialCategories,
}: {
  initialTopics:     TrendingTopic[];
  initialCategories: Category[];
}) {
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [extraTopics,    setExtraTopics]    = useState<TrendingTopic[]>([]);
  const [page,           setPage]           = useState(1);
  const [hasMore,        setHasMore]        = useState(false);
  const [loading,        setLoading]        = useState(false);

  // Split initial topics into sections (only when no category filter)
  const hero        = initialTopics.slice(0, 5);
  const breaking    = initialTopics.slice(5, 15);
  const topStories  = initialTopics.slice(15, 21);
  const quickInit   = initialTopics.slice(21);

  // ── Category-filtered fetch ─────────────────────────────────────────────
  const fetchFiltered = useCallback(async (slug: string | null, pageNum: number, append: boolean) => {
    setLoading(true);
    try {
      const supabase = getBrowserClient();
      let query = supabase
        .from('trending_topics')
        .select('*, category:categories(id, name, slug, color, description)')
        .eq('status', 'published')
        .eq('fact_check', 'yes')
        .order('published_at', { ascending: false })
        .range((pageNum - 1) * PAGE_SIZE, pageNum * PAGE_SIZE - 1);

      if (slug) {
        const { data: cat } = await supabase.from('categories').select('id').eq('slug', slug).single();
        if (cat) query = query.eq('category_id', (cat as any).id);
      }

      const { data } = await query;
      const rows = (data ?? []) as TrendingTopic[];
      setExtraTopics(prev => append ? [...prev, ...rows] : rows);
      setHasMore(rows.length === PAGE_SIZE);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleCategoryChange = (slug: string | null) => {
    setActiveCategory(slug);
    setPage(1);
    if (slug === null) {
      setExtraTopics([]);
      setHasMore(false);
    } else {
      fetchFiltered(slug, 1, false);
    }
  };

  const loadMore = () => {
    const next = page + 1;
    setPage(next);
    fetchFiltered(activeCategory, next, true);
  };

  // ── Render ──────────────────────────────────────────────────────────────

  // Category-filtered view: show results in Top Stories + Quick Reads layout
  if (activeCategory !== null) {
    const filtered = extraTopics;
    const ftHero   = filtered.slice(0, 5);
    const ftQuick  = filtered.slice(5);

    return (
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '16px 16px 48px' }}>
        {/* Category chips */}
        <div style={{ marginBottom: 24 }}>
          <CategoryChips categories={initialCategories} active={activeCategory} onSelect={handleCategoryChange} />
        </div>

        {loading && ftHero.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px', color: 'var(--color-text-muted-light, #888)', fontSize: 14 }}>
            Loading…
          </div>
        ) : filtered.length === 0 && !loading ? (
          <div style={{ textAlign: 'center', padding: '48px', color: 'var(--color-text-muted-light, #888)', fontSize: 14 }}>
            No topics found in this category yet.
          </div>
        ) : (
          <>
            <TopStoriesGrid topics={ftHero} />
            <QuickReads topics={ftQuick} />
            {hasMore && (
              <div style={{ textAlign: 'center', marginTop: 8 }}>
                <button
                  onClick={loadMore}
                  disabled={loading}
                  style={{ padding: '10px 28px', borderRadius: 8, background: BRAND_RED, color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', cursor: 'pointer', opacity: loading ? 0.6 : 1 }}
                >
                  {loading ? 'Loading…' : 'Load More'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  // Default view: all sections
  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '16px 16px 48px' }}>

      {/* Hero Carousel */}
      <HeroCarousel topics={hero} />

      {/* Breaking News */}
      <BreakingNewsBar topics={breaking} />

      {/* Category Chip Picker */}
      <div style={{ marginBottom: 28 }}>
        <CategoryChips categories={initialCategories} active={null} onSelect={handleCategoryChange} />
      </div>

      {/* Top Stories */}
      <TopStoriesGrid topics={topStories} />

      {/* Quick Reads */}
      <QuickReads topics={quickInit} />

      {/* Load More */}
      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <button
          onClick={() => {
            const next = page + 1;
            setPage(next);
            fetchFiltered(null, next, true);
          }}
          disabled={loading}
          style={{ padding: '10px 28px', borderRadius: 8, background: BRAND_RED, color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', cursor: 'pointer', opacity: loading ? 0.6 : 1 }}
        >
          {loading ? 'Loading…' : 'More Stories'}
        </button>
      </div>

      {/* Extra topics loaded by Load More */}
      {extraTopics.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <QuickReads topics={extraTopics} />
        </div>
      )}
    </div>
  );
}
