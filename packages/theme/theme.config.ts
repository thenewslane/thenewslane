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
  // Brand colours — upmarket Gen Z palette
  // ---------------------------------------------------------------------------
  primaryColor:   '#E8384F', // vibrant coral-red — bold, contemporary
  secondaryColor: '#141422', // deep indigo-black — editorial depth
  accentColor:    '#7C5CFC', // electric violet — Gen Z signature
  linkColor:      '#3B82F6', // modern blue — accessible, clean

  // ---------------------------------------------------------------------------
  // Background — light and dark variants
  // ---------------------------------------------------------------------------
  backgroundColor: {
    light: '#FAFAFA',
    dark:  '#0A0A14',
  },

  // ---------------------------------------------------------------------------
  // Text — primary / secondary / muted, light and dark
  // ---------------------------------------------------------------------------
  textColor: {
    primary: {
      light: '#1C1C1E',
      dark:  '#F5F5F7',
    },
    secondary: {
      light: '#48484A',
      dark:  '#A0A0A8',
    },
    muted: {
      light: '#8E8E93',
      dark:  '#636366',
    },
  },

  // ---------------------------------------------------------------------------
  // Card backgrounds
  // ---------------------------------------------------------------------------
  cardBackground: {
    light: '#FFFFFF',
    dark:  '#1C1C2E',
  },

  // ---------------------------------------------------------------------------
  // Border radius scale — slightly more generous for Gen Z aesthetic
  // ---------------------------------------------------------------------------
  borderRadius: {
    small:  6,   // px — badges, chips, buttons
    medium: 12,  // px — default cards
    large:  20,  // px — modals, hero cards
  },

  // ---------------------------------------------------------------------------
  // Typography — modern geometric heading, clean body
  // ---------------------------------------------------------------------------
  fontFamily: {
    heading: '"Plus Jakarta Sans", "Inter", system-ui, -apple-system, sans-serif',
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
    technology:      '#3478F6', // modern blue
    entertainment:   '#AF52DE', // rich purple
    sports:          '#FF6B35', // vibrant orange
    politics:        '#E8384F', // coral-red
    'business-finance': '#30D158', // fresh green
    'health-science':   '#00C7BE', // teal
    lifestyle:       '#FFB340', // warm gold
    'world-news':    '#3A3A4A', // charcoal
    'culture-arts':  '#FF6482', // rose
    environment:     '#34C759', // eco green
  },

  // ---------------------------------------------------------------------------
  // Viral tier colours
  // ---------------------------------------------------------------------------
  viralTierColors: {
    tier1: '#E8384F', // coral-red — hottest stories
    tier2: '#FFB340', // gold      — trending stories
    tier3: '#30D158', // green     — emerging stories
  },

  // ---------------------------------------------------------------------------
  // Ad slot background
  // ---------------------------------------------------------------------------
  adSlotBackground: '#F2F2F7',
} as const;

export type Theme = typeof theme;
