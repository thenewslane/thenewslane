/**
 * Theme — /theme
 *
 * Color pickers for 5 brand colors.
 * Live preview of a mock TopicCard.
 * Save: stores to Supabase config table + triggers Vercel redeploy webhook.
 */

import React from 'react';
import { getServerClient }    from '@platform/supabase';
import { ThemeEditor }        from './_ThemeEditor';
import type { BrandColors }   from './_ThemeEditor';

// Default colors from theme.config.ts (used if no DB override exists)
const DEFAULT_COLORS: BrandColors = {
  primary:    '#AD2D37',
  secondary:  '#1E3A5F',
  accent:     '#E05A1E',
  link:       '#2563EB',
  viralTier1: '#E63946',
};

async function getCurrentColors(): Promise<BrandColors> {
  try {
    const supabase = getServerClient();
    const { data } = await supabase
      .from('config')
      .select('value')
      .eq('key', 'brand_colors')
      .single() as unknown as { data: { value: unknown } | null; error: unknown };

    if (data?.value && typeof data.value === 'object' && !Array.isArray(data.value)) {
      const v = data.value as Record<string, unknown>;
      // Merge DB values with defaults (in case DB has partial keys)
      return {
        primary:    typeof v.primary    === 'string' ? v.primary    : DEFAULT_COLORS.primary,
        secondary:  typeof v.secondary  === 'string' ? v.secondary  : DEFAULT_COLORS.secondary,
        accent:     typeof v.accent     === 'string' ? v.accent     : DEFAULT_COLORS.accent,
        link:       typeof v.link       === 'string' ? v.link       : DEFAULT_COLORS.link,
        viralTier1: typeof v.viralTier1 === 'string' ? v.viralTier1 : DEFAULT_COLORS.viralTier1,
      };
    }
  } catch {
    // No config row yet or DB unavailable — use defaults
  }
  return DEFAULT_COLORS;
}

export default async function ThemePage() {
  const colors = await getCurrentColors();

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Theme</h1>
        <p className="text-slate-500 text-sm mt-1">
          Customize brand colors. Changes are saved to the database and trigger a Vercel
          redeploy to update the CSS token system.
        </p>
      </div>
      <ThemeEditor initialColors={colors} />
    </div>
  );
}
