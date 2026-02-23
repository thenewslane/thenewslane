/**
 * GET /api/cron/run-pipeline
 *
 * Called by Vercel Cron (or any scheduler) to trigger the content pipeline.
 * If RUNNER_WEBHOOK_URL is set, this route forwards the request there so your
 * agent (e.g. python main.py --schedule or a small HTTP server) can run the pipeline.
 *
 * Security: Vercel Cron sends Authorization: Bearer <CRON_SECRET>. Validate that
 * so only your cron can trigger the pipeline.
 *
 * Env vars (Vercel):
 *   CRON_SECRET         — required; must match the bearer token from the cron
 *   RUNNER_WEBHOOK_URL  — optional; URL to POST to trigger the agent (e.g. Railway/Render)
 *
 * If RUNNER_WEBHOOK_URL is not set, the route still returns 200 (cron stays green)
 * but does not trigger any runner — run the agent separately (e.g. python main.py --schedule).
 */

import { NextRequest, NextResponse } from 'next/server';

const CRON_SECRET = process.env.CRON_SECRET ?? '';
const RUNNER_WEBHOOK_URL = (process.env.RUNNER_WEBHOOK_URL ?? '').trim();

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET(req: NextRequest) {
  const auth = req.headers.get('authorization');
  const token = auth?.startsWith('Bearer ') ? auth.slice(7) : '';

  if (!CRON_SECRET || token !== CRON_SECRET) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 });
  }

  if (!RUNNER_WEBHOOK_URL) {
    console.log('[cron/run-pipeline] No RUNNER_WEBHOOK_URL — cron ok, pipeline not triggered');
    return NextResponse.json({
      ok: true,
      message: 'Cron received. Set RUNNER_WEBHOOK_URL to trigger the pipeline.',
    });
  }

  try {
    const res = await fetch(RUNNER_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: 'vercel-cron', at: new Date().toISOString() }),
      signal: AbortSignal.timeout(55_000),
    });

    if (!res.ok) {
      console.error('[cron/run-pipeline] Runner responded', res.status, await res.text());
      return NextResponse.json(
        { ok: false, error: `Runner returned ${res.status}` },
        { status: 502 },
      );
    }

    console.log('[cron/run-pipeline] Pipeline trigger sent to runner');
    return NextResponse.json({ ok: true, triggered: true });
  } catch (err) {
    console.error('[cron/run-pipeline] Failed to call runner:', err);
    return NextResponse.json(
      { ok: false, error: 'Runner request failed' },
      { status: 502 },
    );
  }
}
