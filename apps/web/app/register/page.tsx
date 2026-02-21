'use client';

/**
 * Registration page — /register
 *
 * Three-step flow:
 *   Step 1 — AgeGate
 *     • Under 13 → friendly block, stop.
 *     • 13–17   → isMinor=true, proceed.
 *     • 18+     → isMinor=false, proceed.
 *   Step 2 — Email / password / display-name form
 *     • supabase.auth.signUp()
 *     • Insert user_profiles row (display_name, is_minor, is_admin=false)
 *     • If session returned → redirect to /onboarding/categories
 *     • If no session (email confirmation required) → show step 3
 *   Step 3 — "Check your email" confirmation holding page
 */

import React, { useState } from 'react';
import { useRouter }        from 'next/navigation';
import Link                 from 'next/link';
import { AgeGate }          from '@platform/ui/web';
import { getBrowserClient } from '@platform/supabase';
import {
  AuthFormCard,
  inputStyle,
  primaryBtnStyle,
  labelStyle,
  errorStyle,
} from '@/components/AuthFormCard';

type Step = 'age' | 'credentials' | 'confirm-email' | 'blocked';

export default function RegisterPage() {
  const router = useRouter();

  const [step,    setStep]    = useState<Step>('age');
  const [isMinor, setIsMinor] = useState(false);

  // Credentials form state
  const [displayName, setDisplayName] = useState('');
  const [email,       setEmail]       = useState('');
  const [password,    setPassword]    = useState('');
  const [error,       setError]       = useState<string | null>(null);
  const [loading,     setLoading]     = useState(false);

  // ── Step 1: AgeGate handlers ───────────────────────────────────────────
  function handleAgeVerified(minor: boolean) {
    setIsMinor(minor);
    setStep('credentials');
  }

  function handleAgeBlocked() {
    setStep('blocked');
  }

  // ── Step 2: credentials submit ─────────────────────────────────────────
  async function handleCredentialsSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    const supabase = getBrowserClient();

    // 1. Create auth user
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { display_name: displayName, is_minor: isMinor },
      },
    });

    if (signUpError) {
      setError(signUpError.message);
      setLoading(false);
      return;
    }

    const user = data.user;
    if (!user) {
      setError('Sign-up failed. Please try again.');
      setLoading(false);
      return;
    }

    // 2. Insert user_profiles (only when we have a session — i.e. no email confirmation)
    if (data.session) {
      // `as never`: Supabase v2.97 write generics resolve to `never` with hand-crafted types.
      const { error: profileError } = await supabase.from('user_profiles').insert({
        id:           user.id,
        email:        user.email!,
        display_name: displayName.trim() || null,
        is_minor:     isMinor,
        is_admin:     false,
        is_active:    true,
        ccpa_opt_out: false,
        weekly_submission_used_at: null,
      } as never);

      if (profileError && profileError.code !== '23505') {
        // 23505 = unique violation (profile already exists — safe to ignore)
        setError(profileError.message);
        setLoading(false);
        return;
      }

      router.push('/onboarding/categories');
    } else {
      // Email confirmation required — profile will be created after confirmation
      setStep('confirm-email');
    }
  }

  // ── Step 3: Under-13 block ─────────────────────────────────────────────
  if (step === 'blocked') {
    return (
      <AuthFormCard title="Access Restricted">
        <div style={{ textAlign: 'center', padding: 'var(--spacing-4) 0' }}>
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="var(--color-primary)"
            aria-hidden
            style={{ marginBottom: 'var(--spacing-4)' }}
          >
            <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm-1-5h2v2h-2zm0-8h2v6h-2z"/>
          </svg>
          <p
            style={{
              fontFamily:  'var(--font-body)',
              fontSize:    '15px',
              lineHeight:  1.7,
              color:       'var(--color-text-secondary-light)',
              margin:      '0 0 var(--spacing-6)',
            }}
          >
            We&apos;re sorry — you must be at least 13 years old to create
            an account on {process.env.NEXT_PUBLIC_PUBLICATION_NAME ?? 'theNewslane'}.
          </p>
          <Link
            href="/"
            style={{
              color:          'var(--color-link)',
              fontFamily:     'var(--font-body)',
              fontSize:       '14px',
              fontWeight:     600,
              textDecoration: 'none',
            }}
          >
            ← Back to home
          </Link>
        </div>
      </AuthFormCard>
    );
  }

  // ── Step 3: Email confirmation waiting ────────────────────────────────
  if (step === 'confirm-email') {
    return (
      <AuthFormCard
        title="Check your inbox"
        subtitle="We sent a confirmation link to your email address. Click it to activate your account."
      >
        <div style={{ textAlign: 'center', padding: 'var(--spacing-2) 0 var(--spacing-4)' }}>
          <svg
            width="56"
            height="56"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-secondary)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
            style={{ marginBottom: 'var(--spacing-4)' }}
          >
            <rect x="2" y="4" width="20" height="16" rx="2"/>
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
          </svg>
          <p
            style={{
              fontFamily: 'var(--font-body)',
              fontSize:   '13px',
              color:      'var(--color-text-muted-light)',
              margin:     0,
            }}
          >
            Didn&apos;t receive it?{' '}
            <Link href="/login" style={{ color: 'var(--color-link)' }}>
              Sign in to resend
            </Link>
          </p>
        </div>
      </AuthFormCard>
    );
  }

  // ── Step 1: AgeGate ────────────────────────────────────────────────────
  if (step === 'age') {
    return (
      <AuthFormCard
        title="Create your account"
        subtitle="We need to verify your age before getting started."
      >
        <AgeGate onVerified={handleAgeVerified} onBlocked={handleAgeBlocked} />
      </AuthFormCard>
    );
  }

  // ── Step 2: Credentials form ───────────────────────────────────────────
  return (
    <AuthFormCard
      title="Create your account"
      subtitle={
        isMinor
          ? "You're almost there. Set up your login details."
          : "Set up your login details."
      }
    >
      <form onSubmit={handleCredentialsSubmit} noValidate>
        {error && <p role="alert" style={errorStyle}>{error}</p>}

        <div style={{ marginBottom: 'var(--spacing-4)' }}>
          <label htmlFor="reg-name" style={labelStyle}>
            Display name <span style={{ fontWeight: 400, color: 'var(--color-text-muted-light)' }}>(optional)</span>
          </label>
          <input
            id="reg-name"
            type="text"
            autoComplete="name"
            value={displayName}
            onChange={e => setDisplayName(e.target.value)}
            style={inputStyle}
            placeholder="How should we call you?"
            maxLength={60}
          />
        </div>

        <div style={{ marginBottom: 'var(--spacing-4)' }}>
          <label htmlFor="reg-email" style={labelStyle}>Email address</label>
          <input
            id="reg-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={inputStyle}
            placeholder="you@example.com"
          />
        </div>

        <div style={{ marginBottom: 'var(--spacing-6)' }}>
          <label htmlFor="reg-password" style={labelStyle}>Password</label>
          <input
            id="reg-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={inputStyle}
            placeholder="Minimum 8 characters"
          />
        </div>

        {isMinor && (
          <p
            style={{
              fontSize:        '12px',
              fontFamily:      'var(--font-body)',
              color:           'var(--color-text-muted-light)',
              backgroundColor: 'rgba(0,0,0,.04)',
              borderRadius:    'var(--radius-small)',
              padding:         'var(--spacing-2) var(--spacing-3)',
              marginBottom:    'var(--spacing-4)',
              lineHeight:      1.5,
            }}
          >
            As a user under 18, your account will have certain content restrictions
            applied automatically.
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{ ...primaryBtnStyle, opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Creating account…' : 'Create Account'}
        </button>

        <p
          style={{
            fontSize:   '12px',
            fontFamily: 'var(--font-body)',
            color:      'var(--color-text-muted-light)',
            textAlign:  'center',
            marginTop:  'var(--spacing-3)',
            lineHeight: 1.5,
          }}
        >
          By creating an account you agree to our{' '}
          <Link href="/terms" style={{ color: 'var(--color-link)' }}>Terms</Link>
          {' '}and{' '}
          <Link href="/privacy" style={{ color: 'var(--color-link)' }}>Privacy Policy</Link>.
        </p>
      </form>

      <p
        style={{
          textAlign:  'center',
          marginTop:  'var(--spacing-4)',
          fontSize:   '14px',
          fontFamily: 'var(--font-body)',
          color:      'var(--color-text-secondary-light)',
        }}
      >
        Already have an account?{' '}
        <Link href="/login" style={{ color: 'var(--color-link)', fontWeight: 600 }}>
          Sign in
        </Link>
      </p>
    </AuthFormCard>
  );
}
