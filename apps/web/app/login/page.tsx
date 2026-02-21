'use client';

/**
 * Login page — /login
 *
 * Standard email/password login via Supabase auth.
 * Redirects to homepage on success (or ?returnTo= if present).
 */

import React, { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { getBrowserClient } from '@platform/supabase';
import {
  AuthFormCard,
  inputStyle,
  primaryBtnStyle,
  labelStyle,
  errorStyle,
} from '@/components/AuthFormCard';

// useSearchParams must be inside Suspense
function LoginForm() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const returnTo     = searchParams.get('returnTo') ?? '/';

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = getBrowserClient();
    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });

    if (authError) {
      setError(authError.message);
      setLoading(false);
    } else {
      router.push(returnTo);
    }
  }

  return (
    <AuthFormCard
      title="Welcome back"
      subtitle="Sign in to your account to continue."
    >
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <p role="alert" style={errorStyle}>{error}</p>
        )}

        <div style={{ marginBottom: 'var(--spacing-4)' }}>
          <label htmlFor="login-email" style={labelStyle}>Email address</label>
          <input
            id="login-email"
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
          <label htmlFor="login-password" style={labelStyle}>Password</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={inputStyle}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{ ...primaryBtnStyle, opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Signing in…' : 'Sign In'}
        </button>
      </form>

      <p
        style={{
          textAlign:  'center',
          marginTop:  'var(--spacing-6)',
          fontSize:   '14px',
          fontFamily: 'var(--font-body)',
          color:      'var(--color-text-secondary-light)',
        }}
      >
        Don&apos;t have an account?{' '}
        <Link
          href="/register"
          style={{ color: 'var(--color-link)', fontWeight: 600 }}
        >
          Create one
        </Link>
      </p>
    </AuthFormCard>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
