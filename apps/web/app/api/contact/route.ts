/**
 * POST /api/contact
 *
 * Accepts: { name, email, subject, message }
 * Sends an email via the Resend REST API to the editorial inbox.
 * Returns: 200 { ok: true } | 400/500 { error: string }
 */

import { NextRequest, NextResponse } from 'next/server';

const RESEND_API_KEY      = process.env.RESEND_API_KEY      ?? '';
const PUBLICATION_NAME    = process.env.PUBLICATION_NAME    ?? 'theNewslane';
const PUBLICATION_DOMAIN  = process.env.PUBLICATION_DOMAIN  ?? '';

const TO_EMAIL   = PUBLICATION_DOMAIN
  ? `editorial@${PUBLICATION_DOMAIN}`
  : 'editorial@thenewslane.com';

const FROM_EMAIL = PUBLICATION_DOMAIN
  ? `${PUBLICATION_NAME} <noreply@${PUBLICATION_DOMAIN}>`
  : `${PUBLICATION_NAME} <noreply@thenewslane.com>`;

export async function POST(req: NextRequest) {
  // ── Validate API key ──────────────────────────────────────────────────
  if (!RESEND_API_KEY) {
    console.error('[contact/route] RESEND_API_KEY is not set');
    return NextResponse.json({ error: 'Email service is not configured.' }, { status: 500 });
  }

  // ── Parse body ────────────────────────────────────────────────────────
  let body: { name?: unknown; email?: unknown; subject?: unknown; message?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 });
  }

  const name    = typeof body.name    === 'string' ? body.name.trim()    : '';
  const email   = typeof body.email   === 'string' ? body.email.trim()   : '';
  const subject = typeof body.subject === 'string' ? body.subject.trim() : 'General Enquiry';
  const message = typeof body.message === 'string' ? body.message.trim() : '';

  if (!name || !email || !message) {
    return NextResponse.json({ error: 'name, email, and message are required.' }, { status: 400 });
  }

  // Basic email format check
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: 'Invalid email address.' }, { status: 400 });
  }

  // ── Build email HTML ──────────────────────────────────────────────────
  const html = `
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
  <h2 style="color: #AD2D37; margin: 0 0 16px;">${PUBLICATION_NAME} — Contact Form</h2>
  <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
    <tr><td style="padding: 8px 12px; background: #f5f5f5; font-weight: 600; width: 100px;">From</td>
        <td style="padding: 8px 12px;">${escapeHtml(name)} &lt;${escapeHtml(email)}&gt;</td></tr>
    <tr><td style="padding: 8px 12px; background: #f5f5f5; font-weight: 600;">Subject</td>
        <td style="padding: 8px 12px;">${escapeHtml(subject)}</td></tr>
  </table>
  <div style="background: #fafafa; border: 1px solid #eee; border-radius: 6px; padding: 16px; white-space: pre-wrap; font-size: 15px; line-height: 1.6; color: #333;">
${escapeHtml(message)}
  </div>
  <p style="color: #999; font-size: 12px; margin-top: 24px;">
    Sent via the ${PUBLICATION_NAME} contact form.
    Reply directly to this email to respond to ${escapeHtml(name)}.
  </p>
</div>`.trim();

  const text = `From: ${name} <${email}>\nSubject: ${subject}\n\n${message}`;

  // ── Call Resend API ───────────────────────────────────────────────────
  try {
    const resendRes = await fetch('https://api.resend.com/emails', {
      method:  'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_API_KEY}`,
        'Content-Type':  'application/json',
      },
      body: JSON.stringify({
        from:        FROM_EMAIL,
        to:          [TO_EMAIL],
        reply_to:    email,
        subject:     `[Contact] ${subject} — from ${name}`,
        html,
        text,
      }),
    });

    if (!resendRes.ok) {
      const err = await resendRes.json().catch(() => ({}));
      console.error('[contact/route] Resend error:', err);
      return NextResponse.json(
        { error: 'Failed to send email. Please try again later.' },
        { status: 502 },
      );
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('[contact/route] Network error:', err);
    return NextResponse.json(
      { error: 'Failed to send email. Please try again later.' },
      { status: 502 },
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function escapeHtml(str: string): string {
  return str
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}
