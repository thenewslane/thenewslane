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

export function createAuthClient() {
  const cookieStore = cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get:    (name: string) => cookieStore.get(name)?.value,
        set:    () => { /* no-op: server components cannot set cookies */ },
        remove: () => { /* no-op */ },
      },
    },
  );
}

/** Returns the authenticated user from the JWT cookie, or null. */
export async function getAuthUser() {
  const supabase = createAuthClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.user ?? null;
}
