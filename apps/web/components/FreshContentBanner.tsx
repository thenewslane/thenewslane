'use client';

/**
 * FreshContentBanner
 *
 * Polls Supabase every 60 s for articles published after the baseline
 * timestamp captured when the page first loaded.
 *
 * When new stories are found:
 *   1. A sticky top banner slides in with the count.
 *   2. A 10-second countdown begins — auto-loads when it reaches zero.
 *   3. The user can click "Load now" to refresh immediately, or "×" to
 *      dismiss and cancel the countdown.
 *
 * Props:
 *   latestPublishedAt — ISO string of the newest topic visible on page load
 *   onRefresh         — called to reload page 1 of the feed
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { getBrowserClient } from '@platform/supabase';

interface FreshContentBannerProps {
  latestPublishedAt: string | null;
  onRefresh: () => void;
}

const POLL_INTERVAL_MS  = 60_000; // check every 60 s
const AUTO_LOAD_SECS    = 10;     // auto-load countdown

export function FreshContentBanner({ latestPublishedAt, onRefresh }: FreshContentBannerProps) {
  const [newCount,   setNewCount]   = useState(0);
  const [visible,    setVisible]    = useState(false);
  const [countdown,  setCountdown]  = useState(AUTO_LOAD_SECS);
  const baselineRef  = useRef<string | null>(latestPublishedAt);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Stop the countdown ────────────────────────────────────────────────────
  const clearCountdown = useCallback(() => {
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
  }, []);

  // ── Trigger auto-load countdown ───────────────────────────────────────────
  const startCountdown = useCallback((onZero: () => void) => {
    clearCountdown();
    setCountdown(AUTO_LOAD_SECS);
    let remaining = AUTO_LOAD_SECS;

    countdownRef.current = setInterval(() => {
      remaining -= 1;
      setCountdown(remaining);
      if (remaining <= 0) {
        clearCountdown();
        onZero();
      }
    }, 1_000);
  }, [clearCountdown]);

  // ── Poll Supabase for new content ─────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const supabase = getBrowserClient();
        let query = supabase
          .from('trending_topics')
          .select('id', { count: 'exact', head: true })
          .eq('status', 'published');

        if (baselineRef.current) {
          query = query.gt('published_at', baselineRef.current);
        }

        const { count, error } = await query;
        if (error || !count || count <= 0 || visible) return;

        setNewCount(count);
        setVisible(true);
      } catch {
        // Silent — never break the feed
      }
    };

    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Start countdown when banner becomes visible ───────────────────────────
  useEffect(() => {
    if (!visible) return;

    const doLoad = () => {
      setVisible(false);
      baselineRef.current = new Date().toISOString();
      onRefresh();
    };

    startCountdown(doLoad);
    return () => clearCountdown();
  }, [visible, onRefresh, startCountdown, clearCountdown]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleLoadNow = useCallback(() => {
    clearCountdown();
    setVisible(false);
    baselineRef.current = new Date().toISOString();
    onRefresh();
  }, [clearCountdown, onRefresh]);

  const handleDismiss = useCallback(() => {
    clearCountdown();
    setVisible(false);
  }, [clearCountdown]);

  if (!visible) return null;

  return (
    <>
      <style>{`
        @keyframes slideDown {
          from { transform: translateY(-100%); opacity: 0; }
          to   { transform: translateY(0);    opacity: 1; }
        }
      `}</style>

      <div
        role="status"
        aria-live="polite"
        style={{
          position:       'fixed',
          top:            0,
          left:           0,
          right:          0,
          zIndex:         9999,
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'center',
          gap:            '12px',
          padding:        '11px 16px',
          background:     'linear-gradient(90deg, var(--color-primary) 0%, #7c3aed 100%)',
          color:          '#fff',
          fontFamily:     'var(--font-body)',
          fontSize:       '14px',
          fontWeight:     600,
          boxShadow:      '0 2px 12px rgba(0,0,0,0.25)',
          animation:      'slideDown 0.35s cubic-bezier(0.4,0,0.2,1)',
          flexWrap:       'wrap',
        }}
      >
        {/* Message */}
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '16px' }}>🔔</span>
          {newCount === 1 ? '1 new story available' : `${newCount} new stories available`}
          <span style={{ opacity: 0.75, fontWeight: 400 }}>
            — loading in {countdown}s
          </span>
        </span>

        {/* Load now button */}
        <button
          onClick={handleLoadNow}
          style={{
            background:   'rgba(255,255,255,0.2)',
            border:       '1.5px solid rgba(255,255,255,0.5)',
            borderRadius: '6px',
            color:        '#fff',
            fontFamily:   'var(--font-body)',
            fontSize:     '13px',
            fontWeight:   700,
            padding:      '4px 14px',
            cursor:       'pointer',
            whiteSpace:   'nowrap',
            transition:   'background 0.15s',
          }}
          onMouseEnter={e =>
            ((e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.32)')
          }
          onMouseLeave={e =>
            ((e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.2)')
          }
        >
          Load now
        </button>

        {/* Countdown progress bar */}
        <div
          style={{
            position:        'absolute',
            bottom:          0,
            left:            0,
            height:          '3px',
            background:      'rgba(255,255,255,0.5)',
            width:           `${(countdown / AUTO_LOAD_SECS) * 100}%`,
            transition:      'width 0.9s linear',
            borderRadius:    '0 2px 2px 0',
          }}
          aria-hidden
        />

        {/* Dismiss */}
        <button
          onClick={handleDismiss}
          aria-label="Dismiss notification"
          style={{
            background: 'none',
            border:     'none',
            color:      'rgba(255,255,255,0.7)',
            fontSize:   '20px',
            lineHeight: 1,
            cursor:     'pointer',
            padding:    '0 4px',
          }}
        >
          ×
        </button>
      </div>
    </>
  );
}
