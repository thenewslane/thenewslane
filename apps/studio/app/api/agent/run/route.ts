/**
 * POST /api/agent/run
 *
 * Triggers a background agent run for a specific category.
 * The Python process is spawned detached so it outlives this request.
 *
 * Body: { category: string, max_topics?: number }
 *
 * Returns 202 immediately with { ok: true, batch_id, pid }
 */

import { NextRequest, NextResponse } from 'next/server';
import { spawn }                     from 'child_process';
import { existsSync }                from 'fs';
import path                          from 'path';
import { randomBytes }               from 'crypto';

// Resolve agent directory relative to the studio app root
const AGENT_DIR  = path.resolve(process.cwd(), '../agent');
const MAIN_PY    = path.join(AGENT_DIR, 'main.py');

// Prefer the venv python if it exists, fall back to system python3/python
function resolvePython(): string {
  const venvPy = path.join(AGENT_DIR, '.venv', 'bin', 'python');
  if (existsSync(venvPy)) return venvPy;
  return 'python3';
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json() as { category?: string; max_topics?: number };
    const { category, max_topics } = body;

    if (!category) {
      return NextResponse.json({ ok: false, error: 'category is required' }, { status: 400 });
    }

    // Validate max_topics range
    const limit = max_topics != null
      ? Math.max(1, Math.min(10, Math.round(max_topics)))
      : null;

    const batchId = `batch_cms_${randomBytes(6).toString('hex')}`;
    const python  = resolvePython();

    const args = [
      MAIN_PY,
      `--category=${category}`,
    ];
    if (limit != null) args.push(`--max-topics=${limit}`);

    // Spawn detached — process keeps running after this request closes
    const child = spawn(python, args, {
      cwd:      AGENT_DIR,
      detached: true,
      stdio:    'ignore',
      env: {
        ...process.env,
        BATCH_ID:     batchId,
        PYTHONPATH:   AGENT_DIR,
      },
    });

    child.unref(); // allow this process to exit without waiting for child

    return NextResponse.json(
      { ok: true, batch_id: batchId, pid: child.pid, category, max_topics: limit },
      { status: 202 },
    );
  } catch (err: any) {
    console.error('[api/agent/run]', err);
    return NextResponse.json({ ok: false, error: err.message }, { status: 500 });
  }
}
