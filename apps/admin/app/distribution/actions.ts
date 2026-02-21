'use server';

import { revalidatePath }  from 'next/cache';
import { getServerClient } from '@platform/supabase';

/** Reset a failed distribution entry to 'pending' so the pipeline retries it. */
export async function retryDistribution(id: string): Promise<{ error?: string }> {
  const supabase = getServerClient();

  // First fetch current retry_count
  const { data: row } = await supabase
    .from('distribution_log')
    .select('retry_count')
    .eq('id', id)
    .eq('status', 'failed')
    .single() as unknown as { data: { retry_count: number } | null; error: unknown };

  const { error } = await supabase
    .from('distribution_log')
    .update({
      status:        'pending',
      error_message: null,
      retry_count:   (row?.retry_count ?? 0) + 1,
    } as never)
    .eq('id', id)
    .eq('status', 'failed'); // only retry failed entries

  if (error) return { error: (error as { message: string }).message };
  revalidatePath('/distribution');
  return {};
}
