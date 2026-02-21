import React from 'react';

export interface ViralIndicatorProps {
  tier:       1 | 2 | 3;
  score:      number;   // 0.0 – 1.0
  showScore?: boolean;  // default true
  showLabel?: boolean;  // default true
}

const TIER_COLOR: Record<1 | 2 | 3, string> = {
  1: 'var(--color-viral-tier-1)',
  2: 'var(--color-viral-tier-2)',
  3: 'var(--color-viral-tier-3)',
};

const TIER_LABEL: Record<1 | 2 | 3, string> = {
  1: 'Viral',
  2: 'Trending',
  3: 'Emerging',
};

function FlameIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M17.66 11.2c-.23-.3-.51-.56-.77-.82-.67-.6-1.43-1.03-2.07-1.66C13.33 7.26 13 4.85 13.95 3c-.96.23-1.79.75-2.5 1.32C8.87 6.4 7.85 10.07 9.07 13.22c.04.1.08.2.08.33 0 .22-.15.42-.35.5-.23.1-.47.04-.66-.12a.8.8 0 0 1-.15-.17C6.87 12.33 6.69 10.28 7.45 8.64 5.78 10 4.87 12.3 5 14.47c.06.5.12 1 .29 1.5.14.6.41 1.2.71 1.73C7.08 19.43 8.95 20.67 10.96 20.92c2.14.27 4.43-.12 6.07-1.6 1.83-1.66 2.47-4.32 1.53-6.6l-.13-.26c-.21-.46-.77-1.26-.77-1.26z"/>
    </svg>
  );
}

function TrendingIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
    </svg>
  );
}

function DotIcon() {
  return (
    <svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <circle cx="12" cy="12" r="8"/>
    </svg>
  );
}

const TIER_ICON: Record<1 | 2 | 3, React.ReactElement> = {
  1: <FlameIcon />,
  2: <TrendingIcon />,
  3: <DotIcon />,
};

export function ViralIndicator({
  tier,
  score,
  showScore = true,
  showLabel = true,
}: ViralIndicatorProps) {
  const color = TIER_COLOR[tier];
  const label = TIER_LABEL[tier];
  const pct   = Math.round(score * 100);

  return (
    <span
      aria-label={`${label}${showScore ? ` — ${pct}%` : ''}`}
      style={{
        display:    'inline-flex',
        alignItems: 'center',
        gap:        '3px',
        color,
        fontSize:   '11px',
        fontWeight: 700,
        fontFamily: 'var(--font-body)',
      }}
    >
      {TIER_ICON[tier]}
      {showScore && <span>{pct}%</span>}
      {showLabel && (
        <span style={{ fontWeight: 400, opacity: 0.85 }}>{label}</span>
      )}
    </span>
  );
}
