/**
 * Auth-aware Supabase client for admin server components.
 *
 * Uses @supabase/ssr + next/headers to read the JWT session cookie.
 * Returns the authenticated user — use for reading the current user identity.
 *
 * For admin DB queries (service-role access, bypassing RLS) use
 * getServerClient() from @platform/supabase instead.
 */

import { createServerClient } from '@supabase/ssr';
import { cookies }            from 'next/headers';

export async function createAuthClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll() {
          // Server components cannot set cookies — no-op.
        },
      },
    },
  );
}

/** Returns the authenticated user from the JWT cookie, or null. */
export async function getAuthUser() {
  const supabase = await createAuthClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.user ?? null;
}
