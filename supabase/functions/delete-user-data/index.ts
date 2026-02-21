// =============================================================================
// Edge Function: delete-user-data
// GDPR Article 17 — Right to Erasure
//
// Receives:  POST { "user_id": "<uuid>" }
// Actions:
//   1. Deletes user_preferences, user_submissions, consent_records rows
//   2. Writes an immutable record to deletion_audit_log
//   3. Deletes the auth.users row (cascades → user_profiles via FK)
//
// Must be called with a valid service-role JWT or a JWT from a user who
// owns the user_id being deleted (verify_jwt: true is set at deploy time).
//
// Deploy:
//   supabase functions deploy delete-user-data --project-ref <ref>
// =============================================================================

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// Tables that hold personal data keyed by user_id.
// Order matters: clear child records before the auth.users delete cascades.
const USER_DATA_TABLES = [
  'consent_records',
  'user_submissions',
  'user_preferences',
] as const;

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type',
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}

Deno.serve(async (req: Request): Promise<Response> => {
  // ── CORS preflight ─────────────────────────────────────────────────────────
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: CORS_HEADERS });
  }

  if (req.method !== 'POST') {
    return jsonResponse({ error: 'Method not allowed' }, 405);
  }

  // ── Parse and validate input ───────────────────────────────────────────────
  let user_id: string;
  try {
    const body = await req.json();
    user_id = body?.user_id;
  } catch {
    return jsonResponse({ error: 'Invalid JSON body' }, 400);
  }

  if (!user_id || typeof user_id !== 'string' || user_id.trim() === '') {
    return jsonResponse({ error: 'user_id (non-empty string) is required' }, 400);
  }
  user_id = user_id.trim();

  // ── Supabase admin client (service role bypasses RLS) ─────────────────────
  const supabaseUrl = Deno.env.get('SUPABASE_URL');
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

  if (!supabaseUrl || !serviceKey) {
    console.error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY secrets');
    return jsonResponse({ error: 'Server misconfiguration' }, 500);
  }

  const supabase = createClient(supabaseUrl, serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  const clearedTables: string[] = [];
  const deletionErrors: string[] = [];

  // ── Step 1: Delete personal data from application tables ───────────────────
  for (const table of USER_DATA_TABLES) {
    const { error } = await supabase
      .from(table)
      .delete()
      .eq('user_id', user_id);

    if (error) {
      console.error(`[delete-user-data] Failed on ${table}:`, error.message);
      deletionErrors.push(`${table}: ${error.message}`);
    } else {
      clearedTables.push(table);
    }
  }

  // Abort if any table deletion failed — do not proceed to auth deletion.
  // This prevents a state where auth.users is removed but orphaned data remains.
  if (deletionErrors.length > 0) {
    return jsonResponse(
      {
        error: 'Partial deletion failure — auth user was NOT deleted.',
        details: deletionErrors,
        cleared: clearedTables,
      },
      500,
    );
  }

  // ── Step 2: Write audit record BEFORE deleting auth.users ─────────────────
  // We write the audit record first so that deletion_audit_log.deleted_by can
  // reference user_profiles (if needed) before the cascade removes it.
  const { error: auditError } = await supabase
    .from('deletion_audit_log')
    .insert({
      table_name: 'auth.users',
      record_id: user_id,
      deleted_by: null,       // system/self-service deletion, not admin-initiated
      reason: 'GDPR Article 17 — Right to Erasure request (Edge Function)',
      data_snapshot: {
        user_id,
        action: 'deleted',
        tables_cleared: clearedTables,
        requested_at: new Date().toISOString(),
        source: 'delete-user-data edge function',
      },
    });

  if (auditError) {
    console.error('[delete-user-data] Audit log write failed:', auditError.message);
    return jsonResponse(
      {
        error: `Audit log failed — auth user was NOT deleted: ${auditError.message}`,
        cleared: clearedTables,
      },
      500,
    );
  }

  // ── Step 3: Delete auth.users (cascades to user_profiles via FK) ──────────
  const { error: deleteUserError } = await supabase.auth.admin.deleteUser(user_id);

  if (deleteUserError) {
    console.error('[delete-user-data] Auth user deletion failed:', deleteUserError.message);
    return jsonResponse(
      {
        error: `Auth user deletion failed: ${deleteUserError.message}`,
        note: 'Application data was cleared. Retry to remove the auth user.',
        cleared: clearedTables,
      },
      500,
    );
  }

  // ── Done ───────────────────────────────────────────────────────────────────
  console.log(`[delete-user-data] Successfully deleted user ${user_id}`);

  return jsonResponse({
    success: true,
    user_id,
    tables_cleared: clearedTables,
    deleted_at: new Date().toISOString(),
  });
});
