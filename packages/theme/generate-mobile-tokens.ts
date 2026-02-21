/**
 * generate-mobile-tokens.ts
 *
 * Reads theme.config.ts and writes a React Native StyleSheet-compatible
 * TypeScript constants file to apps/mobile/styles/tokens.ts.
 *
 * Naming convention: camelCase exported constants.
 *   theme.primaryColor            → export const colorPrimary
 *   theme.backgroundColor.light   → export const colorBackgroundLight
 *   theme.textColor.primary.dark  → export const colorTextPrimaryDark
 *   theme.borderRadius.medium     → export const radiusMedium
 *   theme.fontFamily.heading      → export const fontHeading
 *   theme.spacing[4]              → export const spacing4
 *   theme.categoryColors.sports   → export const colorCategorySports
 *   theme.viralTierColors.tier1   → export const colorViralTier1
 *   theme.adSlotBackground        → export const colorAdSlot
 */

import { writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { theme } from './theme.config.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT = resolve(__dirname, '../../apps/mobile/styles/tokens.ts');

/** Convert a dash-separated or dot-separated token name to camelCase. */
function toCamelCase(str: string): string {
  return str
    .replace(/[-.](.)/g, (_, char: string) => char.toUpperCase())
    .replace(/^(.)/, (_, char: string) => char.toLowerCase());
}

/** Emit `export const <name> = <value>;` for a string or number value. */
function emit(name: string, value: string | number): string {
  const val = typeof value === 'number' ? value : `'${value}'`;
  return `export const ${toCamelCase(name)} = ${val};`;
}

function buildExports(): string {
  const lines: string[] = [];

  // --- Brand colours ---------------------------------------------------
  lines.push('// Brand colours');
  lines.push(emit('colorPrimary',   theme.primaryColor));
  lines.push(emit('colorSecondary', theme.secondaryColor));
  lines.push(emit('colorAccent',    theme.accentColor));
  lines.push(emit('colorLink',      theme.linkColor));
  lines.push('');

  // --- Background ------------------------------------------------------
  lines.push('// Background');
  lines.push(emit('colorBackgroundLight', theme.backgroundColor.light));
  lines.push(emit('colorBackgroundDark',  theme.backgroundColor.dark));
  lines.push('');

  // --- Text ------------------------------------------------------------
  lines.push('// Text colours');
  for (const [variant, modes] of Object.entries(theme.textColor)) {
    for (const [mode, value] of Object.entries(modes)) {
      const name = `colorText${cap(variant)}${cap(mode)}`;
      lines.push(`export const ${name} = '${value}';`);
    }
  }
  lines.push('');

  // --- Card background -------------------------------------------------
  lines.push('// Card backgrounds');
  lines.push(emit('colorCardLight', theme.cardBackground.light));
  lines.push(emit('colorCardDark',  theme.cardBackground.dark));
  lines.push('');

  // --- Ad slot ---------------------------------------------------------
  lines.push('// Ad slot');
  lines.push(emit('colorAdSlot', theme.adSlotBackground));
  lines.push('');

  // --- Border radius ---------------------------------------------------
  lines.push('// Border radius (px)');
  for (const [size, value] of Object.entries(theme.borderRadius)) {
    lines.push(`export const radius${cap(size)} = ${value};`);
  }
  lines.push('');

  // --- Typography ------------------------------------------------------
  lines.push('// Font families');
  lines.push(emit('fontHeading', theme.fontFamily.heading));
  lines.push(emit('fontBody',    theme.fontFamily.body));
  lines.push('');

  // --- Spacing ---------------------------------------------------------
  lines.push('// Spacing (px)');
  for (const [key, value] of Object.entries(theme.spacing)) {
    lines.push(`export const spacing${key} = ${value};`);
  }
  lines.push('');

  // --- Spacing as array (convenience for StyleSheet) -------------------
  lines.push('// Full spacing scale as array');
  lines.push(`export const spacingScale = [${Object.values(theme.spacing).join(', ')}] as const;`);
  lines.push('');

  // --- Category colours ------------------------------------------------
  lines.push('// Category colours');
  for (const [slug, color] of Object.entries(theme.categoryColors)) {
    const camel = toCamelCase(`colorCategory-${slug}`);
    lines.push(`export const ${camel} = '${color}';`);
  }
  lines.push('');

  // --- Category colours map (convenient lookup by slug) ----------------
  lines.push('// Category colours map (slug → hex)');
  lines.push('export const categoryColors = {');
  for (const [slug, color] of Object.entries(theme.categoryColors)) {
    lines.push(`  '${slug}': '${color}',`);
  }
  lines.push('} as const;');
  lines.push('');

  // --- Viral tier colours ----------------------------------------------
  lines.push('// Viral tier colours');
  lines.push(emit('colorViralTier1', theme.viralTierColors.tier1));
  lines.push(emit('colorViralTier2', theme.viralTierColors.tier2));
  lines.push(emit('colorViralTier3', theme.viralTierColors.tier3));
  lines.push('');

  // --- Viral tier map --------------------------------------------------
  lines.push('// Viral tier colours map (tier number → hex)');
  lines.push('export const viralTierColors = {');
  lines.push(`  1: '${theme.viralTierColors.tier1}',`);
  lines.push(`  2: '${theme.viralTierColors.tier2}',`);
  lines.push(`  3: '${theme.viralTierColors.tier3}',`);
  lines.push('} as const;');

  return lines.join('\n');
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function generateMobileTokens(): void {
  const timestamp = new Date().toISOString();
  const ts = `// =============================================================================
// tokens.ts — Generated React Native design tokens
// Source: packages/theme/theme.config.ts
// Generated: ${timestamp}
// DO NOT EDIT — run \`npm run generate-tokens\` to regenerate.
// =============================================================================

${buildExports()}
`;

  mkdirSync(dirname(OUTPUT), { recursive: true });
  writeFileSync(OUTPUT, ts, 'utf-8');
  console.log(`[mobile-tokens] ✓ Written → apps/mobile/styles/tokens.ts`);
}

// Allow running directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  generateMobileTokens();
}
