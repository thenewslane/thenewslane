/**
 * Brand Safety — /brand-safety
 *
 * Section 1: Topics that failed brand safety (brand_safety_log where overall_passed=false)
 *            with an Override button to manually approve.
 * Section 2: Editable keyword blocklist from config table (key='keyword_blocklist').
 */

'use client';

import React, { useEffect, useState, useTransition } from 'react';
import { getBrowserClient } from '@platform/supabase';
import { overrideBrandSafety, addBlockedKeyword, deleteBlockedKeyword } from './actions';

// ── Types ──────────────────────────────────────────────────────────────────
interface SafetyRow {
  id:                    string;
  topic_id:              string;
  topic_title:           string;
  topic_slug:            string;
  keyword_check_passed:  boolean;
  blocked_keywords:      string[] | null;
  llama_guard_passed:    boolean;
  llama_guard_score:     number | null;
  haiku_check_passed:    boolean;
  haiku_brand_score:     number | null;
  overall_passed:        boolean;
  created_at:            string;
}

function ScorePill({ score, passed }: { score: number | null; passed: boolean }) {
  const bg    = passed ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700';
  const label = score != null ? (score * 100).toFixed(0) + '%' : passed ? 'Pass' : 'Fail';
  return <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${bg}`}>{label}</span>;
}

// ── Section 1: Failed checks ────────────────────────────────────────────────
function FailedTopicsSection() {
  const [rows,      setRows]      = useState<SafetyRow[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);
  const [toast,     setToast]     = useState<string | null>(null);
  const [actionId,  setActionId]  = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  useEffect(() => {
    const supabase = getBrowserClient();
    supabase
      .from('brand_safety_log')
      .select(`
        id, topic_id, keyword_check_passed, blocked_keywords,
        llama_guard_passed, llama_guard_score,
        haiku_check_passed, haiku_brand_score,
        overall_passed, created_at,
        topic:trending_topics!topic_id(title, slug)
      `)
      .eq('overall_passed', false)
      .order('created_at', { ascending: false })
      .limit(50)
      .then(({ data, error: err }) => {
        if (err) { setError(err.message); setLoading(false); return; }
        const mapped = ((data ?? []) as unknown as {
          id: string; topic_id: string;
          keyword_check_passed: boolean; blocked_keywords: string[] | null;
          llama_guard_passed: boolean; llama_guard_score: number | null;
          haiku_check_passed: boolean; haiku_brand_score: number | null;
          overall_passed: boolean; created_at: string;
          topic: { title: string; slug: string } | null;
        }[]).map(r => ({
          id:                   r.id,
          topic_id:             r.topic_id,
          topic_title:          r.topic?.title ?? 'Unknown',
          topic_slug:           r.topic?.slug  ?? '',
          keyword_check_passed: r.keyword_check_passed,
          blocked_keywords:     r.blocked_keywords,
          llama_guard_passed:   r.llama_guard_passed,
          llama_guard_score:    r.llama_guard_score,
          haiku_check_passed:   r.haiku_check_passed,
          haiku_brand_score:    r.haiku_brand_score,
          overall_passed:       r.overall_passed,
          created_at:           r.created_at,
        }));
        setRows(mapped);
        setLoading(false);
      });
  }, []);

  function handleOverride(row: SafetyRow) {
    setActionId(row.id);
    startTransition(async () => {
      const result = await overrideBrandSafety(row.id, row.topic_id);
      if (result.error) showToast(`Error: ${result.error}`);
      else {
        setRows(s => s.filter(x => x.id !== row.id));
        showToast('Override applied — topic moved to generating.');
      }
      setActionId(null);
    });
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-slate-900 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg">
          {toast}
        </div>
      )}
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-slate-900">Failed Brand Safety Checks</h2>
          <p className="text-xs text-slate-400 mt-0.5">Topics blocked by the automated pipeline</p>
        </div>
        {!loading && (
          <span className="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
            {rows.length} blocked
          </span>
        )}
      </div>
      {loading ? (
        <div className="py-12 text-center text-slate-400 text-sm">Loading…</div>
      ) : error ? (
        <div className="py-12 text-center text-red-500 text-sm">{error}</div>
      ) : rows.length === 0 ? (
        <div className="py-12 text-center text-slate-400 text-sm">No blocked topics.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full admin-table">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Keywords</th>
                <th>Llama Guard</th>
                <th>Claude Haiku</th>
                <th>Blocked At</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.id}>
                  <td>
                    <p className="font-medium text-slate-900 max-w-xs truncate">{row.topic_title}</p>
                    <p className="text-xs text-slate-400 font-mono">{row.topic_slug}</p>
                  </td>
                  <td>
                    <ScorePill score={null} passed={row.keyword_check_passed} />
                    {!row.keyword_check_passed && row.blocked_keywords && row.blocked_keywords.length > 0 && (
                      <p className="text-xs text-slate-400 mt-1">
                        {row.blocked_keywords.slice(0, 3).join(', ')}
                        {row.blocked_keywords.length > 3 && ` +${row.blocked_keywords.length - 3}`}
                      </p>
                    )}
                  </td>
                  <td><ScorePill score={row.llama_guard_score} passed={row.llama_guard_passed} /></td>
                  <td><ScorePill score={row.haiku_brand_score} passed={row.haiku_check_passed} /></td>
                  <td className="text-xs text-slate-500 whitespace-nowrap">
                    {new Date(row.created_at).toLocaleString('en-GB', {
                      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                    })}
                  </td>
                  <td className="text-right">
                    <button
                      onClick={() => handleOverride(row)}
                      disabled={isPending && actionId === row.id}
                      className="px-3 py-1.5 text-xs font-medium bg-amber-500 hover:bg-amber-400 text-white rounded-md disabled:opacity-50 transition-colors"
                    >
                      {isPending && actionId === row.id ? '…' : 'Override'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Section 2: Keyword blocklist ────────────────────────────────────────────
function KeywordBlocklist() {
  const [keywords,  setKeywords]  = useState<string[]>([]);
  const [newKw,     setNewKw]     = useState('');
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);
  const [toast,     setToast]     = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  useEffect(() => {
    const supabase = getBrowserClient();
    (supabase
      .from('config')
      .select('value')
      .eq('key', 'keyword_blocklist')
      .single() as unknown as Promise<{ data: { value: unknown } | null; error: { message: string; code: string } | null }>)
      .then(({ data, error: err }) => {
        if (err && err.code !== 'PGRST116') setError(err.message); // PGRST116 = no row
        setKeywords(Array.isArray(data?.value) ? data.value as string[] : []);
        setLoading(false);
      });
  }, []);

  function handleAdd() {
    const trimmed = newKw.trim().toLowerCase();
    if (!trimmed) return;
    setNewKw('');
    startTransition(async () => {
      const result = await addBlockedKeyword(trimmed);
      if (result.error) showToast(`Error: ${result.error}`);
      else { setKeywords(k => [...k, trimmed]); showToast('Keyword added.'); }
    });
  }

  function handleDelete(kw: string) {
    startTransition(async () => {
      const result = await deleteBlockedKeyword(kw);
      if (result.error) showToast(`Error: ${result.error}`);
      else { setKeywords(k => k.filter(x => x !== kw)); showToast('Keyword removed.'); }
    });
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-slate-900 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg">
          {toast}
        </div>
      )}
      <div className="px-6 py-4 border-b border-slate-100">
        <h2 className="font-semibold text-slate-900">Keyword Blocklist</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Topics containing these keywords are automatically blocked (Stage 1 check).
        </p>
      </div>
      <div className="p-6">
        {/* Add keyword */}
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={newKw}
            onChange={e => setNewKw(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            placeholder="Enter keyword…"
            className="flex-1 px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          />
          <button
            onClick={handleAdd}
            disabled={isPending || !newKw.trim()}
            className="px-4 py-2 bg-red-700 hover:bg-red-600 text-white text-sm font-medium rounded-md disabled:opacity-50 transition-colors"
          >
            Add
          </button>
        </div>

        {error && <p className="text-sm text-red-500 mb-4">{error}</p>}

        {loading ? (
          <p className="text-slate-400 text-sm">Loading blocklist…</p>
        ) : keywords.length === 0 ? (
          <p className="text-slate-400 text-sm">No keywords in blocklist.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {keywords.sort().map(kw => (
              <span
                key={kw}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 text-slate-700 text-sm rounded-full"
              >
                {kw}
                <button
                  onClick={() => handleDelete(kw)}
                  disabled={isPending}
                  className="text-slate-400 hover:text-red-600 transition-colors disabled:opacity-50"
                  aria-label={`Remove ${kw}`}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </span>
            ))}
          </div>
        )}
        <p className="text-xs text-slate-400 mt-4">{keywords.length} keyword{keywords.length !== 1 ? 's' : ''} in blocklist</p>
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────
export default function BrandSafetyPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Brand Safety</h1>
        <p className="text-slate-500 text-sm mt-1">Review blocked topics and manage the keyword blocklist</p>
      </div>
      <FailedTopicsSection />
      <KeywordBlocklist />
    </div>
  );
}
