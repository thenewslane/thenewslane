/**
 * theme.config.ts — Single source of truth for all visual design tokens.
 *
 * Edit this file to retheme the entire platform.
 * Run `npm run generate-tokens` from the repo root (or `npm run generate`
 * from packages/theme) to push changes to:
 *   • apps/web/styles/tokens.css    (CSS custom properties)
 *   • apps/mobile/styles/tokens.ts  (React Native StyleSheet constants)
 *
 * Publication: theNewslane (thenewslane.com)
 */

export const theme = {
  // ---------------------------------------------------------------------------
  // Brand colours
  // ---------------------------------------------------------------------------
  primaryColor:   '#AD2D37', // theNewslane brand red
  secondaryColor: '#1E3A5F', // deep navy
  accentColor:    '#E05A1E', // warm orange — CTAs, highlights
  linkColor:      '#2563EB', // accessible blue

  // ---------------------------------------------------------------------------
  // Background — light and dark variants
  // ---------------------------------------------------------------------------
  backgroundColor: {
    light: '#FFFFFF',
    dark:  '#0D0D0E',
  },

  // ---------------------------------------------------------------------------
  // Text — primary / secondary / muted, light and dark
  // ---------------------------------------------------------------------------
  textColor: {
    primary: {
      light: '#1A1A1A',
      dark:  '#F5F5F7',
    },
    secondary: {
      light: '#4B4B4B',
      dark:  '#A0A0A8',
    },
    muted: {
      light: '#8B8B9A',
      dark:  '#6B6B7A',
    },
  },

  // ---------------------------------------------------------------------------
  // Card backgrounds
  // ---------------------------------------------------------------------------
  cardBackground: {
    light: '#FFFFFF',
    dark:  '#1A1A2E',
  },

  // ---------------------------------------------------------------------------
  // Border radius scale
  // ---------------------------------------------------------------------------
  borderRadius: {
    small:  4,   // px — subtle rounding (badges, chips)
    medium: 8,   // px — default cards
    large:  16,  // px — modals, hero cards
  },

  // ---------------------------------------------------------------------------
  // Typography
  // ---------------------------------------------------------------------------
  fontFamily: {
    heading: '"Georgia", "Times New Roman", Times, serif',
    body:    '"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },

  // ---------------------------------------------------------------------------
  // Spacing scale (px) — used for padding, margin, gap
  // ---------------------------------------------------------------------------
  spacing: {
    1:  4,
    2:  8,
    3:  12,
    4:  16,
    6:  24,
    8:  32,
    12: 48,
    16: 64,
  },

  // ---------------------------------------------------------------------------
  // Category colours — one hex per content vertical (matches seed.sql slugs)
  // ---------------------------------------------------------------------------
  categoryColors: {
    technology:      '#2980B9', // tech blue
    entertainment:   '#8E44AD', // vibrant purple
    sports:          '#E67E22', // energetic orange
    politics:        '#C0392B', // authoritative red
    'business-finance': '#27AE60', // financial green
    'health-science':   '#16A085', // clinical teal
    lifestyle:       '#F39C12', // warm amber
    'world-news':    '#2C3E50', // neutral navy
    'culture-arts':  '#D35400', // rich terracotta
    environment:     '#1ABC9C', // eco green
  },

  // ---------------------------------------------------------------------------
  // Viral tier colours
  // ---------------------------------------------------------------------------
  viralTierColors: {
    tier1: '#E63946', // red-orange — hottest stories
    tier2: '#F4A261', // amber      — trending stories
    tier3: '#2A9D8F', // green      — emerging stories
  },

  // ---------------------------------------------------------------------------
  // Ad slot background
  // ---------------------------------------------------------------------------
  adSlotBackground: '#F0F0F5',
} as const;

export type Theme = typeof theme;
