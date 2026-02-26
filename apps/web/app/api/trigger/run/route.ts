/**
 * GET /api/trigger/run?token=<TRIGGER_TOKEN>&target=5
 *
 * Publicly accessible link that triggers the content agent pipeline.
 * Designed to be opened in a browser — no Bearer header needed.
 *
 * The pipeline will run repeatedly until `target` stories are published
 * (default 5, max 20). Each run follows the full process: collection,
 * viral scoring, brand safety, classification, content generation,
 * media generation, and publishing.
 *
 * Security:
 *   - Token-gated via query parameter (TRIGGER_TOKEN env var)
 *   - Not indexable: X-Robots-Tag: noindex, nofollow
 *   - Already under /api/ which is blocked in robots.txt
 *
 * Env vars:
 *   TRIGGER_TOKEN          — required; the secret token for the URL
 *   RUNNER_WEBHOOK_URL     — URL of the agent webhook server
 *   RUNNER_WEBHOOK_SECRET  — Bearer token for the agent
 */

import { NextRequest, NextResponse } from 'next/server';

const TRIGGER_TOKEN = (process.env.TRIGGER_TOKEN ?? '').trim();
const RUNNER_WEBHOOK_URL = (process.env.RUNNER_WEBHOOK_URL ?? '').trim();
const RUNNER_WEBHOOK_SECRET = (process.env.RUNNER_WEBHOOK_SECRET ?? process.env.CRON_SECRET ?? '').trim();

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET(req: NextRequest) {
  const headers = {
    'X-Robots-Tag': 'noindex, nofollow',
    'Cache-Control': 'no-store, no-cache',
  };

  // Validate token
  const token = req.nextUrl.searchParams.get('token') ?? '';
  if (!TRIGGER_TOKEN || token !== TRIGGER_TOKEN) {
    return NextResponse.json(
      { error: 'Invalid or missing token' },
      { status: 403, headers },
    );
  }

  if (!RUNNER_WEBHOOK_URL) {
    return NextResponse.json(
      { ok: false, error: 'RUNNER_WEBHOOK_URL not configured' },
      { status: 503, headers },
    );
  }

  // Parse target (default 5, clamped 1–20)
  const rawTarget = req.nextUrl.searchParams.get('target') ?? '5';
  const target = Math.max(1, Math.min(20, parseInt(rawTarget, 10) || 5));

  try {
    const reqHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
    if (RUNNER_WEBHOOK_SECRET) {
      reqHeaders['Authorization'] = `Bearer ${RUNNER_WEBHOOK_SECRET}`;
    }

    const res = await fetch(RUNNER_WEBHOOK_URL, {
      method: 'POST',
      headers: reqHeaders,
      body: JSON.stringify({
        source: 'manual-trigger',
        min_publish: target,
        at: new Date().toISOString(),
      }),
      signal: AbortSignal.timeout(55_000),
    });

    if (!res.ok) {
      const body = await res.text().catch(() => '');
      console.error('[trigger/run] Runner responded', res.status, body);
      return NextResponse.json(
        { ok: false, error: `Runner returned ${res.status}` },
        { status: 502, headers },
      );
    }

    const data = await res.json().catch(() => ({}));

    console.log(`[trigger/run] Pipeline triggered — target=${target} stories`);
    return NextResponse.json(
      {
        ok: true,
        triggered: true,
        target,
        message: `Pipeline started. Will run until ${target} stories are published.`,
        runner: data,
      },
      { headers },
    );
  } catch (err) {
    console.error('[trigger/run] Failed to call runner:', err);
    return NextResponse.json(
      { ok: false, error: 'Runner request failed' },
      { status: 502, headers },
    );
  }
}
