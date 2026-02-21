'use server';

import { revalidatePath }  from 'next/cache';
import { getServerClient } from '@platform/supabase';

// ── Override a brand safety failure ───────────────────────────────────────
export async function overrideBrandSafety(
  logId:   string,
  topicId: string,
): Promise<{ error?: string }> {
  const supabase = getServerClient();

  // Mark the log entry as overridden
  const { error: logError } = await supabase
    .from('brand_safety_log')
    .update({ overall_passed: true } as never)
    .eq('id', logId);

  if (logError) return { error: logError.message };

  // Move the topic to the next pipeline step ('generating')
  const { error: topicError } = await supabase
    .from('trending_topics')
    .update({ status: 'generating' } as never)
    .eq('id', topicId)
    .eq('status', 'brand_checking'); // only if still in brand_checking state

  if (topicError) {
    console.warn('[brand-safety/actions] Could not advance topic status:', topicError.message);
  }

  revalidatePath('/brand-safety');
  return {};
}

// ── Keyword blocklist ──────────────────────────────────────────────────────
export async function addBlockedKeyword(keyword: string): Promise<{ error?: string }> {
  const supabase = getServerClient();
  const trimmed = keyword.trim().toLowerCase();
  if (!trimmed) return { error: 'Keyword cannot be empty.' };

  const { data: existingRaw } = await supabase
    .from('config')
    .select('value')
    .eq('key', 'keyword_blocklist')
    .single() as unknown as { data: { value: unknown } | null; error: unknown };

  const currentList: string[] = Array.isArray(existingRaw?.value) ? existingRaw.value as string[] : [];
  if (currentList.includes(trimmed)) return { error: 'Keyword already in list.' };

  const newList = [...currentList, trimmed];

  const { error } = await supabase
    .from('config')
    .upsert({ key: 'keyword_blocklist', value: newList, updated_at: new Date().toISOString() } as never, { onConflict: 'key' });

  if (error) return { error: error.message };
  revalidatePath('/brand-safety');
  return {};
}

export async function deleteBlockedKeyword(keyword: string): Promise<{ error?: string }> {
  const supabase = getServerClient();

  const { data: existingRaw } = await supabase
    .from('config')
    .select('value')
    .eq('key', 'keyword_blocklist')
    .single() as unknown as { data: { value: unknown } | null; error: unknown };

  const currentList: string[] = Array.isArray(existingRaw?.value) ? existingRaw.value as string[] : [];
  const newList = currentList.filter(k => k !== keyword);

  const { error } = await supabase
    .from('config')
    .upsert({ key: 'keyword_blocklist', value: newList, updated_at: new Date().toISOString() } as never, { onConflict: 'key' });

  if (error) return { error: error.message };
  revalidatePath('/brand-safety');
  return {};
}
