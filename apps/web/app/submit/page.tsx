'use client';

/**
 * Submit a topic — /submit  (protected)
 *
 * Redirects to /login if not authenticated.
 *
 * Before showing the form, checks user_profiles.weekly_submission_used_at.
 * If set within the last 7 days → shows a cooldown message with days remaining.
 * Otherwise renders the submission form.
 *
 * On submit:
 *   1. Insert into user_submissions (title, description, url, status=pending)
 *   2. Update user_profiles.weekly_submission_used_at = NOW()
 *   3. Show success message
 */

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getBrowserClient } from '@platform/supabase';
import type { UserProfile } from '@platform/types';
import {
  AuthFormCard,
  inputStyle,
  primaryBtnStyle,
  labelStyle,
  errorStyle,
} from '@/components/AuthFormCard';

const COOLDOWN_DAYS = 7;

function daysUntilNextSubmission(lastUsedAt: string): number {
  const last    = new Date(lastUsedAt).getTime();
  const now     = Date.now();
  const elapsed = (now - last) / (1000 * 60 * 60 * 24); // days
  return Math.max(0, Math.ceil(COOLDOWN_DAYS - elapsed));
}

function isOnCooldown(lastUsedAt: string | null): boolean {
  if (!lastUsedAt) return false;
  return daysUntilNextSubmission(lastUsedAt) > 0;
}

export default function SubmitPage() {
  const router = useRouter();

  const [loading,   setLoading]   = useState(true);
  const [userId,    setUserId]    = useState<string | null>(null);
  const [profile,   setProfile]   = useState<UserProfile | null>(null);

  // Form state
  const [title,       setTitle]       = useState('');
  const [description, setDescription] = useState('');
  const [sourceUrl,   setSourceUrl]   = useState('');
  const [submitting,  setSubmitting]  = useState(false);
  const [error,       setError]       = useState<string | null>(null);
  const [submitted,   setSubmitted]   = useState(false);

  // ── Auth + profile load ────────────────────────────────────────────────
  useEffect(() => {
    const supabase = getBrowserClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        router.replace('/login?returnTo=/submit');
        return;
      }
      setUserId(user.id);
      supabase
        .from('user_profiles')
        .select('*')
        .eq('id', user.id)
        .single()
        .then(({ data }) => {
          setProfile(data as UserProfile | null);
          setLoading(false);
        });
    });
  }, [router]);

  // ── Submit handler ─────────────────────────────────────────────────────
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError('Topic title is required.');
      return;
    }

    setSubmitting(true);
    const supabase = getBrowserClient();

    // 1. Insert submission
    // `as never`: Supabase v2.97 write generics resolve to `never` with hand-crafted types.
    const { error: insertError } = await supabase.from('user_submissions').insert({
      user_id:     userId!,
      title:       title.trim(),
      description: description.trim() || null,
      url:         sourceUrl.trim() || null,
      status:      'pending',
    } as never);

    if (insertError) {
      setError(insertError.message);
      setSubmitting(false);
      return;
    }

    // 2. Update weekly cooldown timestamp
    const { error: updateError } = await supabase
      .from('user_profiles')
      .update({ weekly_submission_used_at: new Date().toISOString() } as never)
      .eq('id', userId!);

    if (updateError) {
      // Non-fatal — submission is already recorded
      console.warn('[SubmitPage] Failed to update weekly_submission_used_at:', updateError.message);
    }

    setSubmitting(false);
    setSubmitted(true);
  }

  // ── Loading ────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div
          style={{
            width:          40,
            height:         40,
            borderRadius:   '50%',
            border:         '3px solid rgba(0,0,0,.1)',
            borderTopColor: 'var(--color-primary)',
            animation:      'spin 0.7s linear infinite',
          }}
        />
      </div>
    );
  }

  // ── Cooldown check ─────────────────────────────────────────────────────
  if (profile && isOnCooldown(profile.weekly_submission_used_at)) {
    const daysLeft = daysUntilNextSubmission(profile.weekly_submission_used_at!);
    return (
      <AuthFormCard
        title="Submission limit reached"
        subtitle="You can submit one topic per week to keep suggestions high-quality."
      >
        <div style={{ textAlign: 'center', padding: 'var(--spacing-4) 0' }}>
          <div
            style={{
              display:         'inline-flex',
              alignItems:      'center',
              justifyContent:  'center',
              width:           72,
              height:          72,
              borderRadius:    '50%',
              backgroundColor: 'color-mix(in srgb, var(--color-secondary) 12%, transparent)',
              marginBottom:    'var(--spacing-4)',
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--color-secondary)" aria-hidden>
              <path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
            </svg>
          </div>

          <p
            style={{
              fontFamily:   'var(--font-body)',
              fontSize:     '15px',
              lineHeight:   1.7,
              color:        'var(--color-text-primary-light)',
              margin:       '0 0 var(--spacing-2)',
            }}
          >
            You can submit again in{' '}
            <strong style={{ color: 'var(--color-secondary)' }}>
              {daysLeft} {daysLeft === 1 ? 'day' : 'days'}
            </strong>.
          </p>
          <p
            style={{
              fontFamily: 'var(--font-body)',
              fontSize:   '13px',
              color:      'var(--color-text-muted-light)',
              margin:     '0 0 var(--spacing-6)',
              lineHeight: 1.5,
            }}
          >
            Your previous submission is being reviewed by our editorial team.
          </p>

          <button
            onClick={() => router.push('/')}
            style={{
              padding:         'var(--spacing-2) var(--spacing-6)',
              borderRadius:    'var(--radius-small)',
              border:          '1.5px solid rgba(0,0,0,.12)',
              backgroundColor: 'transparent',
              color:           'var(--color-text-secondary-light)',
              fontSize:        '14px',
              fontWeight:      600,
              fontFamily:      'var(--font-body)',
              cursor:          'pointer',
            }}
          >
            Back to feed
          </button>
        </div>
      </AuthFormCard>
    );
  }

  // ── Success state ──────────────────────────────────────────────────────
  if (submitted) {
    return (
      <AuthFormCard
        title="Topic submitted!"
        subtitle="Thanks for your suggestion. Our editorial team will review it within 48 hours."
      >
        <div style={{ textAlign: 'center', padding: 'var(--spacing-4) 0' }}>
          <div
            style={{
              display:         'inline-flex',
              alignItems:      'center',
              justifyContent:  'center',
              width:           72,
              height:          72,
              borderRadius:    '50%',
              backgroundColor: 'color-mix(in srgb, var(--color-viral-tier-3) 15%, transparent)',
              marginBottom:    'var(--spacing-4)',
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--color-viral-tier-3)" aria-hidden>
              <path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/>
            </svg>
          </div>

          <p
            style={{
              fontFamily: 'var(--font-body)',
              fontSize:   '13px',
              color:      'var(--color-text-muted-light)',
              margin:     '0 0 var(--spacing-6)',
              lineHeight: 1.5,
            }}
          >
            You can submit another topic in {COOLDOWN_DAYS} days.
          </p>

          <button
            onClick={() => router.push('/')}
            style={{
              padding:         'var(--spacing-2) var(--spacing-6)',
              borderRadius:    'var(--radius-small)',
              border:          'none',
              backgroundColor: 'var(--color-primary)',
              color:           '#fff',
              fontSize:        '14px',
              fontWeight:      700,
              fontFamily:      'var(--font-body)',
              cursor:          'pointer',
            }}
          >
            Back to feed
          </button>
        </div>
      </AuthFormCard>
    );
  }

  // ── Submission form ────────────────────────────────────────────────────
  return (
    <AuthFormCard
      title="Suggest a topic"
      subtitle="See something trending that we've missed? Let us know."
      maxWidth={520}
    >
      <form onSubmit={handleSubmit} noValidate>
        {error && <p role="alert" style={errorStyle}>{error}</p>}

        {/* Title */}
        <div style={{ marginBottom: 'var(--spacing-4)' }}>
          <label htmlFor="submit-title" style={labelStyle}>
            Topic title <span style={{ color: 'var(--color-primary)' }}>*</span>
          </label>
          <input
            id="submit-title"
            type="text"
            required
            maxLength={200}
            value={title}
            onChange={e => setTitle(e.target.value)}
            style={inputStyle}
            placeholder="e.g. The new AI model everyone is talking about"
          />
          <p style={{ margin: '4px 0 0', fontSize: '11px', fontFamily: 'var(--font-body)', color: 'var(--color-text-muted-light)' }}>
            {title.length}/200
          </p>
        </div>

        {/* Why it's trending */}
        <div style={{ marginBottom: 'var(--spacing-4)' }}>
          <label htmlFor="submit-description" style={labelStyle}>
            Why is it trending?{' '}
            <span style={{ fontWeight: 400, color: 'var(--color-text-muted-light)' }}>(optional)</span>
          </label>
          <textarea
            id="submit-description"
            rows={4}
            maxLength={500}
            value={description}
            onChange={e => setDescription(e.target.value)}
            style={{
              ...inputStyle,
              resize:     'vertical',
              lineHeight: 1.6,
            }}
            placeholder="Briefly explain why this topic is going viral right now…"
          />
          <p style={{ margin: '4px 0 0', fontSize: '11px', fontFamily: 'var(--font-body)', color: 'var(--color-text-muted-light)' }}>
            {description.length}/500
          </p>
        </div>

        {/* Source URL */}
        <div style={{ marginBottom: 'var(--spacing-6)' }}>
          <label htmlFor="submit-url" style={labelStyle}>
            Source URL{' '}
            <span style={{ fontWeight: 400, color: 'var(--color-text-muted-light)' }}>(optional)</span>
          </label>
          <input
            id="submit-url"
            type="url"
            value={sourceUrl}
            onChange={e => setSourceUrl(e.target.value)}
            style={inputStyle}
            placeholder="https://example.com/article"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || !title.trim()}
          style={{
            ...primaryBtnStyle,
            opacity: submitting || !title.trim() ? 0.65 : 1,
            cursor:  submitting || !title.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          {submitting ? 'Submitting…' : 'Submit Topic'}
        </button>

        <p
          style={{
            textAlign:  'center',
            marginTop:  'var(--spacing-3)',
            fontSize:   '12px',
            fontFamily: 'var(--font-body)',
            color:      'var(--color-text-muted-light)',
            lineHeight: 1.5,
          }}
        >
          You can submit one topic per week. All suggestions are reviewed by our
          editorial team before publication.
        </p>
      </form>
    </AuthFormCard>
  );
}
