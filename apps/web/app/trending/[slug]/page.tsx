/**
 * Article page — /trending/[slug]
 *
 * Server component. Renders a full trending-topic article with:
 *   • Full-width VideoPlayer (or thumbnail hero)
 *   • h1 title, AuthorByline
 *   • Article body paragraphs
 *   • In-content AdSlot (consent-aware, via ArticleAdSlot)
 *   • FAQ accordion (from schema_blocks)
 *   • SourceAttribution
 *   • Related Topics grid
 *   • Full SEO metadata: OG tags, Twitter Card
 *   • NewsArticle + VideoObject JSON-LD structured data
 *
 * ISR: revalidate = 300 (5 min). On-demand revalidation via revalidatePath()
 * from the Inngest pipeline.
 *
 * generateStaticParams: pre-renders the 30 most-recently published articles
 * at build time; all other slugs are server-rendered on first request.
 */

import React from 'react';
import type { Metadata } from 'next';
import { notFound }       from 'next/navigation';
import { getServerClient } from '@platform/supabase';
import type { TrendingTopic } from '@platform/types';
import { VideoPlayer, AuthorByline, SourceAttribution } from '@platform/ui/web';
import { FaqAccordion }       from '@/components/FaqAccordion';
import { ArticleAdSlot }      from '@/components/ArticleAdSlot';
import { NavigableTopicCard } from '@/components/NavigableTopicCard';

// ---------------------------------------------------------------------------
// Route segment config
// ---------------------------------------------------------------------------
export const revalidate = 300;
export const dynamicParams = true; // server-render unknown slugs on demand

// ---------------------------------------------------------------------------
// Static params (pre-renders 30 most-recent articles at build time)
// ---------------------------------------------------------------------------
export async function generateStaticParams(): Promise<{ slug: string }[]> {
  try {
    const supabase = getServerClient();
    const { data } = await supabase
      .from('trending_topics')
      .select('slug')
      .eq('status', 'published')
      .order('published_at', { ascending: false })
      .limit(30);
    return ((data ?? []) as { slug: string }[]).map(row => ({ slug: row.slug }));
  } catch {
    // Supabase env vars not available at build time — all pages rendered on demand.
    return [];
  }
}

// ---------------------------------------------------------------------------
// Data helpers
// ---------------------------------------------------------------------------
async function getTopic(slug: string): Promise<TrendingTopic | null> {
  const supabase = getServerClient();
  const { data, error } = await supabase
    .from('trending_topics')
    .select('*, category:categories(id, name, slug, color, description)')
    .eq('slug', slug)
    .eq('status', 'published')
    .single();
  if (error || !data) return null;
  return data as TrendingTopic;
}

async function getRelatedTopics(topic: TrendingTopic): Promise<TrendingTopic[]> {
  const supabase = getServerClient();
  let query = supabase
    .from('trending_topics')
    .select('*, category:categories(id, name, slug, color, description)')
    .eq('status', 'published')
    .neq('id', topic.id)
    .order('published_at', { ascending: false })
    .limit(3);

  if (topic.category_id) {
    query = query.eq('category_id', topic.category_id);
  }

  const { data } = await query;
  return (data ?? []) as TrendingTopic[];
}

// ---------------------------------------------------------------------------
// Extract FAQ items from schema_blocks
// ---------------------------------------------------------------------------
interface FaqSchemaBlock {
  '@type':          string;
  mainEntity?:      { '@type': string; name: string; acceptedAnswer: { '@type': string; text: string } }[];
}

function extractFaqItems(schemaBlocks: Record<string, unknown>[] | null) {
  if (!schemaBlocks) return [];
  const items: { question: string; answer: string }[] = [];
  for (const block of schemaBlocks) {
    const typed = block as unknown as FaqSchemaBlock;
    if (typed['@type'] === 'FAQPage' && Array.isArray(typed.mainEntity)) {
      for (const entry of typed.mainEntity) {
        if (entry['@type'] === 'Question' && entry.name && entry.acceptedAnswer?.text) {
          items.push({ question: entry.name, answer: entry.acceptedAnswer.text });
        }
      }
    }
  }
  return items;
}

// ---------------------------------------------------------------------------
// Extract VideoObject JSON-LD from schema_blocks
// ---------------------------------------------------------------------------
function extractVideoSchema(schemaBlocks: Record<string, unknown>[] | null): Record<string, unknown> | null {
  if (!schemaBlocks) return null;
  return schemaBlocks.find(b => (b as { '@type': string })['@type'] === 'VideoObject') ?? null;
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------
const pubName   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const pubDomain = process.env.PUBLICATION_DOMAIN ?? '';
const baseUrl   = pubDomain ? `https://${pubDomain}` : 'http://localhost:3000';
const authorName = process.env.AUTHOR_NAME ?? 'theNewslane Editorial';

export async function generateMetadata(
  { params }: { params: { slug: string } },
): Promise<Metadata> {
  const topic = await getTopic(params.slug);
  if (!topic) return { title: 'Not Found' };

  const url        = `${baseUrl}/trending/${topic.slug}`;
  const imageUrl   = topic.thumbnail_url ?? undefined;
  const description = topic.summary ?? `${pubName} — AI-curated trending news.`;
  const publishedAt = topic.published_at ?? topic.created_at;

  return {
    title:       topic.title,
    description,
    alternates:  { canonical: url },
    openGraph: {
      title:           topic.title,
      description,
      url,
      type:            'article',
      publishedTime:   publishedAt,
      modifiedTime:    topic.updated_at,
      authors:         [authorName],
      images:          imageUrl ? [{ url: imageUrl, alt: topic.title }] : [],
      tags:            topic.iab_tags ?? [],
      siteName:        pubName,
    },
    twitter: {
      card:        'summary_large_image',
      title:       topic.title,
      description,
      images:      imageUrl ? [imageUrl] : [],
    },
  };
}

// ---------------------------------------------------------------------------
// JSON-LD component
// ---------------------------------------------------------------------------
function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default async function ArticlePage({
  params,
}: {
  params: { slug: string };
}) {
  const topic = await getTopic(params.slug);
  if (!topic) notFound();

  const [related, faqItems] = await Promise.all([
    getRelatedTopics(topic),
    Promise.resolve(extractFaqItems(topic.schema_blocks)),
  ]);

  const publishedAt  = topic.published_at ?? topic.created_at;
  const articleUrl   = `${baseUrl}/trending/${topic.slug}`;
  const videoSchema  = extractVideoSchema(topic.schema_blocks);

  // Body paragraphs (split on double newline, fallback to full article)
  const paragraphs = topic.article
    ? topic.article.split(/\n{2,}/).map(p => p.trim()).filter(Boolean)
    : [];

  // ── JSON-LD: NewsArticle ────────────────────────────────────────────────
  const newsArticleSchema: Record<string, unknown> = {
    '@context':        'https://schema.org',
    '@type':           'NewsArticle',
    headline:          topic.title,
    description:       topic.summary ?? '',
    url:               articleUrl,
    datePublished:     publishedAt,
    dateModified:      topic.updated_at,
    author: [{
      '@type': 'Organization',
      name:    pubName,
      url:     baseUrl,
    }],
    publisher: {
      '@type': 'Organization',
      name:    pubName,
      url:     baseUrl,
      ...(topic.thumbnail_url
        ? { logo: { '@type': 'ImageObject', url: topic.thumbnail_url } }
        : {}),
    },
    ...(topic.thumbnail_url
      ? { image: [topic.thumbnail_url] }
      : {}),
    ...(topic.iab_tags?.length
      ? { keywords: topic.iab_tags.join(', ') }
      : {}),
  };

  return (
    <>
      {/* ── Structured data ── */}
      <JsonLd data={newsArticleSchema} />
      {videoSchema && <JsonLd data={videoSchema} />}

      <article
        style={{
          maxWidth:  800,
          margin:    '0 auto',
          padding:   'var(--spacing-4) var(--spacing-4) var(--spacing-16)',
        }}
      >
        {/* ── Category breadcrumb ── */}
        {topic.category && (
          <p
            style={{
              margin:      '0 0 var(--spacing-3)',
              fontSize:    '13px',
              fontFamily:  'var(--font-body)',
              fontWeight:  600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color:       `var(--color-category-${topic.category.slug})`,
            }}
          >
            {topic.category.name}
          </p>
        )}

        {/* ── Title ── */}
        <h1
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     'clamp(24px, 5vw, 40px)',
            fontWeight:   700,
            lineHeight:   1.2,
            color:        'var(--color-text-primary-light)',
            margin:       '0 0 var(--spacing-4)',
          }}
        >
          {topic.title}
        </h1>

        {/* ── Byline ── */}
        <div style={{ marginBottom: 'var(--spacing-6)' }}>
          <AuthorByline
            authorName={authorName}
            publishedAt={publishedAt}
          />
        </div>

        {/* ── Video / hero image ── */}
        {(topic.video_type || topic.thumbnail_url) && (
          <div style={{ marginBottom: 'var(--spacing-8)', borderRadius: 'var(--radius-large)', overflow: 'hidden' }}>
            <VideoPlayer
              videoType={topic.video_type}
              videoId={topic.video_url ?? undefined}
              videoUrl={topic.video_type === 'kling_generated' ? (topic.video_url ?? undefined) : undefined}
              thumbnailUrl={topic.thumbnail_url ?? undefined}
              title={topic.title}
            />
          </div>
        )}

        {/* ── Summary lead ── */}
        {topic.summary && (
          <p
            style={{
              fontFamily:  'var(--font-body)',
              fontSize:    '18px',
              lineHeight:  1.7,
              color:       'var(--color-text-secondary-light)',
              fontWeight:  400,
              margin:      '0 0 var(--spacing-6)',
              paddingLeft: 'var(--spacing-4)',
              borderLeft:  '3px solid var(--color-primary)',
            }}
          >
            {topic.summary}
          </p>
        )}

        {/* ── Article body ── */}
        {paragraphs.length > 0 && (
          <div style={{ marginBottom: 'var(--spacing-6)' }}>
            {paragraphs.map((para, idx) => (
              <React.Fragment key={idx}>
                {/* Insert an ad after the 3rd paragraph */}
                {idx === 3 && (
                  <ArticleAdSlot
                    unitPath="/theNewslane/article-mid"
                    sizes={[[728, 90], [320, 50]]}
                    id="ad-article-mid"
                  />
                )}
                <p
                  style={{
                    fontFamily:   'var(--font-body)',
                    fontSize:     '16px',
                    lineHeight:   1.8,
                    color:        'var(--color-text-primary-light)',
                    margin:       '0 0 var(--spacing-4)',
                  }}
                >
                  {para}
                </p>
              </React.Fragment>
            ))}
          </div>
        )}

        {/* ── Ad slot (if article is short, still show the ad) ── */}
        {paragraphs.length <= 3 && (
          <ArticleAdSlot
            unitPath="/theNewslane/article-mid"
            sizes={[[728, 90], [320, 50]]}
            id="ad-article-mid"
          />
        )}

        {/* ── FAQ accordion ── */}
        <FaqAccordion items={faqItems} />

        {/* ── Source attribution ── */}
        <div
          style={{
            marginTop:   'var(--spacing-8)',
            paddingTop:  'var(--spacing-6)',
            borderTop:   '1px solid rgba(0,0,0,.08)',
          }}
        >
          <SourceAttribution
            sourceName={pubName}
            publishedAt={publishedAt}
            sourceUrl={articleUrl}
          />
        </div>
      </article>

      {/* ── Related Topics ── */}
      {related.length > 0 && (
        <section
          style={{
            maxWidth:    800,
            margin:      '0 auto',
            padding:     '0 var(--spacing-4) var(--spacing-16)',
          }}
        >
          <h2
            style={{
              fontFamily:   'var(--font-heading)',
              fontSize:     'clamp(18px, 3vw, 24px)',
              fontWeight:   700,
              color:        'var(--color-text-primary-light)',
              marginBottom: 'var(--spacing-4)',
            }}
          >
            Related Topics
          </h2>
          <div
            style={{
              display:             'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))',
              gap:                 'var(--spacing-4)',
            }}
          >
            {related.map(rel => (
              <NavigableTopicCard key={rel.id} topic={rel} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
