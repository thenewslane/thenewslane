/**
 * @platform/supabase — Shared Supabase client factory.
 *
 * Exports two typed client creators:
 *
 *   createBrowserClient()
 *     Uses the anon key — respects Row Level Security.
 *     For use in Next.js Client Components and the Expo app.
 *
 *   createServerClient()
 *     Uses the service-role key — bypasses Row Level Security.
 *     For use in Inngest pipeline functions, Next.js Server Components /
 *     Route Handlers, and setup scripts that need admin-level access.
 *     NEVER expose the service key or this client to the browser.
 *
 * Both clients are typed with the shared Database schema from @platform/types.
 *
 * Usage:
 *   import { createBrowserClient } from '@platform/supabase';
 *   const supabase = createBrowserClient();
 *   const { data } = await supabase.from('trending_topics').select('*');
 */

import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import type { Database } from '@platform/types';

// ---------------------------------------------------------------------------
// Environment variable resolution
// ---------------------------------------------------------------------------

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    if (typeof window === 'undefined') {
      // Server-side during build — return empty string gracefully
      return '';
    }		
    throw new Error(
      `[supabase] Missing required environment variable: ${name}. ` +
      `Check your .env file and ensure it is loaded before importing this module.`
    );
  }
  return value;
}

// ---------------------------------------------------------------------------
// Browser client
// Uses: NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_ANON_KEY
// Respects RLS — safe to use in browser bundles.
// ---------------------------------------------------------------------------

export function createBrowserClient(): SupabaseClient<Database> {
  const url  = requireEnv('NEXT_PUBLIC_SUPABASE_URL');
  const anonKey = requireEnv('NEXT_PUBLIC_SUPABASE_ANON_KEY');

  return createClient<Database>(url, anonKey, {
    auth: {
      persistSession:    true,
      autoRefreshToken:  true,
      detectSessionInUrl: true,
    },
  });
}

// ---------------------------------------------------------------------------
// Server client (service role)
// Uses: SUPABASE_URL + SUPABASE_SERVICE_KEY
// Bypasses RLS — NEVER use in browser code or expose the key.
// ---------------------------------------------------------------------------

export function createServerClient(): SupabaseClient<Database> {
  const url        = requireEnv('SUPABASE_URL');
  const serviceKey = requireEnv('SUPABASE_SERVICE_KEY');

  return createClient<Database>(url, serviceKey, {
    auth: {
      persistSession:   false,
      autoRefreshToken: false,
    },
  });
}

// ---------------------------------------------------------------------------
// Singleton helpers
// For apps that want a single shared instance per process/request.
// ---------------------------------------------------------------------------

let _browserClient: SupabaseClient<Database> | null = null;
let _serverClient:  SupabaseClient<Database> | null = null;

/**
 * Returns a cached browser (anon) client.
 * Safe to call on every render — the instance is reused.
 */
export function getBrowserClient(): SupabaseClient<Database> {
  if (!_browserClient) _browserClient = createBrowserClient();
  return _browserClient;
}

/**
 * Returns a cached server (service-role) client.
 * For use in server-only contexts (Inngest, Next.js server, scripts).
 */
export function getServerClient(): SupabaseClient<Database> {
  if (!_serverClient) _serverClient = createServerClient();
  return _serverClient;
}

// ---------------------------------------------------------------------------
// Re-export Supabase types for convenience
// ---------------------------------------------------------------------------

export type { SupabaseClient } from '@supabase/supabase-js';
export type { Database }       from '@platform/types';
