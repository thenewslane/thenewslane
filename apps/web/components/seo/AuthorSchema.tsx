/**
 * AuthorSchema — server component
 *
 * Injects a Person JSON-LD schema block into the page <head> on every route,
 * establishing the author entity for Google's Knowledge Graph and E-E-A-T signals.
 *
 * Configure via environment variables:
 *   AUTHOR_NAME            — display name (default: "theNewslane Editorial")
 *   AUTHOR_TWITTER_URL     — e.g. https://twitter.com/thenewslane
 *   AUTHOR_LINKEDIN_URL    — e.g. https://linkedin.com/company/thenewslane
 *   PUBLICATION_DOMAIN     — canonical domain
 */

const pubDomain  = process.env.PUBLICATION_DOMAIN ?? '';
const baseUrl    = pubDomain ? `https://${pubDomain}` : 'http://localhost:3000';
const authorName = process.env.AUTHOR_NAME ?? 'theNewslane Editorial';

const sameAs = [
  process.env.AUTHOR_TWITTER_URL,
  process.env.AUTHOR_LINKEDIN_URL,
].filter(Boolean) as string[];

const personSchema = {
  '@context': 'https://schema.org',
  '@type':    'Person',
  name:       authorName,
  url:        `${baseUrl}/about`,
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
