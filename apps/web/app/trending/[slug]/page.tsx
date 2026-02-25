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
import Image             from 'next/image';
import Link              from 'next/link';
import { notFound }       from 'next/navigation';
import { getServerClient } from '@platform/supabase';
import type { TrendingTopic } from '@platform/types';
import { VideoPlayer, AuthorByline, SourceAttribution } from '@platform/ui/web';
import { FaqAccordion }       from '@/components/FaqAccordion';
import { ShareBar }           from '@/components/ShareBar';
import { AdSlot }             from '@/components/ads/AdSlot';
import { NavigableTopicCard } from '@/components/NavigableTopicCard';
import { AD_UNITS }           from '@/config/ad-units';
import { discoverImageUrl, DISCOVER_IMAGE_WIDTH, DISCOVER_IMAGE_HEIGHT } from '@/lib/discover-image';
import { formatAndNormalizeArticleText } from '@/lib/format-article-text';

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
      .eq('fact_check', 'yes')
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
    .eq('fact_check', 'yes')
    .single();
  if (error || !data) return null;
  return data as TrendingTopic;
}

const RELATED_COUNT = 5;

async function getRelatedTopics(topic: TrendingTopic): Promise<TrendingTopic[]> {
  const supabase = getServerClient();
  const excludeId = topic.id;

  // 1) Prefer same category, up to RELATED_COUNT
  let query = supabase
    .from('trending_topics')
    .select('*, category:categories(id, name, slug, color, description)')
    .eq('status', 'published')
    .eq('fact_check', 'yes')
    .neq('id', excludeId)
    .order('published_at', { ascending: false })
    .limit(RELATED_COUNT);

  if (topic.category_id) {
    query = query.eq('category_id', topic.category_id);
  }

  const { data: sameCategory } = await query;
  const related = (sameCategory ?? []) as TrendingTopic[];

  // 2) If fewer than RELATED_COUNT, fill with most recent (any category)
  if (related.length < RELATED_COUNT) {
    const haveIds = new Set(related.map((r) => r.id));
    haveIds.add(excludeId);
    const need = RELATED_COUNT - related.length;
    const { data: recent } = await supabase
      .from('trending_topics')
      .select('*, category:categories(id, name, slug, color, description)')
      .eq('status', 'published')
      .eq('fact_check', 'yes')
      .order('published_at', { ascending: false })
      .limit(need + 10);
    const recentList = (recent ?? []) as TrendingTopic[];
    for (const t of recentList) {
      if (haveIds.has(t.id)) continue;
      related.push(t);
      haveIds.add(t.id);
      if (related.length >= RELATED_COUNT) break;
    }
  }

  return related;
}

// ---------------------------------------------------------------------------
// Extract FAQ items from schema_blocks
//
// schema_blocks is stored as a plain object by the pipeline:
//   { faq: [{question, answer}, ...], seo_title, image_prompt, ... }
// ---------------------------------------------------------------------------
interface FaqItem {
  question: string;
  answer:   string;
}

function extractFaqItems(schemaBlocks: Record<string, unknown> | null): FaqItem[] {
  if (!schemaBlocks) return [];

  // Pipeline stores FAQ directly under the "faq" key
  const faq = schemaBlocks['faq'];
  if (Array.isArray(faq)) {
    return (faq as unknown[]).reduce<FaqItem[]>((acc, item) => {
      if (
        item &&
        typeof item === 'object' &&
        'question' in item &&
        'answer' in item &&
        typeof (item as FaqItem).question === 'string' &&
        typeof (item as FaqItem).answer   === 'string'
      ) {
        acc.push({ question: (item as FaqItem).question, answer: (item as FaqItem).answer });
      }
      return acc;
    }, []);
  }

  return [];
}

// ---------------------------------------------------------------------------
// Build VideoObject JSON-LD from topic columns
// ---------------------------------------------------------------------------
function buildVideoSchema(
  topic: TrendingTopic,
  articleUrl: string,
  embedId: string | undefined,
): Record<string, unknown> | null {
  if (!topic.video_url && !embedId) return null;
  return {
    '@context': 'https://schema.org',
    '@type':    'VideoObject',
    name:        topic.title,
    description: topic.summary ?? '',
    thumbnailUrl: topic.thumbnail_url ?? undefined,
    uploadDate:   topic.published_at ?? topic.created_at,
    ...(topic.video_url ? { contentUrl: topic.video_url } : {}),
    ...(embedId
      ? { embedUrl: `https://www.youtube.com/embed/${embedId}` }
      : {}),
    publisher: {
      '@type': 'Organization',
      name:    pubName,
      url:     baseUrl,
    },
  };
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------
const pubName   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const pubDomain = process.env.PUBLICATION_DOMAIN ?? '';
const baseUrl   = pubDomain ? `https://${pubDomain}` : 'http://localhost:3000';
const supabaseHostname = process.env.NEXT_PUBLIC_SUPABASE_URL
  ? (() => { try { return new URL(process.env.NEXT_PUBLIC_SUPABASE_URL!).hostname; } catch { return undefined; } })()
  : undefined;
const authorName = process.env.AUTHOR_NAME ?? 'theNewslane Editorial';
const defaultDateline = process.env.PUBLICATION_COUNTRY ?? 'United States';

export async function generateMetadata(
  { params }: { params: { slug: string } },
): Promise<Metadata> {
  const topic = await getTopic(params.slug);
  if (!topic) return { title: 'Not Found' };

  const url        = `${baseUrl}/trending/${topic.slug}`;
  const imageUrl   = topic.thumbnail_url ?? undefined;
  const discoverOgImage = discoverImageUrl(imageUrl, supabaseHostname) ?? imageUrl;
  // Ensure og:image is absolute (Google Discover requires absolute URL, min 1200×628)
  const ogImageUrl = discoverOgImage
    ? (discoverOgImage.startsWith('http') ? discoverOgImage : `${baseUrl}${discoverOgImage.startsWith('/') ? '' : '/'}${discoverOgImage}`)
    : undefined;
  const sbMeta     = topic.schema_blocks as Record<string, unknown> | null;
  const description =
    (topic.summary && topic.summary.trim()) ||
    (typeof sbMeta?.meta_description === 'string' && sbMeta.meta_description.trim()) ||
    (typeof sbMeta?.seo_title === 'string' && sbMeta.seo_title.trim()) ||
    `${pubName} — AI-curated trending news.`;
  const publishedAt = topic.published_at ?? topic.created_at;

  return {
    title:       topic.title,
    description,
    alternates:  { canonical: url },
    openGraph: {
      title:             topic.title,
      description,
      url,
      type:              'article',
      siteName:          pubName,
      publishedTime:     publishedAt,
      modifiedTime:      topic.updated_at,
      authors:           [authorName],
      images:            ogImageUrl
        ? [{ url: ogImageUrl, alt: topic.title, width: DISCOVER_IMAGE_WIDTH, height: DISCOVER_IMAGE_HEIGHT }]
        : [],
      tags:              topic.iab_tags ?? [],
    },
    twitter: {
      card:        'summary_large_image',
      title:       topic.title,
      description,
      images:      discoverOgImage ? [discoverOgImage] : [],
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
  const allowAds     = (topic.schema_blocks as Record<string, unknown> | null)?.brand_safe !== false;

  // Summary: prefer DB column, then schema_blocks.meta_description / seo_title
  const sb = topic.schema_blocks as Record<string, unknown> | null;
  const displaySummary =
    (topic.summary && topic.summary.trim()) ||
    (typeof sb?.meta_description === 'string' && sb.meta_description.trim()) ||
    (typeof sb?.seo_title === 'string' && sb.seo_title.trim()) ||
    null;
  // Dateline: city and/or country before article (schema_blocks.dateline or .location or default)
  const dateline =
    (typeof sb?.dateline === 'string' && sb.dateline.trim()) ||
    (typeof sb?.location === 'string' && sb.location.trim()) ||
    defaultDateline;

  // Body paragraphs (split on double newline); fallback to single paragraph if article is one line
  const rawArticle = (topic.article && topic.article.trim()) || '';
  const paragraphs = rawArticle
    ? rawArticle.split(/\n{2,}/).map(p => p.trim()).filter(Boolean)
    : [];
  const hasArticleBody = paragraphs.length > 0;

  // Resolve video data — embed ID lives in schema_blocks for YouTube/Vimeo
  const embedId    = typeof sb?.['video_id'] === 'string' ? sb['video_id'] : undefined;
  const videoSchema = buildVideoSchema(topic, articleUrl, embedId);
  const hasVideo   =
    (topic.video_type === 'youtube_embed' && !!embedId) ||
    (topic.video_type === 'vimeo_embed'   && !!embedId) ||
    (topic.video_type === 'kling_generated' && !!topic.video_url);

  // ── JSON-LD: NewsArticle (required for Google Discover / rich results) ───
  const authorPageUrl = `${baseUrl}/about`;
  const newsArticleSchema: Record<string, unknown> = {
    '@context':        'https://schema.org',
    '@type':           'NewsArticle',
    headline:          topic.title,
    description:       displaySummary ?? topic.summary ?? '',
    url:               articleUrl,
    datePublished:     publishedAt,
    dateModified:      topic.updated_at,
    author: [
      { '@type': 'Person', name: authorName, url: authorPageUrl },
      { '@type': 'Organization', name: pubName, url: baseUrl },
    ],
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
        {/* ── Breadcrumb (Home › Category only; no slug/title) ── */}
        <nav
          aria-label="Breadcrumb"
          style={{
            margin:      '0 0 var(--spacing-3)',
            fontSize:    '13px',
            fontFamily:  'var(--font-body)',
            fontWeight:  600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
        >
          <Link
            href="/"
            style={{
              color:           'var(--color-text-muted-light)',
              textDecoration:  'none',
            }}
          >
            Home
          </Link>
          {topic.category ? (
            <>
              <span style={{ color: 'var(--color-text-muted-light)', margin: '0 var(--spacing-2)' }} aria-hidden>›</span>
              <Link
                href={`/category/${topic.category.slug}`}
                style={{
                  color:           `var(--color-category-${topic.category.slug})`,
                  textDecoration:  'none',
                }}
              >
                {topic.category.name}
              </Link>
            </>
          ) : null}
        </nav>

        {/* ── Title ── */}
        <h1
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     'clamp(24px, 5vw, 40px)',
            fontWeight:   700,
            lineHeight:   1.2,
            color:        'var(--color-text-primary-light)',
            margin:       '0 0 var(--spacing-2)',
          }}
        >
          {formatAndNormalizeArticleText(topic.title)}
        </h1>

        {/* ── Dateline (country/city before article detail) ── */}
        <p
          style={{
            fontFamily:  'var(--font-body)',
            fontSize:    '13px',
            fontWeight:  600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color:       'var(--color-text-muted-light)',
            margin:      '0 0 var(--spacing-4)',
          }}
        >
          {formatAndNormalizeArticleText(dateline)}
        </p>

        {/* ── Byline ── */}
        <div style={{ marginBottom: 'var(--spacing-6)' }}>
          <AuthorByline
            authorName={authorName}
            publishedAt={publishedAt}
          />
          {topic.updated_at && publishedAt && topic.updated_at > publishedAt && (
            <p
              style={{
                margin:     'var(--spacing-1) 0 0',
                fontSize:   '12px',
                fontFamily: 'var(--font-body)',
                color:      'var(--color-text-muted-light)',
              }}
            >
              Last updated{' '}
              <time dateTime={topic.updated_at}>
                {new Date(topic.updated_at).toLocaleDateString(undefined, {
                  dateStyle: 'medium',
                })}
              </time>
            </p>
          )}
        </div>

        {/* ── Share bar ── */}
        <div style={{ marginBottom: 'var(--spacing-6)' }}>
          <ShareBar url={articleUrl} title={topic.title} />
        </div>

        {/* ── Hero thumbnail (LCP candidate): priority load, explicit size for CLS ── */}
        {!hasVideo && topic.thumbnail_url && (
          <div
            style={{
              position:     'relative',
              marginBottom: 'var(--spacing-6)',
              borderRadius: 'var(--radius-large)',
              overflow:     'hidden',
              width:        '100%',
              aspectRatio:  '16 / 9',
              minHeight:    200,
            }}
          >
            <Image
              src={topic.thumbnail_url}
              alt={topic.title}
              fill
              priority
              sizes="(max-width: 800px) 100vw, 800px"
              style={{ objectFit: 'cover' }}
            />
          </div>
        )}

        {/* ── Summary lead ── */}
        {displaySummary && (
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
            {formatAndNormalizeArticleText(displaySummary)}
          </p>
        )}

        {/* ── Article body — video injected after 3rd paragraph ── */}
        {hasArticleBody ? (
          <div style={{ marginBottom: 'var(--spacing-6)' }}>
            {paragraphs.map((para, idx) => (
              <React.Fragment key={idx}>
                <p
                  style={{
                    fontFamily: 'var(--font-body)',
                    fontSize:   '16px',
                    lineHeight: 1.8,
                    color:      'var(--color-text-primary-light)',
                    margin:     '0 0 var(--spacing-4)',
                  }}
                >
                  {formatAndNormalizeArticleText(para)}
                </p>

                {/* Video embedded after 3rd paragraph (YouTube/Vimeo/Kling — embed-friendly, copyright-safe sources) */}
                {idx === 2 && hasVideo && (
                  <div style={{ margin: 'var(--spacing-6) 0', borderRadius: 'var(--radius-large)', overflow: 'hidden' }}>
                    <VideoPlayer
                      videoType={topic.video_type}
                      videoId={
                        (topic.video_type === 'youtube_embed' || topic.video_type === 'vimeo_embed')
                          ? embedId
                          : undefined
                      }
                      videoUrl={
                        topic.video_type === 'kling_generated'
                          ? (topic.video_url ?? undefined)
                          : undefined
                      }
                      thumbnailUrl={topic.thumbnail_url ?? undefined}
                      title={topic.title}
                    />
                  </div>
                )}

                {/* In-content ad after 3rd paragraph (disabled for UNSAFE / brand-unsafe content) */}
                {idx === 2 && allowAds && (
                  <div style={{ margin: 'var(--spacing-6) 0', display: 'flex', justifyContent: 'center' }}>
                    <AdSlot
                      unitPath={AD_UNITS.IN_CONTENT.unitPath}
                      sizes={AD_UNITS.IN_CONTENT.sizes as [number, number][]}
                      targeting={{ iab_categories: topic.iab_tags ?? [] }}
                      id="gam-in-content"
                    />
                  </div>
                )}

                {/* Similar News after 4th paragraph (at least 1 line of content between ad and this) */}
                {idx === 3 && related.length > 0 && (
                  <section
                    style={{
                      marginTop:   'var(--spacing-8)',
                      marginBottom: 'var(--spacing-6)',
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
                      Similar News
                    </h2>
                    <div
                      style={{
                        display:        'flex',
                        flexDirection:  'row',
                        gap:            'var(--spacing-4)',
                        overflowX:      'auto',
                        overflowY:      'hidden',
                        paddingBottom:  'var(--spacing-2)',
                        scrollSnapType: 'x mandatory',
                        WebkitOverflowScrolling: 'touch',
                      }}
                    >
                      {related.map(rel => (
                        <div
                          key={rel.id}
                          style={{
                            flex:            '0 0 50%',
                            minWidth:        280,
                            maxWidth:        400,
                            display:         'flex',
                            flexDirection:   'column',
                            scrollSnapAlign: 'start',
                          }}
                        >
                          <NavigableTopicCard topic={rel} />
                          <span
                            style={{
                              marginTop:    'var(--spacing-1)',
                              fontSize:     '11px',
                              fontFamily:   'var(--font-body)',
                              color:        'var(--color-text-muted-light)',
                              overflow:     'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace:   'nowrap',
                            }}
                          >
                            /trending/{rel.slug}
                          </span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </React.Fragment>
            ))}
            {/* If fewer than 4 paragraphs, show Similar News after the last one (no “1 line” gap) */}
            {paragraphs.length > 0 && paragraphs.length < 4 && related.length > 0 && (
              <section
                style={{
                  marginTop:   'var(--spacing-8)',
                  marginBottom: 'var(--spacing-6)',
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
                  Similar News
                </h2>
                <div
                  style={{
                    display:        'flex',
                    flexDirection:  'row',
                    gap:            'var(--spacing-4)',
                    overflowX:      'auto',
                    overflowY:      'hidden',
                    paddingBottom:  'var(--spacing-2)',
                    scrollSnapType: 'x mandatory',
                    WebkitOverflowScrolling: 'touch',
                  }}
                >
                  {related.map(rel => (
                    <div
                      key={rel.id}
                      style={{
                        flex:            '0 0 50%',
                        minWidth:        280,
                        maxWidth:        400,
                        display:         'flex',
                        flexDirection:   'column',
                        scrollSnapAlign: 'start',
                      }}
                    >
                      <NavigableTopicCard topic={rel} />
                      <span
                        style={{
                          marginTop:    'var(--spacing-1)',
                          fontSize:     '11px',
                          fontFamily:   'var(--font-body)',
                          color:        'var(--color-text-muted-light)',
                          overflow:     'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace:   'nowrap',
                        }}
                      >
                        /trending/{rel.slug}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        ) : (
          <p
            style={{
              fontFamily: 'var(--font-body)',
              fontSize:   '16px',
              lineHeight: 1.8,
              color:      'var(--color-text-muted-light)',
              margin:     '0 0 var(--spacing-6)',
            }}
          >
            Content is being prepared. Check back soon.
          </p>
        )}

        {/* ── FAQ accordion ── */}
        <FaqAccordion items={faqItems} />

        {/* ── Source attribution (1 source per article when available, rel=nofollow) ── */}
        <div
          style={{
            marginTop:   'var(--spacing-8)',
            paddingTop:  'var(--spacing-6)',
            borderTop:   '1px solid rgba(0,0,0,.08)',
          }}
        >
          <div style={{ marginBottom: 'var(--spacing-6)' }}>
            <ShareBar url={articleUrl} title={topic.title} />
          </div>
          <SourceAttribution
            sourceName={(() => {
              const sb = topic.schema_blocks ?? {};
              const sourceUrl = typeof sb['source_url'] === 'string' ? sb['source_url'] : undefined;
              const sourceName = typeof sb['source_name'] === 'string' ? sb['source_name'] : undefined;
              if (sourceUrl && pubDomain && !sourceUrl.startsWith(baseUrl)) return sourceName ?? 'Source';
              return pubName;
            })()}
            publishedAt={publishedAt}
            sourceUrl={(() => {
              const sb = topic.schema_blocks ?? {};
              const sourceUrl = typeof sb['source_url'] === 'string' ? sb['source_url'] : undefined;
              if (sourceUrl && pubDomain && !sourceUrl.startsWith(baseUrl)) return sourceUrl;
              return articleUrl;
            })()}
          />
        </div>
      </article>

      {/* ── Mobile anchor ad — fixed bottom, mobile only (disabled for UNSAFE content) ── */}
      {allowAds && (
        <div
          style={{
            position:   'fixed',
            bottom:     0,
            left:       0,
            right:      0,
            zIndex:     50,
            display:    'flex',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
          className="mobile-anchor-ad"
        >
          <div style={{ pointerEvents: 'auto' }}>
            <AdSlot
              unitPath={AD_UNITS.MOBILE_ANCHOR.unitPath}
              sizes={AD_UNITS.MOBILE_ANCHOR.sizes as [number, number][]}
              id="gam-mobile-anchor"
            />
          </div>
        </div>
      )}
    </>
  );
}
