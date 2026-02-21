/**
 * POST /api/revalidate
 *
 * On-demand ISR revalidation for article and homepage routes.
 * Called by the Inngest pipeline agent after publishing a new topic.
 *
 * Request body: { secret: string; slug: string }
 *   secret — must match REVALIDATE_SECRET env var
 *   slug   — the trending_topic slug to revalidate
 *
 * Response 200: { revalidated: true; paths: string[] }
 * Response 401: { error: 'Unauthorised' }
 * Response 400: { error: 'slug is required' }
 * Response 500: { error: string }
 *
 * Environment variables:
 *   REVALIDATE_SECRET — set in Vercel dashboard; shared with Inngest pipeline
 */

import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath }            from 'next/cache';

const REVALIDATE_SECRET = process.env.REVALIDATE_SECRET ?? '';

export async function POST(req: NextRequest) {
  // ── Auth ─────────────────────────────────────────────────────────────
  if (!REVALIDATE_SECRET) {
    console.error('[revalidate] REVALIDATE_SECRET is not configured');
    return NextResponse.json({ error: 'Revalidation not configured.' }, { status: 500 });
  }

  let body: { secret?: unknown; slug?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
  }

  if (body.secret !== REVALIDATE_SECRET) {
    return NextResponse.json({ error: 'Unauthorised.' }, { status: 401 });
  }

  // ── Validate slug ─────────────────────────────────────────────────────
  const slug = typeof body.slug === 'string' ? body.slug.trim() : '';
  if (!slug) {
    return NextResponse.json({ error: 'slug is required.' }, { status: 400 });
  }

  // ── Revalidate ────────────────────────────────────────────────────────
  const paths: string[] = [];

  try {
    // Article page
    const articlePath = `/trending/${slug}`;
    revalidatePath(articlePath);
    paths.push(articlePath);

    // Homepage — shows latest articles, should reflect new publications
    revalidatePath('/');
    paths.push('/');

    console.log(`[revalidate] Revalidated: ${paths.join(', ')}`);

    return NextResponse.json({ revalidated: true, paths });
  } catch (err) {
    console.error('[revalidate] revalidatePath failed:', err);
    return NextResponse.json(
      { error: 'Revalidation failed. See server logs.' },
      { status: 500 },
    );
  }
}
