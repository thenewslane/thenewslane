/**
 * TopicSkeleton
 *
 * Shimmer placeholder that mirrors the TopicCard layout.
 * Pure server component — no hooks required.
 */

export function TopicSkeleton() {
  return (
    <div
      aria-hidden="true"
      style={{
        display:         'flex',
        flexDirection:   'column',
        borderRadius:    'var(--radius-medium)',
        overflow:        'hidden',
        backgroundColor: 'var(--color-card-light)',
        boxShadow:       '0 1px 3px rgba(0,0,0,.08)',
      }}
    >
      {/* Thumbnail shimmer */}
      <div
        style={{
          width:     '100%',
          paddingTop: '52.5%',
          position:  'relative',
        }}
      >
        <div style={{ position: 'absolute', inset: 0 }}>
          <Shimmer />
        </div>
      </div>

      {/* Content shimmer */}
      <div
        style={{
          padding:       'var(--spacing-3)',
          display:       'flex',
          flexDirection: 'column',
          gap:           'var(--spacing-2)',
        }}
      >
        {/* Badges row */}
        <div style={{ display: 'flex', gap: 'var(--spacing-2)' }}>
          <div style={{ width: 64, height: 20, borderRadius: '999px', overflow: 'hidden' }}>
            <Shimmer />
          </div>
          <div style={{ width: 80, height: 20, borderRadius: '999px', overflow: 'hidden' }}>
            <Shimmer />
          </div>
        </div>

        {/* Title */}
        <div style={{ height: 20, borderRadius: 'var(--radius-small)', overflow: 'hidden' }}>
          <Shimmer />
        </div>
        <div style={{ height: 20, width: '75%', borderRadius: 'var(--radius-small)', overflow: 'hidden' }}>
          <Shimmer />
        </div>

        {/* Summary */}
        <div style={{ height: 14, borderRadius: 'var(--radius-small)', overflow: 'hidden' }}>
          <Shimmer />
        </div>
        <div style={{ height: 14, width: '90%', borderRadius: 'var(--radius-small)', overflow: 'hidden' }}>
          <Shimmer />
        </div>
        <div style={{ height: 14, width: '60%', borderRadius: 'var(--radius-small)', overflow: 'hidden' }}>
          <Shimmer />
        </div>

        {/* Byline */}
        <div style={{ height: 13, width: 120, borderRadius: 'var(--radius-small)', overflow: 'hidden', marginTop: 'var(--spacing-1)' }}>
          <Shimmer />
        </div>
      </div>
    </div>
  );
}

function Shimmer() {
  return (
    <div
      style={{
        width:      '100%',
        height:     '100%',
        background: 'linear-gradient(90deg, rgba(0,0,0,.06) 25%, rgba(0,0,0,.03) 50%, rgba(0,0,0,.06) 75%)',
        backgroundSize: '200% 100%',
        animation:  'shimmer 1.4s ease infinite',
      }}
    />
  );
}
