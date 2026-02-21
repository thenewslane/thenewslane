/**
 * generate-web-tokens.ts
 *
 * Reads theme.config.ts and writes CSS custom properties to
 * apps/web/styles/tokens.css.
 *
 * Naming convention: every nested key is joined with a dash and prefixed
 * with the appropriate category:
 *   theme.primaryColor            → --color-primary
 *   theme.backgroundColor.light   → --color-background-light
 *   theme.textColor.primary.dark  → --color-text-primary-dark
 *   theme.borderRadius.medium     → --radius-medium
 *   theme.fontFamily.heading      → --font-heading
 *   theme.spacing[4]              → --spacing-4
 *   theme.categoryColors.sports   → --color-category-sports
 *   theme.viralTierColors.tier1   → --color-viral-tier-1
 *   theme.adSlotBackground        → --color-ad-slot
 */

import { writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { theme } from './theme.config.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT = resolve(__dirname, '../../apps/web/styles/tokens.css');

function buildCssVars(): string {
  const vars: string[] = [];

  // --- Flat colour tokens -----------------------------------------------
  vars.push(`  --color-primary:   ${theme.primaryColor};`);
  vars.push(`  --color-secondary: ${theme.secondaryColor};`);
  vars.push(`  --color-accent:    ${theme.accentColor};`);
  vars.push(`  --color-link:      ${theme.linkColor};`);

  // Background
  vars.push(`  --color-background-light: ${theme.backgroundColor.light};`);
  vars.push(`  --color-background-dark:  ${theme.backgroundColor.dark};`);

  // Text
  for (const [variant, modes] of Object.entries(theme.textColor)) {
    for (const [mode, value] of Object.entries(modes)) {
      vars.push(`  --color-text-${variant}-${mode}: ${value};`);
    }
  }

  // Card background
  vars.push(`  --color-card-light: ${theme.cardBackground.light};`);
  vars.push(`  --color-card-dark:  ${theme.cardBackground.dark};`);

  // Ad slot
  vars.push(`  --color-ad-slot: ${theme.adSlotBackground};`);

  vars.push('');

  // --- Border radius ----------------------------------------------------
  for (const [size, value] of Object.entries(theme.borderRadius)) {
    vars.push(`  --radius-${size}: ${value}px;`);
  }

  vars.push('');

  // --- Typography -------------------------------------------------------
  vars.push(`  --font-heading: ${theme.fontFamily.heading};`);
  vars.push(`  --font-body:    ${theme.fontFamily.body};`);

  vars.push('');

  // --- Spacing ----------------------------------------------------------
  for (const [key, value] of Object.entries(theme.spacing)) {
    vars.push(`  --spacing-${key}: ${value}px;`);
  }

  vars.push('');

  // --- Category colours -------------------------------------------------
  for (const [slug, color] of Object.entries(theme.categoryColors)) {
    vars.push(`  --color-category-${slug}: ${color};`);
  }

  vars.push('');

  // --- Viral tier colours -----------------------------------------------
  vars.push(`  --color-viral-tier-1: ${theme.viralTierColors.tier1};`);
  vars.push(`  --color-viral-tier-2: ${theme.viralTierColors.tier2};`);
  vars.push(`  --color-viral-tier-3: ${theme.viralTierColors.tier3};`);

  return vars.join('\n');
}

export function generateWebTokens(): void {
  const timestamp = new Date().toISOString();
  const css = `/* =============================================================================
   tokens.css — Generated CSS custom properties
   Source: packages/theme/theme.config.ts
   Generated: ${timestamp}
   DO NOT EDIT — run \`npm run generate-tokens\` to regenerate.
   ============================================================================= */

:root {
${buildCssVars()}
}
`;

  mkdirSync(dirname(OUTPUT), { recursive: true });
  writeFileSync(OUTPUT, css, 'utf-8');
  console.log(`[web-tokens] ✓ Written → apps/web/styles/tokens.css`);
}

// Allow running directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  generateWebTokens();
}
