'use client';

/**
 * FreshContentBanner
 *
 * Polls Supabase every 60 seconds for articles published after the baseline
 * timestamp captured when the page first loaded. When new stories are found
 * a sticky top bar slides in inviting the user to load them.
 *
 * Props:
 *   latestPublishedAt — ISO string of the newest topic visible on page load
 *                       (null if the feed is empty)
 *   onRefresh         — called when the user clicks "Load now"; the parent
 *                       should refetch page 1 of the feed
 */

import React, { useEffect, useRef, useState } from 'react';
import { getBrowserClient } from '@platform/supabase';

interface FreshContentBannerProps {
  latestPublishedAt: string | null;
  onRefresh: () => void;
}

const POLL_INTERVAL_MS = 60_000; // 1 minute

export function FreshContentBanner({ latestPublishedAt, onRefresh }: FreshContentBannerProps) {
  const [newCount,  setNewCount]  = useState(0);
  const [visible,   setVisible]   = useState(false);
  const [animating, setAnimating] = useState(false);
  const baselineRef = useRef<string | null>(latestPublishedAt);

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
        if (error || !count || count <= 0) return;

        setNewCount(count);
        setVisible(true);
        setAnimating(true);
      } catch {
        // Silent — never break the feed
      }
    };

    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  const handleLoad = () => {
    setVisible(false);
    // Update baseline to now so we don't re-trigger immediately
    baselineRef.current = new Date().toISOString();
    onRefresh();
  };

  const handleDismiss = () => {
    setVisible(false);
  };

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
          padding:        '12px 16px',
          background:     'linear-gradient(90deg, var(--color-primary) 0%, #7c3aed 100%)',
          color:          '#fff',
          fontFamily:     'var(--font-body)',
          fontSize:       '14px',
          fontWeight:     600,
          boxShadow:      '0 2px 12px rgba(0,0,0,0.25)',
          animation:      animating ? 'slideDown 0.35s cubic-bezier(0.4,0,0.2,1)' : undefined,
          flexWrap:       'wrap',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '18px' }}>🔔</span>
          {newCount === 1
            ? '1 new story is available'
            : `${newCount} new stories are available`}
        </span>

        <button
          onClick={handleLoad}
          style={{
            background:    'rgba(255,255,255,0.2)',
            border:        '1.5px solid rgba(255,255,255,0.5)',
            borderRadius:  '6px',
            color:         '#fff',
            fontFamily:    'var(--font-body)',
            fontSize:      '13px',
            fontWeight:    700,
            padding:       '5px 14px',
            cursor:        'pointer',
            whiteSpace:    'nowrap',
            transition:    'background 0.15s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.32)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.2)';
          }}
        >
          Load now
        </button>

        <button
          onClick={handleDismiss}
          aria-label="Dismiss notification"
          style={{
            background:  'none',
            border:      'none',
            color:       'rgba(255,255,255,0.7)',
            fontSize:    '20px',
            lineHeight:  1,
            cursor:      'pointer',
            padding:     '0 4px',
            marginLeft:  '4px',
          }}
        >
          ×
        </button>
      </div>
    </>
  );
}
