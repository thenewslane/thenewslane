'use client';

/**
 * Onboarding — Category Picker — /onboarding/categories
 *
 * Shown immediately after registration (or account confirmation).
 * Loads all 10 categories, renders CategoryPicker, and saves the
 * selection to user_preferences on submit.
 * Redirects to the homepage when done (or if user skips).
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter }      from 'next/navigation';
import { CategoryPicker } from '@platform/ui/web';
import { getBrowserClient } from '@platform/supabase';
import type { Category }  from '@platform/types';

export default function OnboardingCategoriesPage() {
  const router = useRouter();

  const [categories, setCategories] = useState<Category[]>([]);
  const [selected,   setSelected]   = useState<number[]>([]);
  const [userId,     setUserId]     = useState<string | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [saving,     setSaving]     = useState(false);
  const [error,      setError]      = useState<string | null>(null);

  // ── Load categories + check auth ──────────────────────────────────────
  useEffect(() => {
    const supabase = getBrowserClient();

    Promise.all([
      supabase.auth.getUser(),
      supabase.from('categories').select('*').order('name', { ascending: true }),
    ]).then(([authResult, catResult]) => {
      if (!authResult.data.user) {
        // Not authenticated — redirect to registration
        router.replace('/register');
        return;
      }
      setUserId(authResult.data.user.id);
      setCategories((catResult.data ?? []) as Category[]);
      setLoading(false);
    });
  }, [router]);

  // ── Save preferences ──────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!userId) return;
    setSaving(true);
    setError(null);

    const supabase = getBrowserClient();
    // `as never` cast: Supabase v2 upsert generics resolve to `never` with
    // hand-crafted Database types (use `npx supabase gen types` to avoid this).
    const { error: upsertError } = await supabase
      .from('user_preferences')
      .upsert(
        { user_id: userId, preferred_categories: selected } as never,
        { onConflict: 'user_id' },
      );

    if (upsertError) {
      setError(upsertError.message);
      setSaving(false);
    } else {
      router.push('/');
    }
  }, [userId, selected, router]);

  // ── Loading ───────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div
          style={{
            width:        40,
            height:       40,
            borderRadius: '50%',
            border:       '3px solid rgba(0,0,0,.1)',
            borderTopColor: 'var(--color-primary)',
            animation:    'spin 0.7s linear infinite',
          }}
        />
      </div>
    );
  }

  // ── Page ──────────────────────────────────────────────────────────────
  return (
    <div
      style={{
        maxWidth: 640,
        margin:   '0 auto',
        padding:  'var(--spacing-12) var(--spacing-4) var(--spacing-16)',
      }}
    >
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-8)' }}>
        <h1
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     'clamp(22px, 4vw, 32px)',
            fontWeight:   700,
            color:        'var(--color-text-primary-light)',
            marginBottom: 'var(--spacing-2)',
          }}
        >
          What do you care about?
        </h1>
        <p
          style={{
            fontFamily: 'var(--font-body)',
            fontSize:   '15px',
            lineHeight: 1.65,
            color:      'var(--color-text-secondary-light)',
            margin:     0,
          }}
        >
          Choose up to 3 topics to personalise your feed. You can always change
          these later in Settings.
        </p>
      </div>

      {/* Category picker */}
      <div style={{ marginBottom: 'var(--spacing-8)' }}>
        <CategoryPicker
          categories={categories}
          selected={selected}
          onChange={setSelected}
          maxSelections={3}
        />
      </div>

      {/* Error */}
      {error && (
        <p
          role="alert"
          style={{
            padding:         'var(--spacing-2) var(--spacing-3)',
            borderRadius:    'var(--radius-small)',
            backgroundColor: 'color-mix(in srgb, var(--color-primary) 10%, transparent)',
            color:           'var(--color-primary)',
            fontSize:        '13px',
            fontFamily:      'var(--font-body)',
            marginBottom:    'var(--spacing-4)',
          }}
        >
          {error}
        </p>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 'var(--spacing-3)', flexDirection: 'column' }}>
        <button
          onClick={handleSave}
          disabled={saving || selected.length === 0}
          style={{
            padding:         'var(--spacing-3)',
            borderRadius:    'var(--radius-small)',
            border:          'none',
            backgroundColor: selected.length > 0 ? 'var(--color-primary)' : 'rgba(0,0,0,.12)',
            color:           selected.length > 0 ? '#fff' : 'var(--color-text-muted-light)',
            fontSize:        '15px',
            fontWeight:      700,
            fontFamily:      'var(--font-body)',
            cursor:          selected.length > 0 ? 'pointer' : 'not-allowed',
            transition:      'background-color 0.15s',
            opacity:         saving ? 0.7 : 1,
          }}
        >
          {saving ? 'Saving…' : `Save ${selected.length > 0 ? `(${selected.length} selected)` : 'preferences'}`}
        </button>

        <button
          onClick={() => router.push('/')}
          style={{
            padding:         'var(--spacing-2)',
            borderRadius:    'var(--radius-small)',
            border:          'none',
            backgroundColor: 'transparent',
            color:           'var(--color-text-muted-light)',
            fontSize:        '13px',
            fontFamily:      'var(--font-body)',
            cursor:          'pointer',
            textDecoration:  'underline',
          }}
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
