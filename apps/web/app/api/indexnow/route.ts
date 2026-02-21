/**
 * POST /api/indexnow
 *
 * Pings the IndexNow API to notify search engines of newly published content.
 * Called by the Inngest pipeline agent after publishing + revalidating a topic.
 *
 * Request body: { secret: string; url: string }
 *   secret — must match REVALIDATE_SECRET (shared secret with the pipeline)
 *   url    — the canonical URL of the newly published page
 *
 * Response 200: { ok: true; url: string; indexnowStatus: number }
 * Response 401: { error: 'Unauthorised' }
 * Response 400: { error: string }
 * Response 500/502: { error: string }
 *
 * Environment variables:
 *   INDEXNOW_KEY     — your IndexNow API key (set in Vercel dashboard)
 *                      Place the verification file at /{INDEXNOW_KEY}.txt in /public
 *   REVALIDATE_SECRET — shared with the Inngest pipeline for auth
 *   PUBLICATION_DOMAIN — e.g. thenewslane.com
 *
 * IndexNow verification:
 *   Create apps/web/public/{INDEXNOW_KEY}.txt containing just the key value.
 *   This satisfies the IndexNow ownership verification requirement.
 *
 * IndexNow endpoint pings both Bing and Yandex via api.indexnow.org (shared endpoint).
 */

import { NextRequest, NextResponse } from 'next/server';

const REVALIDATE_SECRET  = process.env.REVALIDATE_SECRET  ?? '';
const INDEXNOW_KEY       = process.env.INDEXNOW_KEY       ?? '';
const PUBLICATION_DOMAIN = process.env.PUBLICATION_DOMAIN ?? '';

const INDEXNOW_ENDPOINT  = 'https://api.indexnow.org/indexnow';

export async function POST(req: NextRequest) {
  // ── Auth ─────────────────────────────────────────────────────────────
  if (!REVALIDATE_SECRET) {
    console.error('[indexnow] REVALIDATE_SECRET is not configured');
    return NextResponse.json({ error: 'Not configured.' }, { status: 500 });
  }

  let body: { secret?: unknown; url?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
  }

  if (body.secret !== REVALIDATE_SECRET) {
    return NextResponse.json({ error: 'Unauthorised.' }, { status: 401 });
  }

  // ── Validate ──────────────────────────────────────────────────────────
  const url = typeof body.url === 'string' ? body.url.trim() : '';
  if (!url) {
    return NextResponse.json({ error: 'url is required.' }, { status: 400 });
  }

  if (!INDEXNOW_KEY) {
    console.warn('[indexnow] INDEXNOW_KEY not set — skipping ping');
    return NextResponse.json({ ok: false, reason: 'INDEXNOW_KEY not configured' });
  }

  if (!PUBLICATION_DOMAIN) {
    return NextResponse.json({ error: 'PUBLICATION_DOMAIN not configured.' }, { status: 500 });
  }

  // ── Ping IndexNow ─────────────────────────────────────────────────────
  const keyLocation = `https://${PUBLICATION_DOMAIN}/${INDEXNOW_KEY}.txt`;

  try {
    const indexnowRes = await fetch(INDEXNOW_ENDPOINT, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body:    JSON.stringify({
        host:        PUBLICATION_DOMAIN,
        key:         INDEXNOW_KEY,
        keyLocation,
        urlList:     [url],
      }),
    });

    // IndexNow returns 200/202 on success; 400 for invalid, 422 for unprocessable
    if (!indexnowRes.ok && indexnowRes.status !== 202) {
      const text = await indexnowRes.text().catch(() => '');
      console.error(`[indexnow] IndexNow responded ${indexnowRes.status}: ${text}`);
      return NextResponse.json(
        { error: `IndexNow returned ${indexnowRes.status}` },
        { status: 502 },
      );
    }

    console.log(`[indexnow] Pinged IndexNow for: ${url} (status ${indexnowRes.status})`);

    return NextResponse.json({
      ok:             true,
      url,
      indexnowStatus: indexnowRes.status,
    });
  } catch (err) {
    console.error('[indexnow] Network error pinging IndexNow:', err);
    return NextResponse.json(
      { error: 'Failed to reach IndexNow. See server logs.' },
      { status: 502 },
    );
  }
}
