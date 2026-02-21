'use server';

import { revalidatePath }   from 'next/cache';
import { getServerClient }  from '@platform/supabase';

const RESEND_API_KEY     = process.env.RESEND_API_KEY     ?? '';
const PUBLICATION_NAME   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const PUBLICATION_DOMAIN = process.env.PUBLICATION_DOMAIN ?? '';

// ── Approve ────────────────────────────────────────────────────────────────
export async function approveSubmission(id: string): Promise<{ error?: string }> {
  const supabase = getServerClient();
  const { error } = await supabase
    .from('user_submissions')
    .update({ status: 'approved', reviewed_at: new Date().toISOString() } as never)
    .eq('id', id);

  if (error) return { error: error.message };
  revalidatePath('/submissions');
  return {};
}

// ── Reject ─────────────────────────────────────────────────────────────────
export async function rejectSubmission(
  id: string,
  reason: string,
  submitterEmail: string,
  topicTitle: string,
): Promise<{ error?: string }> {
  const supabase = getServerClient();

  const { error } = await supabase
    .from('user_submissions')
    .update({
      status:          'rejected',
      moderator_notes: reason.trim() || null,
      reviewed_at:     new Date().toISOString(),
    } as never)
    .eq('id', id);

  if (error) return { error: error.message };

  // Send rejection email via Resend (non-fatal if it fails)
  if (RESEND_API_KEY && submitterEmail) {
    try {
      await fetch('https://api.resend.com/emails', {
        method:  'POST',
        headers: {
          'Authorization': `Bearer ${RESEND_API_KEY}`,
          'Content-Type':  'application/json',
        },
        body: JSON.stringify({
          from:    `${PUBLICATION_NAME} <noreply@${PUBLICATION_DOMAIN || 'thenewslane.com'}>`,
          to:      [submitterEmail],
          subject: `Your topic submission has been reviewed`,
          html: `<p>Hi,</p>
<p>Thank you for suggesting <strong>${topicTitle}</strong> to ${PUBLICATION_NAME}.</p>
<p>After review, we've decided not to proceed with this topic at this time.</p>
${reason ? `<p><strong>Reason:</strong> ${reason}</p>` : ''}
<p>You're welcome to submit another topic next week.</p>
<p>— The ${PUBLICATION_NAME} team</p>`,
        }),
      });
    } catch (e) {
      console.warn('[submissions/actions] Failed to send rejection email:', e);
    }
  }

  revalidatePath('/submissions');
  return {};
}
