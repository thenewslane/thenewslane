/**
 * AuthorSchema — server component
 *
 * Injects a Person JSON-LD schema block into the page <head> on every route,
 * establishing the author entity for Google's Knowledge Graph and E-E-A-T signals.
 *
 * Configure via environment variables:
 *   AUTHOR_NAME            — display name (default: "theNewslane Editorial")
 *   AUTHOR_PAGE_PATH       — path to author page (default: "/about")
 *   AUTHOR_TWITTER_URL     — e.g. https://twitter.com/thenewslane
 *   AUTHOR_LINKEDIN_URL    — e.g. https://linkedin.com/company/thenewslane
 *   AUTHOR_SAMEAS         — comma-separated list of verified profile URLs (optional)
 *   PUBLICATION_DOMAIN    — canonical domain
 */

const pubDomain  = process.env.PUBLICATION_DOMAIN ?? '';
const baseUrl    = pubDomain ? `https://${pubDomain}` : 'http://localhost:3000';
const authorName = process.env.AUTHOR_NAME ?? 'theNewslane Editorial';
const authorPath = (process.env.AUTHOR_PAGE_PATH ?? '/about').replace(/^\/+/, '/');
const authorUrl  = `${baseUrl}${authorPath}`;

const sameAs = [
  process.env.AUTHOR_TWITTER_URL,
  process.env.AUTHOR_LINKEDIN_URL,
  ...(typeof process.env.AUTHOR_SAMEAS === 'string'
    ? process.env.AUTHOR_SAMEAS.split(',').map((u) => u.trim()).filter(Boolean)
    : []),
].filter(Boolean) as string[];

const personSchema = {
  '@context': 'https://schema.org',
  '@type':    'Person',
  name:       authorName,
  url:        authorUrl,
  ...(sameAs.length > 0 ? { sameAs } : {}),
};

export function AuthorSchema() {
  return (
    <script
      type="application/ld+json"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: JSON.stringify(personSchema) }}
    />
  );
}
