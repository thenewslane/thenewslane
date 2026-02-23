/**
 * Admin middleware — runs on every request.
 *
 * 1. Allows /login and static assets to pass through.
 * 2. Checks for a valid Supabase session via cookie.
 * 3. Queries user_profiles.is_admin — rejects non-admin sessions.
 * 4. Refreshes the auth token cookie on each request.
 *
 * Uses @supabase/ssr because Next.js middleware runs at the Edge and
 * cannot use the Node.js-only packages/supabase server client.
 */

import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { NextResponse, type NextRequest }          from 'next/server';

const PUBLIC_PATHS = ['/login'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // ── Require Supabase env (avoids 500 when missing on Vercel) ──────────
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseAnonKey) {
    return new NextResponse(
      [
        '<!DOCTYPE html><html><head><title>Configuration required</title></head><body style="font-family:sans-serif;max-width:32rem;margin:4rem auto;padding:1rem;">',
        '<h1>Configuration required</h1>',
        '<p>Missing <code>NEXT_PUBLIC_SUPABASE_URL</code> or <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in this environment.</p>',
        '<p>Add them in Vercel: Project → Settings → Environment Variables.</p>',
        '</body></html>',
      ].join(''),
      { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
    );
  }

  // ── Allow public paths ────────────────────────────────────────────────
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // ── Build a mutable response so we can refresh the auth cookie ────────
  let response = NextResponse.next({
    request: { headers: request.headers },
  });

  const supabase = createServerClient(
    supabaseUrl,
    supabaseAnonKey,
    {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          request.cookies.set({ name, value, ...options });
          response = NextResponse.next({ request: { headers: request.headers } });
          response.cookies.set({ name, value, ...options });
        },
        remove(name: string, options: CookieOptions) {
          request.cookies.set({ name, value: '', ...options });
          response = NextResponse.next({ request: { headers: request.headers } });
          response.cookies.set({ name, value: '', ...options });
        },
      },
    },
  );

  // ── Check session ─────────────────────────────────────────────────────
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    const loginUrl = new URL('/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

  // ── Check is_admin ────────────────────────────────────────────────────
  const { data: profile } = await supabase
    .from('user_profiles')
    .select('is_admin')
    .eq('id', session.user.id)
    .single();

  if (!profile?.is_admin) {
    const loginUrl = new URL('/login?error=unauthorized', request.url);
    return NextResponse.redirect(loginUrl);
  }

  return response;
}

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
