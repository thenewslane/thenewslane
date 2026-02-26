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
/** Keep under typical proxy timeouts (e.g. Cloudflare 100s, Vercel 60s) so we respond before gateway timeout. */
export const maxDuration = 15;

/** How long to wait for the runner to respond before treating as "sent but unconfirmed". */
const RUNNER_FETCH_TIMEOUT_MS = 12_000;

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
      {
        ok: false,
        error: 'RUNNER_WEBHOOK_URL not configured',
        hint: 'Set RUNNER_WEBHOOK_URL in your deployment env (e.g. Vercel) to the agent webhook URL, e.g. https://your-agent-host/run',
      },
      { status: 503, headers },
    );
  }

  // Parse target (default 5, clamped 1–20)
  const rawTarget = req.nextUrl.searchParams.get('target') ?? '5';
  const target = Math.max(1, Math.min(20, parseInt(rawTarget, 10) || 5));

  const reqHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
  if (RUNNER_WEBHOOK_SECRET) {
    reqHeaders['Authorization'] = `Bearer ${RUNNER_WEBHOOK_SECRET}`;
  }

  const payload = {
    source: 'manual-trigger',
    min_publish: target,
    at: new Date().toISOString(),
  };

  try {
    const res = await fetch(RUNNER_WEBHOOK_URL, {
      method: 'POST',
      headers: reqHeaders,
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(RUNNER_FETCH_TIMEOUT_MS),
    });

    if (!res.ok) {
      const body = await res.text().catch(() => '');
      console.error('[trigger/run] Runner responded', res.status, body);
      return NextResponse.json(
        {
          ok: false,
          error: `Runner returned ${res.status}`,
          status: res.status,
        },
        { status: 503, headers },
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
    const isTimeout = err instanceof Error && err.name === 'TimeoutError';
    console.error('[trigger/run] Failed to call runner:', err);

    // Timeout or network error: return 200 with "sent but unconfirmed" so we don't surface 502 to Cloudflare.
    // The POST may have reached the runner; pipeline might still be running.
    if (isTimeout) {
      return NextResponse.json(
        {
          ok: true,
          triggered: true,
          target,
          message: `Trigger sent. Runner did not respond within ${RUNNER_FETCH_TIMEOUT_MS / 1000}s — pipeline may still be running. Check runner logs.`,
          unconfirmed: true,
        },
        { headers },
      );
    }

    // Connection refused, DNS failure, etc. — service unavailable, not bad gateway
    return NextResponse.json(
      {
        ok: false,
        error: 'Runner unreachable',
        hint: 'RUNNER_WEBHOOK_URL must be a public URL (not localhost). Start the agent with: python main.py --webhook. See docs/trigger-and-runner-setup.md',
      },
      { status: 503, headers },
    );
  }
}
