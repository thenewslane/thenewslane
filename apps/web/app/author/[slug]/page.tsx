/**
 * Author profile page — /author/[slug]
 *
 * Dedicated E-E-A-T profile page for each named author (jay, aadi, julie).
 * Shows: profile card (avatar, name, role, bio), article count, and
 * a paginated feed of their published articles.
 *
 * 404 for any slug not in the known-authors map.
 * ISR: revalidate = 300 (5 min)
 */

import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getServerClient } from '@platform/supabase';
import type { TrendingTopic } from '@platform/types';

export const revalidate = 300;

// ---------------------------------------------------------------------------
// Author data (source of truth for profile content)
// ---------------------------------------------------------------------------
interface AuthorProfile {
  name:      string;
  honorific: string;
  bio:       string;
}

const AUTHORS: Record<string, AuthorProfile> = {
  jay: {
    name:      'Jay',
    honorific: 'Contributing Editor',
    bio:       'Jay is a contributing editor at theNewslane with extensive experience covering global affairs, technology, and culture. He brings investigative depth and analytical clarity to every story, ensuring that trending topics are presented with the context readers need to understand what truly matters.',
  },
  aadi: {
    name:      'Aadi',
    honorific: 'Founder & Editor-in-Chief',
    bio:       'Aadi founded theNewslane to prove that AI and editorial craftsmanship can coexist. With a background in digital media and machine learning, Aadi designed the platform\'s viral-prediction engine and oversees all editorial decisions — from the categories we cover to the stories that make the front page.',
  },
  julie: {
    name:      'Julie',
    honorific: 'Senior Correspondent',
    bio:       'Julie is a senior correspondent at theNewslane specialising in breaking news, technology, and political affairs. She brings a sharp editorial eye to the AI-curated pipeline, ensuring every story is framed with accuracy, nuance, and the reader firmly in mind.',
  },
};

const ARTICLE_LIMIT = 18;
const pubName   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const pubDomain = process.env.PUBLICATION_DOMAIN ?? '';
const baseUrl   = pubDomain ? `https://${pubDomain}` : 'http://localhost:3000';

// ---------------------------------------------------------------------------
// Static params — pre-render all three author pages at build time
// ---------------------------------------------------------------------------
export async function generateStaticParams(): Promise<{ slug: string }[]> {
  return Object.keys(AUTHORS).map(slug => ({ slug }));
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------
export async function generateMetadata(
  { params }: { params: { slug: string } },
): Promise<Metadata> {
  const author = AUTHORS[params.slug];
  if (!author) return { title: 'Not Found' };

  const title = `${author.name} · ${author.honorific} · ${pubName}`;
  const description = author.bio.slice(0, 155) + '…';
  const url = `${baseUrl}/author/${params.slug}`;

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      type: 'profile',
      siteName: pubName,
    },
  };
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------
async function getAuthorArticles(authorName: string): Promise<TrendingTopic[]> {
  const supabase = getServerClient();
  const { data } = await supabase
    .from('trending_topics')
    .select('id, title, slug, summary, published_at, thumbnail_url, viral_tier, category:categories(id, name, slug, color, description)')
    .eq('status', 'published')
    .eq('fact_check', 'yes')
    .eq('author_name', authorName)
    .order('published_at', { ascending: false })
    .limit(ARTICLE_LIMIT);
  return (data ?? []) as TrendingTopic[];
}

// ---------------------------------------------------------------------------
// Shared style constants
// ---------------------------------------------------------------------------
const bodyStyle: React.CSSProperties = {
  fontFamily: 'var(--font-body)',
  fontSize:   '15px',
  lineHeight: 1.75,
  color:      'var(--color-text-secondary-light)',
  margin:     '0 0 var(--spacing-4)',
};

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
export default async function AuthorPage({
  params,
}: {
  params: { slug: string };
}) {
  const author = AUTHORS[params.slug];
  if (!author) notFound();

  const articles = await getAuthorArticles(author.name);

  const profileUrl = `${baseUrl}/author/${params.slug}`;
  const personSchema = {
    '@context':  'https://schema.org',
    '@type':     'Person',
    name:        author.name,
    jobTitle:    author.honorific,
    url:         profileUrl,
    worksFor: {
      '@type': 'Organization',
      name:    pubName,
      url:     baseUrl,
    },
    description: author.bio,
  };

  return (
    <>
      <JsonLd data={personSchema} />

      <div
        style={{
          maxWidth: 720,
          margin:   '0 auto',
          padding:  'var(--spacing-12) var(--spacing-4) var(--spacing-16)',
        }}
      >
        {/* ── Breadcrumb ── */}
        <nav
          aria-label="Breadcrumb"
          style={{
            marginBottom: 'var(--spacing-6)',
            fontSize:     '13px',
            fontFamily:   'var(--font-body)',
            fontWeight:   600,
            letterSpacing:'0.06em',
            textTransform:'uppercase',
          }}
        >
          <Link
            href="/"
            style={{ color: 'var(--color-text-muted-light)', textDecoration: 'none' }}
          >
            Home
          </Link>
          <span style={{ color: 'var(--color-text-muted-light)', margin: '0 var(--spacing-2)' }} aria-hidden>›</span>
          <span style={{ color: 'var(--color-text-secondary-light)' }}>Author</span>
        </nav>

        {/* ── Profile card ── */}
        <section aria-labelledby="author-name" style={{ marginBottom: 'var(--spacing-10)' }}>
          <div
            style={{
              display:    'flex',
              gap:        'var(--spacing-6)',
              alignItems: 'flex-start',
              flexWrap:   'wrap',
            }}
          >
            {/* Avatar with initials */}
            <div
              aria-hidden
              style={{
                flexShrink:      0,
                width:           96,
                height:          96,
                borderRadius:    '50%',
                backgroundColor: 'var(--color-primary)',
                border:          '3px solid var(--color-primary)',
                display:         'flex',
                alignItems:      'center',
                justifyContent:  'center',
                color:           '#fff',
                fontSize:        38,
                fontWeight:      700,
                fontFamily:      'var(--font-heading)',
              }}
            >
              {author.name.charAt(0).toUpperCase()}
            </div>

            {/* Name + role */}
            <div style={{ flex: 1, minWidth: 200 }}>
              <h1
                id="author-name"
                style={{
                  fontFamily:  'var(--font-heading)',
                  fontSize:    'clamp(26px, 5vw, 36px)',
                  fontWeight:  800,
                  color:       'var(--color-text-primary-light)',
                  margin:      '0 0 var(--spacing-1)',
                  lineHeight:  1.15,
                }}
              >
                {author.name}
              </h1>
              <p
                style={{
                  fontFamily:    'var(--font-body)',
                  fontSize:      '13px',
                  fontWeight:    600,
                  color:         'var(--color-primary)',
                  margin:        '0 0 var(--spacing-3)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                {author.honorific} · {pubName}
              </p>
              <p style={{ ...bodyStyle, margin: 0 }}>{author.bio}</p>
            </div>
          </div>
        </section>

        <hr
          style={{
            border:    'none',
            borderTop: '1px solid rgba(0,0,0,.08)',
            margin:    '0 0 var(--spacing-8)',
          }}
        />

        {/* ── Articles feed ── */}
        <section aria-labelledby="articles-heading">
          <h2
            id="articles-heading"
            style={{
              fontFamily: 'var(--font-heading)',
              fontSize:   'clamp(18px, 3vw, 22px)',
              fontWeight: 700,
              color:      'var(--color-text-primary-light)',
              margin:     '0 0 var(--spacing-5)',
            }}
          >
            Articles by {author.name}
            {articles.length > 0 && (
              <span
                style={{
                  marginLeft:  'var(--spacing-2)',
                  fontSize:    '14px',
                  fontWeight:  400,
                  color:       'var(--color-text-muted-light)',
                }}
              >
                ({articles.length}{articles.length === ARTICLE_LIMIT ? '+' : ''})
              </span>
            )}
          </h2>

          {articles.length === 0 ? (
            <p style={bodyStyle}>No published articles yet.</p>
          ) : (
            <ul
              style={{
                listStyle: 'none',
                padding:   0,
                margin:    0,
                display:   'flex',
                flexDirection: 'column',
                gap:       'var(--spacing-4)',
              }}
            >
              {articles.map(article => (
                <li
                  key={article.id}
                  style={{
                    borderBottom: '1px solid rgba(0,0,0,.06)',
                    paddingBottom: 'var(--spacing-4)',
                  }}
                >
                  <Link
                    href={`/trending/${article.slug}`}
                    style={{ textDecoration: 'none' }}
                  >
                    <p
                      style={{
                        fontFamily:  'var(--font-heading)',
                        fontSize:    '16px',
                        fontWeight:  700,
                        color:       'var(--color-text-primary-light)',
                        margin:      '0 0 var(--spacing-1)',
                        lineHeight:  1.3,
                      }}
                    >
                      {article.title}
                    </p>
                    {article.summary && (
                      <p
                        style={{
                          fontFamily: 'var(--font-body)',
                          fontSize:   '13px',
                          color:      'var(--color-text-muted-light)',
                          margin:     '0 0 var(--spacing-1)',
                          overflow:   'hidden',
                          display:    '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                        } as React.CSSProperties}
                      >
                        {article.summary}
                      </p>
                    )}
                    <span
                      style={{
                        fontFamily: 'var(--font-body)',
                        fontSize:   '12px',
                        color:      'var(--color-text-muted-light)',
                      }}
                    >
                      {article.published_at
                        ? new Date(article.published_at).toLocaleDateString('en-US', {
                            year: 'numeric', month: 'short', day: 'numeric',
                          })
                        : ''}
                      {article.category && (
                        <span
                          style={{
                            marginLeft: 'var(--spacing-2)',
                            color:      `var(--color-category-${article.category.slug})`,
                            fontWeight: 600,
                          }}
                        >
                          · {article.category.name}
                        </span>
                      )}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* ── Footer nav ── */}
        <hr
          style={{
            border:    'none',
            borderTop: '1px solid rgba(0,0,0,.08)',
            margin:    'var(--spacing-10) 0 var(--spacing-6)',
          }}
        />
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontSize:   '13px',
            color:      'var(--color-text-muted-light)',
            margin:     0,
          }}
        >
          <Link href="/about" style={{ color: 'var(--color-link)' }}>About {pubName}</Link>
          {' · '}
          <Link href="/editorial-policy" style={{ color: 'var(--color-link)' }}>Editorial Policy</Link>
          {' · '}
          <Link href="/contact" style={{ color: 'var(--color-link)' }}>Contact</Link>
        </p>
      </div>
    </>
  );
}
