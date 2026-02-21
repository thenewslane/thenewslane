'use client';

export function SkipToContent() {
  return (
    <a
      href="#main-content"
      className="skip-link"
      style={{
        position:        'absolute',
        left:            '-9999px',
        top:             'auto',
        width:           1,
        height:          1,
        overflow:        'hidden',
        zIndex:          999,
        backgroundColor: 'var(--color-primary)',
        color:           '#fff',
        padding:         'var(--spacing-3) var(--spacing-6)',
        borderRadius:    'var(--radius-small)',
        fontFamily:      'var(--font-body)',
        fontWeight:      700,
        textDecoration:  'none',
      }}
      onFocus={e => {
        const el = e.currentTarget;
        el.style.left   = 'var(--spacing-4)';
        el.style.top    = 'var(--spacing-4)';
        el.style.width  = 'auto';
        el.style.height = 'auto';
      }}
      onBlur={e => {
        const el = e.currentTarget;
        el.style.left   = '-9999px';
        el.style.top    = 'auto';
        el.style.width  = '1px';
        el.style.height = '1px';
      }}
    >
      Skip to main content
    </a>
  );
}
