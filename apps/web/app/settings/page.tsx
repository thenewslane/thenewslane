'use client';

/**
 * Settings page — /settings  (protected)
 *
 * Redirects to /login if no authenticated session.
 *
 * Sections:
 *   1. Category Preferences — CategoryPicker + save
 *   2. Notifications — push + email digest toggles + frequency
 *   3. Privacy — CCPA opt-out, data export request, Delete Account
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CategoryPicker } from '@platform/ui/web';
import { getBrowserClient } from '@platform/supabase';
import type { Category, UserProfile, UserPreferences } from '@platform/types';

// ---------------------------------------------------------------------------
// Style atoms
// ---------------------------------------------------------------------------
const sectionStyle: React.CSSProperties = {
  backgroundColor: 'var(--color-card-light)',
  borderRadius:    'var(--radius-large)',
  padding:         'var(--spacing-6)',
  marginBottom:    'var(--spacing-6)',
  boxShadow:       '0 1px 3px rgba(0,0,0,.06)',
};

const sectionTitleStyle: React.CSSProperties = {
  fontFamily:   'var(--font-heading)',
  fontSize:     '18px',
  fontWeight:   700,
  color:        'var(--color-text-primary-light)',
  margin:       '0 0 var(--spacing-4)',
};

const saveBtnStyle: React.CSSProperties = {
  padding:         'var(--spacing-2) var(--spacing-6)',
  borderRadius:    'var(--radius-small)',
  border:          'none',
  backgroundColor: 'var(--color-primary)',
  color:           '#fff',
  fontSize:        '13px',
  fontWeight:      700,
  fontFamily:      'var(--font-body)',
  cursor:          'pointer',
  transition:      'opacity 0.15s',
};

const toggleRowStyle: React.CSSProperties = {
  display:        'flex',
  alignItems:     'center',
  justifyContent: 'space-between',
  padding:        'var(--spacing-3) 0',
  borderBottom:   '1px solid rgba(0,0,0,.07)',
};

// ---------------------------------------------------------------------------
// Toggle switch (pure style — no hooks)
// ---------------------------------------------------------------------------
function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled,
}: {
  checked:      boolean;
  onChange:     (v: boolean) => void;
  label:        string;
  description?: string;
  disabled?:    boolean;
}) {
  return (
    <div style={toggleRowStyle}>
      <div>
        <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, fontFamily: 'var(--font-body)', color: 'var(--color-text-primary-light)' }}>
          {label}
        </p>
        {description && (
          <p style={{ margin: '2px 0 0', fontSize: '12px', fontFamily: 'var(--font-body)', color: 'var(--color-text-muted-light)', lineHeight: 1.5 }}>
            {description}
          </p>
        )}
      </div>

      <button
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        style={{
          flexShrink:      0,
          position:        'relative',
          width:           44,
          height:          24,
          borderRadius:    12,
          border:          'none',
          backgroundColor: checked ? 'var(--color-primary)' : 'rgba(0,0,0,.18)',
          cursor:          disabled ? 'not-allowed' : 'pointer',
          transition:      'background-color 0.2s',
          opacity:         disabled ? 0.5 : 1,
        }}
      >
        <span
          style={{
            position:        'absolute',
            top:             2,
            left:            checked ? 22 : 2,
            width:           20,
            height:          20,
            borderRadius:    10,
            backgroundColor: '#fff',
            boxShadow:       '0 1px 4px rgba(0,0,0,.2)',
            transition:      'left 0.2s',
          }}
        />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Delete Account confirmation modal
// ---------------------------------------------------------------------------
function DeleteAccountModal({
  onConfirm,
  onCancel,
  loading,
}: {
  onConfirm: () => void;
  onCancel:  () => void;
  loading:   boolean;
}) {
  const [typed, setTyped] = useState('');

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-modal-title"
      style={{
        position:        'fixed',
        inset:           0,
        backgroundColor: 'rgba(0,0,0,.5)',
        display:         'flex',
        alignItems:      'center',
        justifyContent:  'center',
        zIndex:          9998,
        padding:         'var(--spacing-4)',
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--color-card-light)',
          borderRadius:    'var(--radius-large)',
          padding:         'var(--spacing-8)',
          maxWidth:        420,
          width:           '100%',
          boxShadow:       '0 8px 40px rgba(0,0,0,.2)',
        }}
      >
        <h2
          id="delete-modal-title"
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     '20px',
            fontWeight:   700,
            color:        'var(--color-primary)',
            margin:       '0 0 var(--spacing-3)',
          }}
        >
          Delete Account
        </h2>

        <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', lineHeight: 1.65, color: 'var(--color-text-secondary-light)', margin: '0 0 var(--spacing-4)' }}>
          This action is <strong>permanent and cannot be undone</strong>. All your
          data — profile, preferences, and submissions — will be deleted immediately.
        </p>

        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary-light)', margin: '0 0 var(--spacing-2)' }}>
          Type <strong>DELETE</strong> to confirm:
        </p>

        <input
          type="text"
          value={typed}
          onChange={e => setTyped(e.target.value)}
          placeholder="DELETE"
          style={{
            width:           '100%',
            padding:         'var(--spacing-2) var(--spacing-3)',
            borderRadius:    'var(--radius-small)',
            border:          '1.5px solid rgba(0,0,0,.15)',
            fontSize:        '15px',
            fontFamily:      'var(--font-body)',
            color:           'var(--color-text-primary-light)',
            backgroundColor: 'var(--color-background-light)',
            marginBottom:    'var(--spacing-4)',
            boxSizing:       'border-box',
            outline:         'none',
          }}
        />

        <div style={{ display: 'flex', gap: 'var(--spacing-3)' }}>
          <button
            onClick={onConfirm}
            disabled={typed !== 'DELETE' || loading}
            style={{
              flex:            1,
              padding:         'var(--spacing-3)',
              borderRadius:    'var(--radius-small)',
              border:          'none',
              backgroundColor: typed === 'DELETE' ? 'var(--color-primary)' : 'rgba(0,0,0,.12)',
              color:           typed === 'DELETE' ? '#fff' : 'var(--color-text-muted-light)',
              fontSize:        '14px',
              fontWeight:      700,
              fontFamily:      'var(--font-body)',
              cursor:          typed === 'DELETE' && !loading ? 'pointer' : 'not-allowed',
              opacity:         loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Deleting…' : 'Delete my account'}
          </button>

          <button
            onClick={onCancel}
            disabled={loading}
            style={{
              flex:            1,
              padding:         'var(--spacing-3)',
              borderRadius:    'var(--radius-small)',
              border:          '1.5px solid rgba(0,0,0,.12)',
              backgroundColor: 'transparent',
              color:           'var(--color-text-secondary-light)',
              fontSize:        '14px',
              fontWeight:      600,
              fontFamily:      'var(--font-body)',
              cursor:          loading ? 'not-allowed' : 'pointer',
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function SettingsPage() {
  const router = useRouter();

  const [authLoading,  setAuthLoading]  = useState(true);
  const [userId,       setUserId]       = useState<string | null>(null);
  const [profile,      setProfile]      = useState<UserProfile | null>(null);
  const [prefs,        setPrefs]        = useState<UserPreferences | null>(null);
  const [categories,   setCategories]   = useState<Category[]>([]);

  // Section 1 — category state
  const [selectedCats, setSelectedCats] = useState<number[]>([]);
  const [catsSaving,   setCatsSaving]   = useState(false);
  const [catsSaved,    setCatsSaved]    = useState(false);

  // Section 2 — notifications state
  const [notifEnabled,     setNotifEnabled]     = useState(true);
  const [emailDigest,      setEmailDigest]      = useState(false);
  const [digestFrequency,  setDigestFrequency]  = useState<'daily' | 'weekly'>('weekly');
  const [notifSaving,      setNotifSaving]      = useState(false);
  const [notifSaved,       setNotifSaved]       = useState(false);

  // Section 3 — privacy state
  const [ccpaOptOut,       setCcpaOptOut]       = useState(false);
  const [privacySaving,    setPrivacySaving]    = useState(false);
  const [privacySaved,     setPrivacySaved]     = useState(false);
  const [showDeleteModal,  setShowDeleteModal]  = useState(false);
  const [deleteLoading,    setDeleteLoading]    = useState(false);

  const [pageError, setPageError] = useState<string | null>(null);

  // ── Auth check + data load ─────────────────────────────────────────────
  useEffect(() => {
    const supabase = getBrowserClient();

    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        router.replace('/login?returnTo=/settings');
        return;
      }
      setUserId(user.id);

      // Load profile, prefs, categories in parallel
      Promise.all([
        supabase.from('user_profiles').select('*').eq('id', user.id).single(),
        supabase.from('user_preferences').select('*').eq('user_id', user.id).single(),
        supabase.from('categories').select('*').order('name', { ascending: true }),
      ]).then(([profileRes, prefsRes, catsRes]) => {
        const p = profileRes.data as UserProfile | null;
        const pref = prefsRes.data as UserPreferences | null;

        setProfile(p);
        setPrefs(pref);
        setCategories((catsRes.data ?? []) as Category[]);

        // Seed local state
        setSelectedCats(pref?.preferred_categories ?? []);
        setNotifEnabled(pref?.notification_enabled ?? true);
        setEmailDigest(pref?.email_digest_enabled ?? false);
        setDigestFrequency(pref?.digest_frequency ?? 'weekly');
        setCcpaOptOut(p?.ccpa_opt_out ?? false);

        setAuthLoading(false);
      });
    });
  }, [router]);

  // ── Section 1 save ─────────────────────────────────────────────────────
  const saveCategoryPrefs = useCallback(async () => {
    if (!userId) return;
    setCatsSaving(true);
    setCatsSaved(false);
    const supabase = getBrowserClient();
    // `as never`: Supabase upsert generics resolve to `never` with hand-crafted types.
    const { error } = await supabase.from('user_preferences').upsert(
      { user_id: userId, preferred_categories: selectedCats } as never,
      { onConflict: 'user_id' },
    );
    if (error) setPageError(error.message);
    else setCatsSaved(true);
    setCatsSaving(false);
    setTimeout(() => setCatsSaved(false), 3000);
  }, [userId, selectedCats]);

  // ── Section 2 save ─────────────────────────────────────────────────────
  const saveNotifPrefs = useCallback(async () => {
    if (!userId) return;
    setNotifSaving(true);
    setNotifSaved(false);
    const supabase = getBrowserClient();
    const { error } = await supabase.from('user_preferences').upsert(
      {
        user_id:              userId,
        notification_enabled: notifEnabled,
        email_digest_enabled: emailDigest,
        digest_frequency:     emailDigest ? digestFrequency : null,
      } as never,
      { onConflict: 'user_id' },
    );
    if (error) setPageError(error.message);
    else setNotifSaved(true);
    setNotifSaving(false);
    setTimeout(() => setNotifSaved(false), 3000);
  }, [userId, notifEnabled, emailDigest, digestFrequency]);

  // ── Section 3 save (CCPA) ──────────────────────────────────────────────
  const savePrivacy = useCallback(async () => {
    if (!userId) return;
    setPrivacySaving(true);
    setPrivacySaved(false);
    const supabase = getBrowserClient();
    const { error } = await supabase
      .from('user_profiles')
      .update({ ccpa_opt_out: ccpaOptOut } as never)
      .eq('id', userId);
    if (error) {
      setPageError(error.message);
    } else {
      // Persist in localStorage for ad targeting layer
      localStorage.setItem('nl_ccpa_opt_out', ccpaOptOut ? '1' : '0');
      setPrivacySaved(true);
    }
    setPrivacySaving(false);
    setTimeout(() => setPrivacySaved(false), 3000);
  }, [userId, ccpaOptOut]);

  // ── Delete account ─────────────────────────────────────────────────────
  const deleteAccount = useCallback(async () => {
    if (!userId) return;
    setDeleteLoading(true);
    const supabase = getBrowserClient();
    const { error } = await supabase.functions.invoke('delete-user-data');
    if (error) {
      setPageError(error.message);
      setDeleteLoading(false);
      setShowDeleteModal(false);
      return;
    }
    await supabase.auth.signOut();
    localStorage.removeItem('nl_consent_v1');
    localStorage.removeItem('nl_ccpa_opt_out');
    router.replace('/');
  }, [userId, router]);

  // ── Loading state ──────────────────────────────────────────────────────
  if (authLoading) {
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

  // ── Page ───────────────────────────────────────────────────────────────
  return (
    <>
      {showDeleteModal && (
        <DeleteAccountModal
          onConfirm={deleteAccount}
          onCancel={() => setShowDeleteModal(false)}
          loading={deleteLoading}
        />
      )}

      <div
        style={{
          maxWidth: 680,
          margin:   '0 auto',
          padding:  'var(--spacing-8) var(--spacing-4) var(--spacing-16)',
        }}
      >
        <h1
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     'clamp(22px, 4vw, 32px)',
            fontWeight:   700,
            color:        'var(--color-text-primary-light)',
            marginBottom: 'var(--spacing-8)',
          }}
        >
          Account Settings
        </h1>

        {pageError && (
          <p
            role="alert"
            style={{
              padding:         'var(--spacing-3)',
              borderRadius:    'var(--radius-small)',
              backgroundColor: 'color-mix(in srgb, var(--color-primary) 10%, transparent)',
              color:           'var(--color-primary)',
              fontSize:        '13px',
              fontFamily:      'var(--font-body)',
              marginBottom:    'var(--spacing-6)',
            }}
          >
            {pageError}
          </p>
        )}

        {/* ── Section 1: Category preferences ── */}
        <section style={sectionStyle} aria-labelledby="cats-heading">
          <h2 id="cats-heading" style={sectionTitleStyle}>Category Preferences</h2>
          <p style={{ margin: '0 0 var(--spacing-4)', fontSize: '13px', fontFamily: 'var(--font-body)', color: 'var(--color-text-secondary-light)', lineHeight: 1.6 }}>
            Choose up to 3 categories to personalise your feed.
          </p>

          <CategoryPicker
            categories={categories}
            selected={selectedCats}
            onChange={setSelectedCats}
            maxSelections={3}
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-3)', marginTop: 'var(--spacing-6)' }}>
            <button
              onClick={saveCategoryPrefs}
              disabled={catsSaving}
              style={{ ...saveBtnStyle, opacity: catsSaving ? 0.7 : 1 }}
            >
              {catsSaving ? 'Saving…' : 'Save Preferences'}
            </button>
            {catsSaved && (
              <span style={{ fontSize: '13px', fontFamily: 'var(--font-body)', color: 'var(--color-viral-tier-3)' }}>
                ✓ Saved
              </span>
            )}
          </div>
        </section>

        {/* ── Section 2: Notifications ── */}
        <section style={sectionStyle} aria-labelledby="notif-heading">
          <h2 id="notif-heading" style={sectionTitleStyle}>Notifications</h2>

          <Toggle
            checked={notifEnabled}
            onChange={setNotifEnabled}
            label="Push notifications"
            description="Get notified when new trending topics are published."
          />

          <Toggle
            checked={emailDigest}
            onChange={setEmailDigest}
            label="Email digest"
            description="Receive a curated digest of trending topics by email."
          />

          {emailDigest && (
            <div
              style={{
                padding:   'var(--spacing-3) 0',
                borderBottom: '1px solid rgba(0,0,0,.07)',
              }}
            >
              <label
                htmlFor="digest-frequency"
                style={{ display: 'block', fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-body)', color: 'var(--color-text-primary-light)', marginBottom: 'var(--spacing-1)' }}
              >
                Digest frequency
              </label>
              <select
                id="digest-frequency"
                value={digestFrequency}
                onChange={e => setDigestFrequency(e.target.value as 'daily' | 'weekly')}
                style={{
                  padding:         'var(--spacing-1) var(--spacing-3)',
                  borderRadius:    'var(--radius-small)',
                  border:          '1.5px solid rgba(0,0,0,.15)',
                  backgroundColor: 'var(--color-background-light)',
                  color:           'var(--color-text-primary-light)',
                  fontSize:        '13px',
                  fontFamily:      'var(--font-body)',
                  cursor:          'pointer',
                }}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-3)', marginTop: 'var(--spacing-6)' }}>
            <button
              onClick={saveNotifPrefs}
              disabled={notifSaving}
              style={{ ...saveBtnStyle, opacity: notifSaving ? 0.7 : 1 }}
            >
              {notifSaving ? 'Saving…' : 'Save Notification Settings'}
            </button>
            {notifSaved && (
              <span style={{ fontSize: '13px', fontFamily: 'var(--font-body)', color: 'var(--color-viral-tier-3)' }}>
                ✓ Saved
              </span>
            )}
          </div>
        </section>

        {/* ── Section 3: Privacy ── */}
        <section style={sectionStyle} aria-labelledby="privacy-heading">
          <h2 id="privacy-heading" style={sectionTitleStyle}>Privacy</h2>

          {/* CCPA opt-out */}
          <Toggle
            checked={ccpaOptOut}
            onChange={setCcpaOptOut}
            label="Do Not Sell My Personal Information"
            description="Opt out of the sale or sharing of your personal information for targeted advertising (CCPA)."
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-3)', margin: 'var(--spacing-4) 0 var(--spacing-6)' }}>
            <button
              onClick={savePrivacy}
              disabled={privacySaving}
              style={{ ...saveBtnStyle, opacity: privacySaving ? 0.7 : 1 }}
            >
              {privacySaving ? 'Saving…' : 'Save Privacy Settings'}
            </button>
            {privacySaved && (
              <span style={{ fontSize: '13px', fontFamily: 'var(--font-body)', color: 'var(--color-viral-tier-3)' }}>
                ✓ Saved
              </span>
            )}
          </div>

          {/* Data export */}
          <div
            style={{
              padding:      'var(--spacing-4)',
              borderRadius: 'var(--radius-medium)',
              border:       '1px solid rgba(0,0,0,.08)',
              marginBottom: 'var(--spacing-4)',
            }}
          >
            <p style={{ margin: '0 0 var(--spacing-2)', fontSize: '14px', fontWeight: 600, fontFamily: 'var(--font-body)', color: 'var(--color-text-primary-light)' }}>
              Request a copy of your data
            </p>
            <p style={{ margin: '0 0 var(--spacing-3)', fontSize: '13px', fontFamily: 'var(--font-body)', color: 'var(--color-text-muted-light)', lineHeight: 1.5 }}>
              Under GDPR and CCPA you have the right to receive a copy of all
              personal data we hold about you.
            </p>
            <a
              href={`mailto:privacy@${process.env.NEXT_PUBLIC_PUBLICATION_NAME?.toLowerCase() ?? 'thenewslane'}.com?subject=Data%20Export%20Request&body=Please%20send%20me%20a%20copy%20of%20all%20personal%20data%20associated%20with%20my%20account.`}
              style={{
                display:         'inline-block',
                padding:         'var(--spacing-2) var(--spacing-4)',
                borderRadius:    'var(--radius-small)',
                border:          '1.5px solid rgba(0,0,0,.15)',
                color:           'var(--color-text-secondary-light)',
                fontSize:        '13px',
                fontWeight:      600,
                fontFamily:      'var(--font-body)',
                textDecoration:  'none',
                transition:      'border-color 0.15s',
              }}
            >
              Request Data Export
            </a>
          </div>

          {/* Delete account */}
          <div
            style={{
              padding:      'var(--spacing-4)',
              borderRadius: 'var(--radius-medium)',
              border:       '1px solid color-mix(in srgb, var(--color-primary) 30%, transparent)',
              backgroundColor: 'color-mix(in srgb, var(--color-primary) 5%, transparent)',
            }}
          >
            <p style={{ margin: '0 0 var(--spacing-1)', fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-body)', color: 'var(--color-primary)' }}>
              Delete Account
            </p>
            <p style={{ margin: '0 0 var(--spacing-3)', fontSize: '13px', fontFamily: 'var(--font-body)', color: 'var(--color-text-secondary-light)', lineHeight: 1.5 }}>
              Permanently delete your account and all associated data. This action
              cannot be undone.
            </p>
            <button
              onClick={() => setShowDeleteModal(true)}
              style={{
                padding:         'var(--spacing-2) var(--spacing-4)',
                borderRadius:    'var(--radius-small)',
                border:          'none',
                backgroundColor: 'var(--color-primary)',
                color:           '#fff',
                fontSize:        '13px',
                fontWeight:      700,
                fontFamily:      'var(--font-body)',
                cursor:          'pointer',
              }}
            >
              Delete My Account
            </button>
          </div>
        </section>
      </div>
    </>
  );
}
