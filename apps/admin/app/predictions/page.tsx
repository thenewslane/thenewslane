/**
 * Predictions — /predictions
 *
 * Line chart: predicted weighted_score vs actual_virality_score over last 30 days.
 * Accuracy % card.
 * Table: recent predictions with tier_assigned vs derived actual tier.
 */

import React from 'react';
import dynamic        from 'next/dynamic';
import { getServerClient } from '@platform/supabase';
import type { ChartPoint } from './_PredictionsChart';
import type { ViralPrediction } from '@platform/types';

const PredictionsChart = dynamic(
  () => import('./_PredictionsChart').then(m => m.PredictionsChart),
  { ssr: false, loading: () => <div className="h-[300px] flex items-center justify-center text-slate-400 text-sm">Loading chart…</div> },
);

// ── Helpers ────────────────────────────────────────────────────────────────
function tierFromScore(score: number): 1 | 2 | 3 {
  return score >= 0.75 ? 1 : score >= 0.45 ? 2 : 3;
}

function tierLabel(tier: 1 | 2 | 3 | null): string {
  return tier === 1 ? 'Tier 1 – Hot' : tier === 2 ? 'Tier 2 – Trending' : tier === 3 ? 'Tier 3 – Emerging' : '—';
}

function tierColor(tier: 1 | 2 | 3 | null): string {
  return tier === 1 ? 'bg-red-100 text-red-700' :
         tier === 2 ? 'bg-amber-100 text-amber-700' :
         tier === 3 ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500';
}

// ── Data ───────────────────────────────────────────────────────────────────
async function getPredictionData() {
  const supabase  = getServerClient();
  const since30d  = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

  const { data, error } = await supabase
    .from('viral_predictions')
    .select('id, weighted_score, actual_virality_score, tier_assigned, created_at, actual_virality_updated_at')
    .gte('created_at', since30d)
    .order('created_at', { ascending: true });

  if (error) throw new Error(error.message);

  const rows = (data ?? []) as Pick<
    ViralPrediction,
    'id' | 'weighted_score' | 'actual_virality_score' | 'tier_assigned' | 'created_at' | 'actual_virality_updated_at'
  >[];

  // Build chart data: one point per day (average predicted & actual)
  const byDay = new Map<string, { preds: number[]; actuals: number[] }>();
  for (const r of rows) {
    const day = r.created_at.slice(0, 10);
    const existing = byDay.get(day) ?? { preds: [], actuals: [] };
    existing.preds.push(r.weighted_score);
    if (r.actual_virality_score != null) existing.actuals.push(r.actual_virality_score);
    byDay.set(day, existing);
  }

  const chartData: ChartPoint[] = Array.from(byDay.entries()).map(([day, v]) => ({
    date:      new Date(day).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }),
    predicted: v.preds.reduce((a, b) => a + b, 0) / v.preds.length,
    actual:    v.actuals.length > 0 ? v.actuals.reduce((a, b) => a + b, 0) / v.actuals.length : null,
  }));

  // Accuracy calculation (rows with actual data only)
  const validated = rows.filter(r => r.actual_virality_score != null && r.tier_assigned != null);
  const correct   = validated.filter(r => r.tier_assigned === tierFromScore(r.actual_virality_score!));
  const accuracy  = validated.length > 0 ? Math.round((correct.length / validated.length) * 100) : null;

  // Recent predictions table (last 50 validated)
  const recentTable = rows
    .filter(r => r.actual_virality_score != null)
    .slice(-50)
    .reverse();

  return { chartData, accuracy, totalValidated: validated.length, recentTable };
}

// ── Page ───────────────────────────────────────────────────────────────────
export default async function PredictionsPage() {
  let result: Awaited<ReturnType<typeof getPredictionData>> | null = null;
  let fetchError: string | null = null;

  try {
    result = await getPredictionData();
  } catch (e) {
    fetchError = (e as Error).message;
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Predictions</h1>
        <p className="text-slate-500 text-sm mt-1">Viral score model performance over the last 30 days</p>
      </div>

      {fetchError ? (
        <div className="bg-red-50 text-red-700 rounded-lg p-4 text-sm">{fetchError}</div>
      ) : result == null ? null : (
        <>
          {/* ── Accuracy card ─────────────────────────────────────────── */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Tier Accuracy</p>
              <p className={`text-3xl font-bold ${
                result.accuracy == null ? 'text-slate-400' :
                result.accuracy >= 70   ? 'text-emerald-600' :
                result.accuracy >= 50   ? 'text-amber-600' : 'text-red-600'
              }`}>
                {result.accuracy != null ? `${result.accuracy}%` : 'N/A'}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {result.totalValidated} validated predictions
              </p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 sm:col-span-2 flex items-center">
              <p className="text-xs text-slate-500 leading-relaxed">
                Accuracy measures whether the <strong>predicted tier</strong> (Tier 1/2/3) matched the
                <strong> actual tier</strong> derived from the observed virality score collected one week
                after publication. A score ≥ 0.75 = Tier 1, ≥ 0.45 = Tier 2, below = Tier 3.
              </p>
            </div>
          </div>

          {/* ── Chart ─────────────────────────────────────────────────── */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-8">
            <h2 className="font-semibold text-slate-900 mb-4">
              Predicted vs Actual Score (daily average)
            </h2>
            <PredictionsChart data={result.chartData} />
          </div>

          {/* ── Table ─────────────────────────────────────────────────── */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-900">Recent Validated Predictions</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full admin-table">
                <thead>
                  <tr>
                    <th>Created</th>
                    <th>Predicted Score</th>
                    <th>Actual Score</th>
                    <th>Predicted Tier</th>
                    <th>Actual Tier</th>
                    <th>Correct?</th>
                  </tr>
                </thead>
                <tbody>
                  {result.recentTable.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center text-slate-400 py-8">
                        No validated predictions yet.
                      </td>
                    </tr>
                  ) : result.recentTable.map(row => {
                    const actualTier   = tierFromScore(row.actual_virality_score!);
                    const isCorrect    = row.tier_assigned === actualTier;
                    return (
                      <tr key={row.id}>
                        <td className="text-xs text-slate-500 whitespace-nowrap">
                          {new Date(row.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: '2-digit' })}
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-slate-100 rounded-full h-1.5 w-20">
                              <div
                                className="bg-red-700 h-1.5 rounded-full"
                                style={{ width: `${Math.min(100, row.weighted_score * 100)}%` }}
                              />
                            </div>
                            <span className="text-xs font-mono text-slate-600 w-10 text-right">
                              {(row.weighted_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className="text-xs font-mono text-slate-600">
                            {(row.actual_virality_score! * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td>
                          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${tierColor(row.tier_assigned)}`}>
                            {tierLabel(row.tier_assigned)}
                          </span>
                        </td>
                        <td>
                          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${tierColor(actualTier)}`}>
                            {tierLabel(actualTier)}
                          </span>
                        </td>
                        <td>
                          <span className={`text-sm ${isCorrect ? 'text-emerald-600' : 'text-red-500'}`}>
                            {isCorrect ? '✓' : '✗'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
