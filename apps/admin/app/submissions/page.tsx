/**
 * Submissions — /submissions
 *
 * Table of pending user_submissions with Approve / Reject actions.
 * Rejection sends an email via Resend.
 */

'use client';

import React, { useEffect, useState, useTransition } from 'react';
import { getBrowserClient }    from '@platform/supabase';
import { approveSubmission, rejectSubmission } from './actions';

interface SubmissionRow {
  id:           string;
  title:        string;
  description:  string | null;
  url:          string | null;
  created_at:   string;
  display_name: string | null;
  email:        string;
  user_id:      string;
}

function StatusBadge({ label, color }: { label: string; color: string }) {
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {label}
    </span>
  );
}

function RejectModal({
  submission,
  onClose,
  onConfirm,
}: {
  submission: SubmissionRow;
  onClose:   () => void;
  onConfirm: (reason: string) => void;
}) {
  const [reason, setReason] = useState('');
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
        <h3 className="font-semibold text-slate-900 mb-1">Reject Submission</h3>
        <p className="text-sm text-slate-500 mb-4">
          <span className="font-medium text-slate-700">{submission.title}</span>
          {' '}by {submission.display_name ?? submission.email}
        </p>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">
          Rejection reason <span className="text-slate-400">(optional — sent to submitter)</span>
        </label>
        <textarea
          rows={3}
          value={reason}
          onChange={e => setReason(e.target.value)}
          className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-red-500"
          placeholder="e.g. Topic doesn't meet our trend threshold at this time."
        />
        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reason)}
            className="px-4 py-2 text-sm bg-red-700 text-white rounded-md hover:bg-red-600 transition-colors"
          >
            Reject &amp; Notify
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SubmissionsPage() {
  const [submissions, setSubmissions] = useState<SubmissionRow[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<SubmissionRow | null>(null);
  const [isPending,  startTransition]  = useTransition();
  const [actionId,   setActionId]      = useState<string | null>(null);
  const [toast,      setToast]         = useState<string | null>(null);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  useEffect(() => {
    const supabase = getBrowserClient();
    supabase
      .from('user_submissions')
      .select(`
        id, title, description, url, created_at, user_id,
        user:user_profiles!user_id(display_name, email)
      `)
      .eq('status', 'pending')
      .order('created_at', { ascending: false })
      .then(({ data, error: err }) => {
        if (err) { setError(err.message); setLoading(false); return; }
        // Flatten the joined user object
        const rows = ((data ?? []) as unknown as {
          id: string; title: string; description: string | null; url: string | null;
          created_at: string; user_id: string;
          user: { display_name: string | null; email: string } | null;
        }[]).map(r => ({
          id:           r.id,
          title:        r.title,
          description:  r.description,
          url:          r.url,
          created_at:   r.created_at,
          user_id:      r.user_id,
          display_name: r.user?.display_name ?? null,
          email:        r.user?.email ?? '',
        }));
        setSubmissions(rows);
        setLoading(false);
      });
  }, []);

  function handleApprove(row: SubmissionRow) {
    setActionId(row.id);
    startTransition(async () => {
      const result = await approveSubmission(row.id);
      if (result.error) { showToast(`Error: ${result.error}`); }
      else {
        setSubmissions(s => s.filter(x => x.id !== row.id));
        showToast('Submission approved.');
      }
      setActionId(null);
    });
  }

  function handleRejectConfirm(reason: string) {
    if (!rejectTarget) return;
    const target = rejectTarget;
    setRejectTarget(null);
    setActionId(target.id);
    startTransition(async () => {
      const result = await rejectSubmission(target.id, reason, target.email, target.title);
      if (result.error) { showToast(`Error: ${result.error}`); }
      else {
        setSubmissions(s => s.filter(x => x.id !== target.id));
        showToast('Submission rejected and submitter notified.');
      }
      setActionId(null);
    });
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-slate-900 text-white text-sm px-4 py-2.5 rounded-lg shadow-lg">
          {toast}
        </div>
      )}

      {/* Reject modal */}
      {rejectTarget && (
        <RejectModal
          submission={rejectTarget}
          onClose={() => setRejectTarget(null)}
          onConfirm={handleRejectConfirm}
        />
      )}

      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Submissions</h1>
          <p className="text-slate-500 text-sm mt-1">Pending user-submitted topic suggestions</p>
        </div>
        {!loading && (
          <span className="text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
            {submissions.length} pending
          </span>
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-slate-400 text-sm">
            Loading submissions…
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16 text-red-500 text-sm">{error}</div>
        ) : submissions.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-slate-400 text-sm">
            No pending submissions.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full admin-table">
              <thead>
                <tr>
                  <th>Topic Title</th>
                  <th>Submitted By</th>
                  <th>Submitted At</th>
                  <th>Source URL</th>
                  <th>Brand Safety</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map(row => (
                  <tr key={row.id}>
                    <td>
                      <p className="font-medium text-slate-900 truncate max-w-xs">{row.title}</p>
                      {row.description && (
                        <p className="text-xs text-slate-400 mt-0.5 truncate max-w-xs">{row.description}</p>
                      )}
                    </td>
                    <td>
                      <p className="font-medium">{row.display_name ?? '—'}</p>
                      <p className="text-xs text-slate-400">{row.email}</p>
                    </td>
                    <td className="text-slate-500 text-xs whitespace-nowrap">
                      {new Date(row.created_at).toLocaleString('en-GB', {
                        day: '2-digit', month: 'short', year: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </td>
                    <td>
                      {row.url ? (
                        <a
                          href={row.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline text-xs truncate block max-w-[160px]"
                        >
                          {row.url}
                        </a>
                      ) : (
                        <span className="text-slate-400 text-xs">—</span>
                      )}
                    </td>
                    <td>
                      <StatusBadge label="Not reviewed" color="bg-slate-100 text-slate-500" />
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleApprove(row)}
                          disabled={isPending && actionId === row.id}
                          className="px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white rounded-md disabled:opacity-50 transition-colors"
                        >
                          {isPending && actionId === row.id ? '…' : 'Approve'}
                        </button>
                        <button
                          onClick={() => setRejectTarget(row)}
                          disabled={isPending && actionId === row.id}
                          className="px-3 py-1.5 text-xs font-medium bg-red-700 hover:bg-red-600 text-white rounded-md disabled:opacity-50 transition-colors"
                        >
                          Reject
                        </button>
                      </div>
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
