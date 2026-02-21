'use client';

/**
 * Contact page — /contact
 *
 * Form fields: name, email, subject (dropdown), message.
 * Submits via POST to /api/contact which calls the Resend API.
 */

import React, { useState } from 'react';
import {
  AuthFormCard,
  inputStyle,
  primaryBtnStyle,
  labelStyle,
  errorStyle,
} from '@/components/AuthFormCard';

const SUBJECTS = [
  'General Enquiry',
  'Correction Request',
  'Privacy Request',
  'Business Inquiry',
  'Press & Media',
  'Other',
] as const;

type Subject = (typeof SUBJECTS)[number];

export default function ContactPage() {
  const [name,      setName]      = useState('');
  const [email,     setEmail]     = useState('');
  const [subject,   setSubject]   = useState<Subject>('General Enquiry');
  const [message,   setMessage]   = useState('');
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim() || !email.trim() || !message.trim()) {
      setError('Please fill in all required fields.');
      return;
    }

    setLoading(true);

    try {
      const res = await fetch('/api/contact', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          name:    name.trim(),
          email:   email.trim(),
          subject,
          message: message.trim(),
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.error ?? `Request failed (${res.status})`);
      }

      setSubmitted(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <AuthFormCard
        title="Message sent!"
        subtitle="Thanks for reaching out. We aim to respond within two business days."
      >
        <div style={{ textAlign: 'center', padding: 'var(--spacing-4) 0' }}>
          <div
            style={{
              display:         'inline-flex',
              alignItems:      'center',
              justifyContent:  'center',
              width:           72,
              height:          72,
              borderRadius:    '50%',
              backgroundColor: 'color-mix(in srgb, var(--color-viral-tier-3) 15%, transparent)',
              marginBottom:    'var(--spacing-4)',
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--color-viral-tier-3)" aria-hidden>
              <path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/>
            </svg>
          </div>
          <button
            onClick={() => { setSubmitted(false); setName(''); setEmail(''); setMessage(''); setSubject('General Enquiry'); }}
            style={{
              display:         'block',
              width:           '100%',
              padding:         'var(--spacing-2) var(--spacing-4)',
              borderRadius:    'var(--radius-small)',
              border:          '1.5px solid rgba(0,0,0,.12)',
              backgroundColor: 'transparent',
              color:           'var(--color-text-secondary-light)',
              fontSize:        '14px',
              fontWeight:      600,
              fontFamily:      'var(--font-body)',
              cursor:          'pointer',
            }}
          >
            Send another message
          </button>
        </div>
      </AuthFormCard>
    );
  }

  return (
    <AuthFormCard
      title="Contact us"
      subtitle="Got a question, correction, or business enquiry? We'd love to hear from you."
      maxWidth={560}
    >
      <form onSubmit={handleSubmit} noValidate>
        {error && <p role="alert" style={errorStyle}>{error}</p>}

        {/* Name */}
        <div style={{ marginBottom: 'var(--spacing-4)' }}>
          <label htmlFor="contact-name" style={labelStyle}>
            Full name <span style={{ color: 'var(--color-primary)' }}>*</span>
          </label>
          <input
            id="contact-name"
            type="text"
            required
            maxLength={100}
            value={name}
            onChange={e => setName(e.target.value)}
            style={inputStyle}
            placeholder="Jane Smith"
            autoComplete="name"
          />
        </div>

        {/* Email */}
        <div style={{ marginBottom: 'var(--spacing-4)' }}>
          <label htmlFor="contact-email" style={labelStyle}>
            Email address <span style={{ color: 'var(--color-primary)' }}>*</span>
          </label>
          <input
            id="contact-email"
            type="email"
            required
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={inputStyle}
            placeholder="you@example.com"
            autoComplete="email"
          />
        </div>

        {/* Subject */}
        <div style={{ marginBottom: 'var(--spacing-4)' }}>
          <label htmlFor="contact-subject" style={labelStyle}>Subject</label>
          <select
            id="contact-subject"
            value={subject}
            onChange={e => setSubject(e.target.value as Subject)}
            style={{
              ...inputStyle,
              appearance:      'auto',
              backgroundColor: '#fff',
            }}
          >
            {SUBJECTS.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {/* Message */}
        <div style={{ marginBottom: 'var(--spacing-6)' }}>
          <label htmlFor="contact-message" style={labelStyle}>
            Message <span style={{ color: 'var(--color-primary)' }}>*</span>
          </label>
          <textarea
            id="contact-message"
            required
            rows={6}
            maxLength={2000}
            value={message}
            onChange={e => setMessage(e.target.value)}
            style={{
              ...inputStyle,
              resize:     'vertical',
              lineHeight: 1.6,
            }}
            placeholder="Tell us what's on your mind…"
          />
          <p style={{ margin: '4px 0 0', fontSize: '11px', fontFamily: 'var(--font-body)', color: 'var(--color-text-muted-light)' }}>
            {message.length}/2000
          </p>
        </div>

        <button
          type="submit"
          disabled={loading || !name.trim() || !email.trim() || !message.trim()}
          style={{
            ...primaryBtnStyle,
            opacity: loading || !name.trim() || !email.trim() || !message.trim() ? 0.65 : 1,
            cursor:  loading || !name.trim() || !email.trim() || !message.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Sending…' : 'Send Message'}
        </button>

        <p
          style={{
            textAlign:  'center',
            marginTop:  'var(--spacing-3)',
            fontSize:   '12px',
            fontFamily: 'var(--font-body)',
            color:      'var(--color-text-muted-light)',
            lineHeight: 1.5,
          }}
        >
          We typically respond within 2 business days.
        </p>
      </form>
    </AuthFormCard>
  );
}
