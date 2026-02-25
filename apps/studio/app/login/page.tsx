'use client';

/**
 * Studio CMS Login — /login
 *
 * Uses @supabase/ssr createBrowserClient so the session is written
 * to cookies — which the middleware can read to allow access.
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createBrowserClient } from '@supabase/ssr';

function getSupabase() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}

const css = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&display=swap');
  *{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#0a0a0f;--surface:#111118;--surface2:#1a1a24;
    --border:#2a2a38;--accent:#e8c547;--accent2:#7c6af7;
    --text:#f0f0f8;--text2:#9090a8;--text3:#606078;
    --red:#ff4466;
  }
  body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center}
  .login-wrap{width:100%;max-width:380px;padding:24px}
  .login-logo{text-align:center;margin-bottom:36px}
  .logo-mark{font-family:'DM Serif Display',serif;font-size:26px;color:var(--accent);letter-spacing:-.5px}
  .logo-sub{font-size:11px;color:var(--text3);letter-spacing:2px;text-transform:uppercase;margin-top:4px}
  .login-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:28px}
  .login-title{font-family:'DM Serif Display',serif;font-size:22px;margin-bottom:4px}
  .login-sub{font-size:13px;color:var(--text3);margin-bottom:24px}
  .form-group{margin-bottom:16px}
  .form-label{font-size:12px;color:var(--text2);margin-bottom:6px;display:block;font-weight:500}
  .form-input{width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:7px;padding:10px 14px;font-size:13px;color:var(--text);font-family:'DM Sans',sans-serif;outline:none;transition:border-color .15s}
  .form-input:focus{border-color:var(--accent2)}
  .btn{display:flex;align-items:center;justify-content:center;width:100%;padding:11px;border-radius:7px;font-size:14px;font-weight:600;cursor:pointer;border:none;font-family:'DM Sans',sans-serif;transition:all .15s;margin-top:8px}
  .btn:disabled{opacity:.6;cursor:not-allowed}
  .btn-primary{background:var(--accent);color:#0a0a0f}
  .btn-primary:hover:not(:disabled){background:#f0ce55}
  .error-box{background:rgba(255,68,102,.1);border:1px solid rgba(255,68,102,.3);border-radius:7px;padding:10px 14px;font-size:12px;color:var(--red);margin-bottom:16px}
`;

export default function LoginPage() {
  const router                      = useRouter();
  const [email,    setEmail]        = useState('');
  const [password, setPassword]     = useState('');
  const [loading,  setLoading]      = useState(false);
  const [error,    setError]        = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    const supabase = getSupabase();
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });

    if (signInError) {
      setError(signInError.message);
      setLoading(false);
      return;
    }

    // Refresh server state so the middleware cookie is recognised,
    // then navigate to the CMS dashboard.
    router.refresh();
    router.push('/');
  }

  return (
    <>
      <style suppressHydrationWarning>{css}</style>
      <div className="login-wrap">
        <div className="login-logo">
          <div className="logo-mark">theNewslane</div>
          <div className="logo-sub">Studio CMS</div>
        </div>
        <div className="login-card">
          <div className="login-title">Sign in</div>
          <div className="login-sub">Enter your credentials to access the CMS</div>

          {error && <div className="error-box">⚠ {error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input
                className="form-input"
                type="email"
                placeholder="you@thenewslane.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                className="form-input"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>
            <button
              className="btn btn-primary"
              type="submit"
              disabled={loading || !email || !password}
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
