'use client';

/**
 * Admin Login — /login
 *
 * Email + password via Supabase Auth.
 * After sign-in, checks user_profiles.is_admin before redirecting.
 * Non-admin users see an error and are signed back out.
 */

import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getBrowserClient } from '@platform/supabase';

function LoginInner() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const errorParam   = searchParams.get('error');

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(
    errorParam === 'unauthorized' ? 'Your account does not have admin access.' : null,
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = getBrowserClient();

    // 1. Sign in
    const { data, error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (signInError) {
      setError(signInError.message);
      setLoading(false);
      return;
    }

    if (!data.user) {
      setError('Sign-in failed. Please try again.');
      setLoading(false);
      return;
    }

    // 2. Check is_admin
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('is_admin')
      .eq('id', data.user.id)
      .single() as unknown as { data: { is_admin: boolean } | null; error: unknown };

    if (!profile?.is_admin) {
      await supabase.auth.signOut();
      setError('Your account does not have admin access.');
      setLoading(false);
      return;
    }

    // 3. Redirect to dashboard
    router.push('/');
    router.refresh();
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-8 h-8 bg-red-700 rounded" />
          <div>
            <p className="text-white font-bold text-lg leading-none">theNewslane</p>
            <p className="text-slate-400 text-xs">Admin Panel</p>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl border border-slate-700 p-8">
          <h1 className="text-white font-semibold text-xl mb-6">Sign in to admin</h1>

          {error && (
            <div
              role="alert"
              className="mb-4 px-3 py-2 bg-red-900/40 border border-red-700/50 rounded-md text-red-300 text-sm"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="mb-4">
              <label htmlFor="email" className="block text-sm text-slate-300 mb-1.5">
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent"
                placeholder="admin@thenewslane.com"
              />
            </div>

            <div className="mb-6">
              <label htmlFor="password" className="block text-sm text-slate-300 mb-1.5">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !email.trim() || !password}
              className="w-full py-2.5 bg-red-700 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-md transition-colors"
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          Admin access only. Unauthorised access is prohibited.
        </p>
      </div>
    </div>
  );
}

// Wrap in Suspense for useSearchParams
import { Suspense } from 'react';
export default function LoginPage() {
  return (
    <Suspense>
      <LoginInner />
    </Suspense>
  );
}
