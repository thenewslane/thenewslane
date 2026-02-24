/**
 * Dashboard — /
 *
 * Summary cards: topics published today, prediction accuracy %,
 * distribution success rate (7d), total registered users.
 * Runs log table: last 10 pipeline executions from runs_log.
 */

import React from 'react';
import { getServerClient } from '@platform/supabase';
import type { BatchRun }   from '@platform/types';

// ── Data fetching ──────────────────────────────────────────────────────────
async function getDashboardStats(): Promise<
  | { ok: true; topicsToday: number; draftCount: number; totalUsers: number; recentRuns: BatchRun[]; distRate: number | null; predAccuracy: number | null; distTotal: number; predTotal: number; recentDrafts: { id: string; title: string; slug: string; created_at: string }[] }
  | { ok: false; error: string }
> {
  try {
    const supabase = getServerClient();
    const [topicsToday, draftCountRes, totalUsers, recentRuns, distRows, predRows, recentDrafts] = await Promise.all([
    supabase
      .from('trending_topics')
      .select('id', { count: 'exact', head: true })
      .eq('status', 'published')
      .eq('fact_check', 'yes')
      .gte('published_at', new Date(new Date().setHours(0, 0, 0, 0)).toISOString()),

    supabase
      .from('trending_topics')
      .select('id', { count: 'exact', head: true })
      .eq('fact_check', 'no'),

    supabase
      .from('user_profiles')
      .select('id', { count: 'exact', head: true }),

    supabase
      .from('runs_log')
      .select('*')
      .order('started_at', { ascending: false })
      .limit(10),

    supabase
      .from('distribution_log')
      .select('status')
      .gte('created_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()),

    supabase
      .from('viral_predictions')
      .select('tier_assigned, actual_virality_score')
      .not('actual_virality_score', 'is', null)
      .limit(200),

    supabase
      .from('trending_topics')
      .select('id, title, slug, created_at')
      .eq('fact_check', 'no')
      .order('created_at', { ascending: false })
      .limit(5),
  ]);

  // Distribution success rate
  const dist        = (distRows.data ?? []) as { status: string }[];
  const distTotal   = dist.length;
  const distPosted  = dist.filter(d => d.status === 'posted').length;
  const distRate    = distTotal > 0 ? Math.round((distPosted / distTotal) * 100) : null;

  // Prediction accuracy: compare tier_assigned to actual tier derived from actual_virality_score
  const preds     = (predRows.data ?? []) as { tier_assigned: number | null; actual_virality_score: number | null }[];
  const predTotal = preds.length;
  const predCorrect = preds.filter(p => {
    if (!p.tier_assigned || p.actual_virality_score == null) return false;
    const actualTier = p.actual_virality_score >= 0.75 ? 1 : p.actual_virality_score >= 0.45 ? 2 : 3;
    return p.tier_assigned === actualTier;
  }).length;
  const predAccuracy = predTotal > 0 ? Math.round((predCorrect / predTotal) * 100) : null;

    return {
      ok: true as const,
      topicsToday:   topicsToday.count  ?? 0,
      draftCount:    draftCountRes.count ?? 0,
      totalUsers:    totalUsers.count   ?? 0,
      recentRuns:    (recentRuns.data   ?? []) as BatchRun[],
      distRate,
      predAccuracy,
      distTotal,
      predTotal,
      recentDrafts:  (recentDrafts.data ?? []) as { id: string; title: string; slug: string; created_at: string }[],
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, error: message };
  }
}

// ── Sub-components ─────────────────────────────────────────────────────────
function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label:   string;
  value:   string | number;
  sub?:    string;
  accent?: 'green' | 'amber' | 'red';
}) {
  const accentClass =
    accent === 'green' ? 'text-emerald-600' :
    accent === 'amber' ? 'text-amber-600'   :
    accent === 'red'   ? 'text-red-600'     : 'text-slate-900';
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold ${accentClass}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

function RunStatusBadge({ status }: { status: string }) {
  const classes: Record<string, string> = {
    completed: 'bg-emerald-100 text-emerald-700',
    running:   'bg-blue-100 text-blue-700',
    failed:    'bg-red-100 text-red-700',
    partial:   'bg-amber-100 text-amber-700',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${classes[status] ?? 'bg-slate-100 text-slate-600'}`}>
      {status}
    </span>
  );
}

function formatDuration(start: string, end: string | null): string {
  if (!end) return '—';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const s  = Math.round(ms / 1000);
  return s < 60 ? `${s}s` : `${Math.round(s / 60)}m ${s % 60}s`;
}

// ── Page ───────────────────────────────────────────────────────────────────
export default async function DashboardPage() {
  const stats = await getDashboardStats();

  if (!stats.ok) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
          <h2 className="font-semibold text-lg mb-2">Unable to load dashboard</h2>
          <p className="text-sm mb-2">This usually means the server is missing Supabase configuration.</p>
          <p className="text-xs font-mono bg-amber-100/80 p-2 rounded mb-3 break-all">{stats.error}</p>
          <p className="text-sm">In Vercel: Project → Settings → Environment Variables, add <code className="bg-amber-100 px-1 rounded">SUPABASE_URL</code> and <code className="bg-amber-100 px-1 rounded">SUPABASE_SERVICE_KEY</code>.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">theNewslane pipeline overview</p>
      </div>

      {/* ── Stat cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <StatCard
          label="Topics published today"
          value={stats.topicsToday}
          sub="Fact-checked, since midnight UTC"
        />
        <StatCard
          label="Drafts (pending fact-check)"
          value={stats.draftCount}
          sub="fact_check=no"
          accent={stats.draftCount > 0 ? 'amber' : undefined}
        />
        <StatCard
          label="Prediction accuracy"
          value={stats.predAccuracy != null ? `${stats.predAccuracy}%` : 'N/A'}
          sub={stats.predTotal > 0 ? `${stats.predTotal} validated predictions` : 'No data yet'}
          accent={
            stats.predAccuracy == null ? undefined :
            stats.predAccuracy >= 70   ? 'green'   :
            stats.predAccuracy >= 50   ? 'amber'   : 'red'
          }
        />
        <StatCard
          label="Distribution success (7d)"
          value={stats.distRate != null ? `${stats.distRate}%` : 'N/A'}
          sub={stats.distTotal > 0 ? `${stats.distTotal} total posts` : 'No data yet'}
          accent={
            stats.distRate == null ? undefined :
            stats.distRate >= 90   ? 'green'   :
            stats.distRate >= 70   ? 'amber'   : 'red'
          }
        />
        <StatCard
          label="Registered users"
          value={stats.totalUsers.toLocaleString()}
          sub="All time"
        />
      </div>

      {/* ── Recent drafts (pending fact-check) ──────────────────────────── */}
      {stats.recentDrafts.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Recent drafts (pending fact-check)</h2>
            <span className="text-xs text-slate-400">{stats.draftCount} total</span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full admin-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Slug</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {stats.recentDrafts.map(d => (
                  <tr key={d.id}>
                    <td className="font-medium text-slate-900 truncate max-w-xs">{d.title}</td>
                    <td><code className="text-xs text-slate-500">{d.slug}</code></td>
                    <td className="text-slate-500 text-xs whitespace-nowrap">
                      {new Date(d.created_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Runs log ───────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Recent Pipeline Runs</h2>
          <span className="text-xs text-slate-400">Last 10 executions</span>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full admin-table">
            <thead>
              <tr>
                <th>Batch ID</th>
                <th>Status</th>
                <th>Started</th>
                <th>Duration</th>
                <th className="text-right">Collected</th>
                <th className="text-right">Published</th>
                <th className="text-right">Rejected</th>
              </tr>
            </thead>
            <tbody>
              {stats.recentRuns.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center text-slate-400 py-8">
                    No runs recorded yet.
                  </td>
                </tr>
              )}
              {stats.recentRuns.map(run => (
                <tr key={run.id}>
                  <td>
                    <code className="text-xs font-mono text-slate-500">{run.batch_id.slice(0, 16)}…</code>
                  </td>
                  <td><RunStatusBadge status={run.status} /></td>
                  <td className="text-slate-500 text-xs">
                    {new Date(run.started_at).toLocaleString('en-GB', {
                      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                    })}
                  </td>
                  <td className="text-slate-500 text-xs">
                    {formatDuration(run.started_at, run.completed_at)}
                  </td>
                  <td className="text-right">{run.signals_collected}</td>
                  <td className="text-right text-emerald-600 font-medium">{run.topics_published}</td>
                  <td className="text-right text-red-500">{run.topics_rejected}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
