/**
 * Google Discover image optimization.
 * Discover prefers at least 1200px width and 1.91:1 or 16:9 aspect (e.g. 1200×628).
 * See: https://developers.google.com/search/docs/appearance/google-images
 */

const DISCOVER_WIDTH = 1200;
const DISCOVER_HEIGHT = 628;

/**
 * If the image URL is from our Supabase Storage public bucket, return the
 * render/transform URL at 1200×628 for OG/Discover. Otherwise return the
 * original URL (e.g. YouTube, Wikipedia) — crawlers will use it as-is.
 */
export function discoverImageUrl(
  imageUrl: string | null | undefined,
  supabaseHostname: string | undefined,
): string | undefined {
  if (!imageUrl?.trim()) return undefined;
  if (!supabaseHostname) return imageUrl;

  try {
    const u = new URL(imageUrl);
    // Match Supabase storage public object URL: .../storage/v1/object/public/bucket/path
    const match = u.pathname.match(/^\/storage\/v1\/object\/public\/([^/]+)\/(.+)$/);
    if (!match || u.hostname !== supabaseHostname) return imageUrl;

    const [, bucket, objectPath] = match;
    const renderPath = `/storage/v1/render/image/public/${bucket}/${objectPath}`;
    const renderUrl = new URL(renderPath, u.origin);
    renderUrl.searchParams.set('width', String(DISCOVER_WIDTH));
    renderUrl.searchParams.set('height', String(DISCOVER_HEIGHT));
    return renderUrl.toString();
  } catch {
    return imageUrl;
  }
}

export const DISCOVER_IMAGE_WIDTH = DISCOVER_WIDTH;
export const DISCOVER_IMAGE_HEIGHT = DISCOVER_HEIGHT;
