'use client';

import React, { useState, useTransition } from 'react';
import { getBrowserClient } from '@platform/supabase';

export interface BrandColors {
  primary:    string;
  secondary:  string;
  accent:     string;
  link:       string;
  viralTier1: string;
}

interface ThemeEditorProps {
  initialColors: BrandColors;
}

const COLOR_DEFS: { key: keyof BrandColors; label: string; description: string }[] = [
  { key: 'primary',    label: 'Primary',         description: 'Brand red — used for CTAs, highlights, active states' },
  { key: 'secondary',  label: 'Secondary',        description: 'Deep navy — used for headings and secondary UI' },
  { key: 'accent',     label: 'Accent',           description: 'Warm orange — used for special callouts' },
  { key: 'link',       label: 'Link Color',       description: 'Accessible blue — used for all hyperlinks' },
  { key: 'viralTier1', label: 'Viral Tier 1',     description: 'Hot trend indicator color' },
];

// ── Mock TopicCard preview ─────────────────────────────────────────────────
function MockTopicCard({ colors }: { colors: BrandColors }) {
  return (
    <div
      style={{
        background:   '#ffffff',
        border:       '1px solid #e2e8f0',
        borderRadius: '12px',
        overflow:     'hidden',
        maxWidth:     '320px',
        fontFamily:   'system-ui, sans-serif',
        boxShadow:    '0 1px 4px rgba(0,0,0,0.08)',
      }}
    >
      {/* Thumbnail placeholder */}
      <div
        style={{
          height:          '160px',
          background:      `linear-gradient(135deg, ${colors.primary}22, ${colors.secondary}22)`,
          display:         'flex',
          alignItems:      'center',
          justifyContent:  'center',
          position:        'relative',
        }}
      >
        <div
          style={{
            position:    'absolute',
            top:         8,
            left:        8,
            background:  colors.viralTier1,
            color:       '#fff',
            fontSize:    '11px',
            fontWeight:  700,
            padding:     '2px 8px',
            borderRadius:'99px',
            letterSpacing: '0.05em',
          }}
        >
          TIER 1 HOT
        </div>
        <svg width="40" height="40" viewBox="0 0 24 24" fill={colors.secondary} opacity={0.3} aria-hidden>
          <rect x="3" y="5" width="18" height="14" rx="2"/>
          <polygon points="10 9 16 12 10 15"/>
        </svg>
      </div>
      {/* Content */}
      <div style={{ padding: '12px 14px' }}>
        <p style={{ fontSize: '11px', fontWeight: 600, color: colors.primary, textTransform: 'uppercase', letterSpacing: '0.06em', margin: '0 0 6px' }}>
          Technology
        </p>
        <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#1e293b', margin: '0 0 8px', lineHeight: 1.35 }}>
          The new AI model everyone is talking about
        </h3>
        <p style={{ fontSize: '12px', color: '#64748b', margin: '0 0 10px', lineHeight: 1.5 }}>
          A breakthrough model is reshaping how developers think about AI-assisted workflows…
        </p>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <a href="#" style={{ fontSize: '12px', color: colors.link, fontWeight: 600, textDecoration: 'none' }}>
            Read more →
          </a>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>2 hours ago</span>
        </div>
      </div>
      {/* Bottom bar */}
      <div
        style={{
          borderTop:    '1px solid #f1f5f9',
          padding:      '8px 14px',
          display:      'flex',
          alignItems:   'center',
          gap:          '6px',
          background:   '#fafafa',
        }}
      >
        <div style={{ width: 20, height: 20, borderRadius: '50%', background: colors.secondary, opacity: 0.2 }} />
        <span style={{ fontSize: '11px', color: '#64748b' }}>theNewslane</span>
        <div
          style={{
            marginLeft:  'auto',
            background:  colors.accent,
            color:       '#fff',
            fontSize:    '10px',
            fontWeight:  700,
            padding:     '2px 7px',
            borderRadius:'99px',
          }}
        >
          TRENDING
        </div>
      </div>
    </div>
  );
}

export function ThemeEditor({ initialColors }: ThemeEditorProps) {
  const [colors,     setColors]     = useState<BrandColors>(initialColors);
  const [saved,      setSaved]      = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [isPending,  startTransition] = useTransition();

  const VERCEL_DEPLOY_HOOK = process.env.NEXT_PUBLIC_VERCEL_DEPLOY_HOOK ?? '';

  function handleColorChange(key: keyof BrandColors, value: string) {
    setColors(c => ({ ...c, [key]: value }));
    setSaved(false);
  }

  function handleSave() {
    setError(null);
    startTransition(async () => {
      try {
        // 1. Persist colors to Supabase config table
        const supabase = getBrowserClient();
        const { error: dbError } = await supabase
          .from('config')
          .upsert({
            key:         'brand_colors',
            value:       colors,
            description: 'Brand color overrides set via admin theme editor',
          } as never, { onConflict: 'key' });

        if (dbError) throw new Error(dbError.message);

        // 2. Trigger Vercel redeploy (if webhook configured)
        if (VERCEL_DEPLOY_HOOK) {
          const hookRes = await fetch(VERCEL_DEPLOY_HOOK, { method: 'POST' });
          if (!hookRes.ok) console.warn('[theme] Vercel deploy hook failed:', hookRes.status);
        }

        setSaved(true);
        setTimeout(() => setSaved(false), 4000);
      } catch (e) {
        setError((e as Error).message);
      }
    });
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* ── Editor ──────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h2 className="font-semibold text-slate-900 mb-5">Brand Colors</h2>

        <div className="space-y-5">
          {COLOR_DEFS.map(({ key, label, description }) => (
            <div key={key} className="flex items-center gap-4">
              <div className="relative flex-shrink-0">
                <input
                  type="color"
                  value={colors[key]}
                  onChange={e => handleColorChange(key, e.target.value)}
                  className="w-10 h-10 rounded-md border border-slate-300 cursor-pointer p-0.5"
                  title={`Pick ${label} color`}
                />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-800">{label}</span>
                  <code className="text-xs text-slate-400 font-mono">{colors[key]}</code>
                </div>
                <p className="text-xs text-slate-400 truncate">{description}</p>
              </div>
              <input
                type="text"
                value={colors[key]}
                onChange={e => {
                  const v = e.target.value;
                  if (/^#[0-9A-Fa-f]{0,6}$/.test(v)) handleColorChange(key, v);
                }}
                className="w-24 px-2 py-1 border border-slate-300 rounded text-xs font-mono focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>
          ))}
        </div>

        {error && (
          <p className="mt-4 text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{error}</p>
        )}

        <div className="mt-6 flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={isPending}
            className="px-5 py-2.5 bg-red-700 hover:bg-red-600 text-white text-sm font-semibold rounded-md disabled:opacity-50 transition-colors"
          >
            {isPending ? 'Saving…' : 'Save & Redeploy'}
          </button>
          {saved && (
            <span className="text-sm text-emerald-600 font-medium">
              ✓ Saved — Vercel redeploy triggered
            </span>
          )}
        </div>

        {VERCEL_DEPLOY_HOOK ? null : (
          <p className="mt-3 text-xs text-slate-400">
            Add <code className="bg-slate-100 px-1 rounded">NEXT_PUBLIC_VERCEL_DEPLOY_HOOK</code> to
            trigger automatic redeploy on save.
          </p>
        )}
      </div>

      {/* ── Preview ──────────────────────────────────────────────────── */}
      <div className="bg-slate-100 rounded-xl border border-slate-200 p-6 flex flex-col items-center justify-center gap-4">
        <h2 className="font-semibold text-slate-700 self-start text-sm uppercase tracking-wider">
          Live Preview
        </h2>
        <MockTopicCard colors={colors} />
        <p className="text-xs text-slate-400 text-center">
          Preview updates live as you change colors.<br />
          Actual token update requires a redeploy.
        </p>
      </div>
    </div>
  );
}
