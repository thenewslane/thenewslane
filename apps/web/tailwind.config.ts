/**
 * tailwind.config.ts
 *
 * All design values are driven by CSS custom properties that come from
 * packages/theme/theme.config.ts → apps/web/styles/tokens.css.
 *
 * Tailwind classes reference the CSS variables rather than raw values so that
 * the entire visual system can be rethemed by editing theme.config.ts alone.
 *
 * Note: CSS-variable colors don't support Tailwind's opacity modifier syntax
 * (e.g. bg-primary/50) unless the variable is in `hsl(var(...))` format.
 * Use `bg-primary` directly; for transparency use Tailwind's `opacity-*` util.
 */
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    // Include shared UI components so their classes are not purged.
    '../../packages/ui/web/**/*.{ts,tsx}',
  ],

  theme: {
    // ── Colours ──────────────────────────────────────────────────────────────
    colors: {
      transparent: 'transparent',
      current:     'currentColor',
      white:       '#ffffff',
      black:       '#000000',

      primary:   'var(--color-primary)',
      secondary: 'var(--color-secondary)',
      accent:    'var(--color-accent)',
      link:      'var(--color-link)',

      background: {
        light: 'var(--color-background-light)',
        dark:  'var(--color-background-dark)',
      },

      text: {
        'primary-light':   'var(--color-text-primary-light)',
        'primary-dark':    'var(--color-text-primary-dark)',
        'secondary-light': 'var(--color-text-secondary-light)',
        'secondary-dark':  'var(--color-text-secondary-dark)',
        'muted-light':     'var(--color-text-muted-light)',
        'muted-dark':      'var(--color-text-muted-dark)',
      },

      card: {
        light: 'var(--color-card-light)',
        dark:  'var(--color-card-dark)',
      },

      'ad-slot': 'var(--color-ad-slot)',

      // Per-category colours (slug-keyed, match seed.sql)
      category: {
        technology:          'var(--color-category-technology)',
        entertainment:       'var(--color-category-entertainment)',
        sports:              'var(--color-category-sports)',
        politics:            'var(--color-category-politics)',
        'business-finance':  'var(--color-category-business-finance)',
        'health-science':    'var(--color-category-health-science)',
        lifestyle:           'var(--color-category-lifestyle)',
        'world-news':        'var(--color-category-world-news)',
        'culture-arts':      'var(--color-category-culture-arts)',
        environment:         'var(--color-category-environment)',
      },

      viral: {
        tier1: 'var(--color-viral-tier-1)',
        tier2: 'var(--color-viral-tier-2)',
        tier3: 'var(--color-viral-tier-3)',
      },
    },

    // ── Typography ───────────────────────────────────────────────────────────
    fontFamily: {
      heading: ['var(--font-heading)'],
      body:    ['var(--font-body)'],
      sans:    ['var(--font-body)'],   // Tailwind prose default
    },

    // ── Border radius ────────────────────────────────────────────────────────
    borderRadius: {
      none:    '0',
      sm:      'var(--radius-small)',
      DEFAULT: 'var(--radius-medium)',
      lg:      'var(--radius-large)',
      full:    '9999px',
    },

    // ── Spacing (extends default so numeric Tailwind scale still works) ──────
    extend: {
      spacing: {
        'token-1':  'var(--spacing-1)',   //  4 px
        'token-2':  'var(--spacing-2)',   //  8 px
        'token-3':  'var(--spacing-3)',   // 12 px
        'token-4':  'var(--spacing-4)',   // 16 px
        'token-6':  'var(--spacing-6)',   // 24 px
        'token-8':  'var(--spacing-8)',   // 32 px
        'token-12': 'var(--spacing-12)',  // 48 px
        'token-16': 'var(--spacing-16)',  // 64 px
      },

      // Site-specific layout helpers
      maxWidth: {
        site: '1200px',
      },
    },
  },

  plugins: [],
};

export default config;
