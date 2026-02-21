/**
 * Distribution — /distribution
 *
 * Table of distribution_log entries.
 * Filterable by platform and status.
 * Retry button for failed entries.
 */

'use client';

import React, { useEffect, useState, useTransition } from 'react';
import { getBrowserClient } from '@platform/supabase';
import { retryDistribution } from './actions';
import type { DistributionPlatform, DistributionStatus } from '@platform/types';

interface DistRow {
  id:               string;
  topic_id:         string;
  topic_title:      string;
  platform:         DistributionPlatform;
  status:           DistributionStatus;
  platform_url:     string | null;
  platform_post_id: string | null;
  error_message:    string | null;
  retry_count:      number;
  posted_at:        string | null;
  created_at:       string;
}

const PLATFORMS: { value: string; label: string }[] = [
  { value: '',          label: 'All Platforms'  },
  { value: 'facebook',  label: 'Facebook'       },
  { value: 'instagram', label: 'Instagram'      },
  { value: 'twitter',   label: 'X / Twitter'    },
  { value: 'youtube',   label: 'YouTube'        },
];

const STATUSES: { value: string; label: string }[] = [
  { value: '',        label: 'All Statuses' },
  { value: 'posted',  label: 'Posted'       },
  { value: 'pending', label: 'Pending'      },
  { value: 'failed',  label: 'Failed'       },
  { value: 'skipped', label: 'Skipped'      },
];

function StatusBadge({ status }: { status: DistributionStatus }) {
  const classes: Record<DistributionStatus, string> = {
    posted:  'bg-emerald-100 text-emerald-700',
    pending: 'bg-blue-100 text-blue-700',
    failed:  'bg-red-100 text-red-700',
    skipped: 'bg-slate-100 text-slate-500',
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${classes[status]}`}>
      {status}
    </span>
  );
}

function PlatformBadge({ platform }: { platform: DistributionPlatform }) {
  const labels: Record<DistributionPlatform, string> = {
    facebook:  'FB',
    instagram: 'IG',
    twitter:   'X',
    youtube:   'YT',
  };
  const colors: Record<DistributionPlatform, string> = {
    facebook:  'bg-blue-600',
    instagram: 'bg-pink-600',
    twitter:   'bg-slate-700',
    youtube:   'bg-red-600',
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-bold text-white ${colors[platform]}`}>
      {labels[platform]}
    </span>
  );
}

export default function DistributionPage() {
  const [rows,        setRows]        = useState<DistRow[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);
  const [platform,    setPlatform]    = useState('');
  const [status,      setStatus]      = useState('');
  const [toast,       setToast]       = useState<string | null>(null);
  const [actionId,    setActionId]    = useState<string | null>(null);
  const [isPending,   startTransition] = useTransition();

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  useEffect(() => {
    setLoading(true);
    const supabase = getBrowserClient();

    let query = supabase
      .from('distribution_log')
      .select(`
        id, topic_id, platform, status, platform_url, platform_post_id,
        error_message, retry_count, posted_at, created_at,
        topic:trending_topics!topic_id(title)
      `)
      .order('created_at', { ascending: false })
      .limit(100);

    if (platform) query = query.eq('platform', platform);
    if (status)   query = query.eq('status',   status);

    query.then(({ data, error: err }) => {
      if (err) { setError(err.message); setLoading(false); return; }
      const mapped = ((data ?? []) as unknown as {
        id: string; topic_id: string; platform: DistributionPlatform;
        status: DistributionStatus; platform_url: string | null;
        platform_post_id: string | null; error_message: string | null;
        retry_count: number; posted_at: string | null; created_at: string;
        topic: { title: string } | null;
      }[]).map(r => ({
        id:               r.id,
        topic_id:         r.topic_id,
        topic_title:      r.topic?.title ?? 'Unknown topic',
        platform:         r.platform,
        status:           r.status,
        platform_url:     r.platform_url,
        platform_post_id: r.platform_post_id,
        error_message:    r.error_message,
        retry_count:      r.retry_count,
        posted_at:        r.posted_at,
        created_at:       r.created_at,
      }));
      setRows(mapped);
      setLoading(false);
    });
  }, [platform, status]);

  function handleRetry(row: DistRow) {
    setActionId(row.id);
    startTransition(async () => {
      const result = await retryDistribution(row.id);
      if (result.error) showToast(`Error: ${result.error}`);
      else {
        setRows(r => r.map(x => x.id === row.id ? { ...x, status: 'pending', error_message: null } : x));
        showToast('Entry queued for retry.');
      }
      setActionId(null);
    });
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-slate-900 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg">
          {toast}
        </div>
      )}

      <div className="mb-8 flex flex-wrap items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Distribution</h1>
          <p className="text-slate-500 text-sm mt-1">Social media post log</p>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <select
            value={platform}
            onChange={e => setPlatform(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {PLATFORMS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
          <select
            value={status}
            onChange={e => setStatus(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-slate-400 text-sm">Loading…</div>
        ) : error ? (
          <div className="py-16 text-center text-red-500 text-sm">{error}</div>
        ) : rows.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-sm">No entries matching the current filter.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full admin-table">
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Platform</th>
                  <th>Status</th>
                  <th>Posted At</th>
                  <th>Retries</th>
                  <th>Error</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(row => (
                  <tr key={row.id}>
                    <td>
                      <p className="font-medium max-w-xs truncate">{row.topic_title}</p>
                    </td>
                    <td><PlatformBadge platform={row.platform} /></td>
                    <td><StatusBadge status={row.status} /></td>
                    <td className="text-xs text-slate-500 whitespace-nowrap">
                      {row.posted_at
                        ? new Date(row.posted_at).toLocaleString('en-GB', {
                            day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                          })
                        : '—'}
                    </td>
                    <td className="text-center">
                      {row.retry_count > 0 ? (
                        <span className="text-amber-600 font-medium text-xs">{row.retry_count}</span>
                      ) : (
                        <span className="text-slate-400 text-xs">0</span>
                      )}
                    </td>
                    <td>
                      {row.error_message ? (
                        <p className="text-xs text-red-500 max-w-[200px] truncate" title={row.error_message}>
                          {row.error_message}
                        </p>
                      ) : (
                        <span className="text-slate-300 text-xs">—</span>
                      )}
                    </td>
                    <td className="text-right">
                      {row.status === 'failed' && (
                        <button
                          onClick={() => handleRetry(row)}
                          disabled={isPending && actionId === row.id}
                          className="px-3 py-1.5 text-xs font-medium bg-amber-500 hover:bg-amber-400 text-white rounded-md disabled:opacity-50 transition-colors"
                        >
                          {isPending && actionId === row.id ? '…' : 'Retry'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
