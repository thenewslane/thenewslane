/**
 * Privacy Policy — /privacy  (server component, static)
 *
 * Sections:
 *   1. Introduction
 *   2. Information We Collect
 *   3. How We Use Your Information
 *   4. Cookies & Tracking Technologies
 *   5. Third-Party Services
 *   6. Data Retention
 *   7. GDPR Rights (EEA/UK residents)
 *   8. CCPA Rights (California residents)
 *   9. COPPA — Children's Privacy
 *  10. Changes to This Policy
 *  11. Contact
 */

import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';

const PUBLICATION_NAME   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const PUBLICATION_DOMAIN = process.env.PUBLICATION_DOMAIN ?? '';

export const metadata: Metadata = {
  title:       `Privacy Policy · ${PUBLICATION_NAME}`,
  description: `How ${PUBLICATION_NAME} collects, uses, and protects your personal information.`,
};

const h2Style: React.CSSProperties = {
  fontFamily:  'var(--font-heading)',
  fontSize:    'clamp(17px, 2.5vw, 21px)',
  fontWeight:  700,
  color:       'var(--color-text-primary-light)',
  margin:      'var(--spacing-8) 0 var(--spacing-3)',
};

const pStyle: React.CSSProperties = {
  fontFamily: 'var(--font-body)',
  fontSize:   '15px',
  lineHeight: 1.75,
  color:      'var(--color-text-secondary-light)',
  margin:     '0 0 var(--spacing-4)',
};

const liStyle: React.CSSProperties = {
  fontFamily:   'var(--font-body)',
  fontSize:     '15px',
  lineHeight:   1.7,
  color:        'var(--color-text-secondary-light)',
  marginBottom: 'var(--spacing-2)',
};

const calloutStyle: React.CSSProperties = {
  padding:         'var(--spacing-4)',
  borderRadius:    'var(--radius-small)',
  backgroundColor: 'color-mix(in srgb, var(--color-secondary) 7%, transparent)',
  borderLeft:      '3px solid var(--color-secondary)',
  marginBottom:    'var(--spacing-6)',
};

const lastUpdated = 'February 2026';

export default function PrivacyPage() {
  return (
    <div
      style={{
        maxWidth: 720,
        margin:   '0 auto',
        padding:  'var(--spacing-12) var(--spacing-4) var(--spacing-16)',
      }}
    >
      <h1
        style={{
          fontFamily:  'var(--font-heading)',
          fontSize:    'clamp(26px, 5vw, 40px)',
          fontWeight:  800,
          color:       'var(--color-text-primary-light)',
          margin:      '0 0 var(--spacing-2)',
        }}
      >
        Privacy Policy
      </h1>
      <p
        style={{
          fontFamily: 'var(--font-body)',
          fontSize:   '13px',
          color:      'var(--color-text-muted-light)',
          margin:     '0 0 var(--spacing-6)',
        }}
      >
        Last updated: {lastUpdated}
      </p>
      <p style={pStyle}>
        {PUBLICATION_NAME} (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;)
        operates{PUBLICATION_DOMAIN ? ` ${PUBLICATION_DOMAIN}` : ' this website'} (the
        &ldquo;Service&rdquo;). This Privacy Policy explains how we collect, use,
        disclose, and protect your information when you use our Service.
      </p>
      <p style={pStyle}>
        By using {PUBLICATION_NAME} you agree to the practices described in this policy.
        If you do not agree, please do not use the Service.
      </p>

      {/* 1. Information We Collect */}
      <h2 style={h2Style}>1. Information We Collect</h2>
      <p style={pStyle}><strong>Information you provide:</strong></p>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Account registration: email address, display name, and age verification (date of birth is not stored — only an age-band flag).',
          'Topic submissions: title, description, and optional source URL.',
          'Contact form messages: name, email, subject, and message content.',
          'Preference settings: category preferences, notification opt-ins, and digest frequency.',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>
      <p style={pStyle}><strong>Information collected automatically:</strong></p>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Log data: IP address, browser type, pages visited, time and date of visit, referring URLs.',
          'Device data: device type, operating system, screen resolution.',
          'Cookies and similar technologies (see Section 4).',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>

      {/* 2. How We Use */}
      <h2 style={h2Style}>2. How We Use Your Information</h2>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'To provide and personalise the Service, including your category feed and notification preferences.',
          'To process and respond to topic submissions.',
          'To communicate with you about your account, including security alerts.',
          'To send email digests where you have opted in.',
          'To investigate abuse, enforce our Terms of Service, and comply with legal obligations.',
          'To improve the Service through aggregated, anonymised analytics.',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>
      <p style={pStyle}>
        We do not sell your personal information to third parties for their
        own marketing purposes. See Section 8 for California-specific disclosures.
      </p>

      {/* 3. Legal Basis (GDPR) */}
      <h2 style={h2Style}>3. Legal Basis for Processing (GDPR)</h2>
      <p style={pStyle}>
        If you are located in the European Economic Area (EEA) or the UK, we
        process your personal data under the following legal bases:
      </p>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Contract performance — to create and manage your account and deliver the Service.',
          'Legitimate interests — to operate, secure, and improve the Service; to send transactional communications.',
          'Consent — for optional email digests and non-essential cookies.',
          'Legal obligation — to comply with applicable laws and regulations.',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>

      {/* 4. Cookies */}
      <h2 style={h2Style}>4. Cookies &amp; Tracking Technologies</h2>
      <p style={pStyle}>
        We use the following categories of cookies:
      </p>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Strictly necessary — authentication session tokens (Supabase). Cannot be disabled.',
          'Functional — your preference settings and consent choices stored locally.',
          'Analytics — aggregated, anonymised page-view data. Requires your consent.',
          'Advertising — we do not currently use advertising cookies.',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>
      <p style={pStyle}>
        You can manage your cookie preferences at any time via the Cookie Settings
        link in our site footer.
      </p>

      {/* 5. Third-Party Services */}
      <h2 style={h2Style}>5. Third-Party Services</h2>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Supabase — authentication, database, and file storage. Processes data in the EU.',
          'Resend — transactional email delivery. Processes your email address for sending only.',
          'Anthropic / Claude — AI content generation. Topic data (no user PII) is sent to the API.',
          "Vercel — hosting and edge functions. Subject to Vercel's own privacy policy.",
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>
      <p style={pStyle}>
        We do not share your personal information with any third party except as
        necessary to operate the Service or as required by law.
      </p>

      {/* 6. Data Retention */}
      <h2 style={h2Style}>6. Data Retention</h2>
      <p style={pStyle}>
        We retain your account data for as long as your account is active or as
        needed to provide the Service. You may request deletion at any time via
        Settings &rarr; Delete Account, or by emailing us (see Section 11).
        Log data is retained for up to 90 days.
      </p>

      {/* 7. GDPR Rights */}
      <h2 style={h2Style}>7. Your Rights — EEA &amp; UK Residents (GDPR)</h2>
      <div style={calloutStyle}>
        <p style={{ ...pStyle, margin: 0, fontWeight: 500 }}>
          If you are located in the EEA or the United Kingdom, you have the
          following rights under the GDPR / UK GDPR:
        </p>
      </div>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Right of access — request a copy of the personal data we hold about you.',
          'Right to rectification — ask us to correct inaccurate or incomplete data.',
          'Right to erasure ("right to be forgotten") — request deletion of your personal data.',
          'Right to restriction of processing — ask us to limit how we use your data.',
          'Right to data portability — receive your data in a machine-readable format.',
          'Right to object — object to processing based on legitimate interests or for direct marketing.',
          'Right to withdraw consent — where we rely on consent, you may withdraw it at any time.',
          'Right to lodge a complaint — with your national data protection authority.',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>
      <p style={pStyle}>
        To exercise any of these rights, please contact us using the details in
        Section 11. We will respond within 30 days.
      </p>

      {/* 8. CCPA */}
      <h2 style={h2Style}>8. Your Rights — California Residents (CCPA / CPRA)</h2>
      <div style={calloutStyle}>
        <p style={{ ...pStyle, margin: 0, fontWeight: 500 }}>
          If you are a California resident, the California Consumer Privacy Act
          (CCPA) as amended by the CPRA grants you the following rights:
        </p>
      </div>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Right to know — the categories and specific pieces of personal information we have collected about you.',
          'Right to know — the categories of sources from which we collected your information.',
          'Right to know — the business or commercial purpose for collecting or sharing your information.',
          'Right to know — the categories of third parties with whom we share your information.',
          'Right to delete — request deletion of personal information we have collected from you, subject to certain exceptions.',
          'Right to correct — request correction of inaccurate personal information.',
          'Right to opt out of sale or sharing — we do not sell personal information. You may still submit a Do Not Sell or Share request via our Do Not Sell page.',
          'Right to limit use of sensitive personal information — we collect only minimal sensitive information (age band) and do not use it beyond account functionality.',
          'Right to non-discrimination — we will not discriminate against you for exercising any of these rights.',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>
      <p style={pStyle}>
        <strong>Categories of personal information collected:</strong> identifiers
        (email, IP address, device ID); internet/network activity (page views);
        inferences drawn from usage to create a profile (category preferences).
      </p>
      <p style={pStyle}>
        To submit a CCPA request, visit our{' '}
        <Link href="/do-not-sell" style={{ color: 'var(--color-link)' }}>
          Do Not Sell or Share My Personal Information
        </Link>{' '}
        page, or email{' '}
        {PUBLICATION_DOMAIN ? (
          <a href={`mailto:privacy@${PUBLICATION_DOMAIN}`} style={{ color: 'var(--color-link)' }}>
            privacy@{PUBLICATION_DOMAIN}
          </a>
        ) : 'our privacy team'}.
      </p>

      {/* 9. COPPA */}
      <h2 style={h2Style}>9. Children&apos;s Privacy (COPPA)</h2>
      <div style={calloutStyle}>
        <p style={{ ...pStyle, margin: 0, fontWeight: 500 }}>
          {PUBLICATION_NAME} is not directed to children under the age of 13 and
          does not knowingly collect personal information from children under 13.
        </p>
      </div>
      <p style={pStyle}>
        During registration, we ask users to confirm their age. Any user who
        indicates they are under 13 is blocked from creating an account. If we
        become aware that we have inadvertently collected personal information
        from a child under 13, we will delete it immediately.
      </p>
      <p style={pStyle}>
        Users who indicate they are between 13 and 17 (&ldquo;minors&rdquo;) have
        their account flagged accordingly. Content restrictions may apply. We do
        not use data from minor accounts for advertising or sell it to third
        parties. Parents or guardians who believe their child has created an
        account should contact us immediately using the details in Section 11.
      </p>
      <p style={pStyle}>
        If you are a parent or guardian and have questions about our children&apos;s
        privacy practices, please contact us at{' '}
        {PUBLICATION_DOMAIN ? (
          <a href={`mailto:privacy@${PUBLICATION_DOMAIN}`} style={{ color: 'var(--color-link)' }}>
            privacy@{PUBLICATION_DOMAIN}
          </a>
        ) : 'our privacy team'}.
      </p>

      {/* 10. Changes */}
      <h2 style={h2Style}>10. Changes to This Policy</h2>
      <p style={pStyle}>
        We may update this Privacy Policy periodically. When we do, we will
        update the &ldquo;Last updated&rdquo; date at the top of this page. For
        material changes, we will notify you via email (if you have an account)
        or by posting a prominent notice on the Service. Your continued use of
        the Service after such notice constitutes your acceptance of the changes.
      </p>

      {/* 11. Contact */}
      <h2 style={h2Style}>11. Contact</h2>
      <p style={pStyle}>
        For privacy-related requests or questions, please contact us:
      </p>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        <li style={liStyle}>
          <strong>Contact form:</strong>{' '}
          <Link href="/contact" style={{ color: 'var(--color-link)' }}>/contact</Link>
          {' '}(select &ldquo;Privacy Request&rdquo; as the subject)
        </li>
        {PUBLICATION_DOMAIN && (
          <li style={liStyle}>
            <strong>Email:</strong>{' '}
            <a href={`mailto:privacy@${PUBLICATION_DOMAIN}`} style={{ color: 'var(--color-link)' }}>
              privacy@{PUBLICATION_DOMAIN}
            </a>
          </li>
        )}
        <li style={liStyle}>
          <strong>Do Not Sell / CCPA opt-out:</strong>{' '}
          <Link href="/do-not-sell" style={{ color: 'var(--color-link)' }}>
            Do Not Sell or Share My Personal Information
          </Link>
        </li>
      </ul>
    </div>
  );
}
