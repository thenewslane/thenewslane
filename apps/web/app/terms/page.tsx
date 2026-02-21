/**
 * Terms of Service — /terms  (server component, static)
 */

import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';

const PUBLICATION_NAME   = process.env.PUBLICATION_NAME   ?? 'theNewslane';
const PUBLICATION_DOMAIN = process.env.PUBLICATION_DOMAIN ?? '';

export const metadata: Metadata = {
  title:       `Terms of Service · ${PUBLICATION_NAME}`,
  description: `Terms and conditions for using ${PUBLICATION_NAME}.`,
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

const lastUpdated = 'February 2026';

export default function TermsPage() {
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
        Terms of Service
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
        Please read these Terms of Service (&ldquo;Terms&rdquo;) carefully before
        using {PUBLICATION_NAME}{PUBLICATION_DOMAIN ? ` (${PUBLICATION_DOMAIN})` : ''}{' '}
        (the &ldquo;Service&rdquo;). By accessing or using the Service, you agree
        to be bound by these Terms. If you do not agree, do not use the Service.
      </p>

      <h2 style={h2Style}>1. Eligibility</h2>
      <p style={pStyle}>
        You must be at least 13 years old to use the Service. By creating an account
        you represent that you meet this age requirement. Users between 13 and 17 must
        have parental or guardian consent where required by applicable law.
      </p>

      <h2 style={h2Style}>2. Accounts</h2>
      <p style={pStyle}>
        You are responsible for maintaining the confidentiality of your account
        credentials and for all activity that occurs under your account. You agree
        to notify us immediately of any unauthorised use of your account.
      </p>
      <p style={pStyle}>
        You may not create accounts using automated methods, share your account with
        others, or use another person&apos;s account without their permission.
      </p>

      <h2 style={h2Style}>3. User Content &amp; Submissions</h2>
      <p style={pStyle}>
        You may submit topic suggestions and other content (&ldquo;User Content&rdquo;)
        to the Service. By submitting User Content, you grant {PUBLICATION_NAME} a
        non-exclusive, worldwide, royalty-free licence to use, display, and distribute
        that content in connection with the Service.
      </p>
      <p style={pStyle}>
        You represent that you own or have the necessary rights to submit User Content
        and that it does not violate any third-party rights or applicable law.
      </p>
      <p style={pStyle}>You may not submit content that:</p>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Is false, misleading, or deceptive',
          'Infringes any intellectual property rights',
          'Contains viruses, malware, or other harmful code',
          'Harasses, threatens, or discriminates against any person',
          'Violates any applicable law or regulation',
          'Constitutes spam or unsolicited commercial communications',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>
      <p style={pStyle}>
        We reserve the right to remove any User Content at our discretion and to
        terminate accounts that violate these Terms.
      </p>

      <h2 style={h2Style}>4. AI-Generated Content</h2>
      <p style={pStyle}>
        Articles and other content on {PUBLICATION_NAME} are substantially generated
        by artificial intelligence. We make reasonable efforts to ensure accuracy, but
        AI-generated content may contain errors or omissions. The Service is not a
        substitute for professional advice.{PUBLICATION_NAME} makes no warranty as to
        the accuracy, completeness, or timeliness of any content.
      </p>
      <p style={pStyle}>
        All AI-generated content is labelled as such. You should verify important
        information from primary sources before relying on it.
      </p>

      <h2 style={h2Style}>5. Intellectual Property</h2>
      <p style={pStyle}>
        The Service and all content created by or for {PUBLICATION_NAME} (excluding
        User Content) are owned by {PUBLICATION_NAME} and protected by copyright and
        other intellectual property laws. You may not reproduce, distribute, or create
        derivative works without our prior written consent.
      </p>
      <p style={pStyle}>
        You may share links to individual articles. Brief quotations for commentary or
        criticism are permitted under fair use / fair dealing principles.
      </p>

      <h2 style={h2Style}>6. Prohibited Uses</h2>
      <p style={pStyle}>You agree not to:</p>
      <ul style={{ paddingLeft: 'var(--spacing-5)', margin: '0 0 var(--spacing-4)' }}>
        {[
          'Scrape, crawl, or systematically download content from the Service without written permission',
          'Attempt to gain unauthorised access to any part of the Service',
          'Interfere with or disrupt the Service or servers',
          'Use the Service to transmit unsolicited advertising or spam',
          'Impersonate any person or entity',
          'Use automated tools to create multiple accounts',
        ].map((item, i) => <li key={i} style={liStyle}>{item}</li>)}
      </ul>

      <h2 style={h2Style}>7. Privacy</h2>
      <p style={pStyle}>
        Your use of the Service is also governed by our{' '}
        <Link href="/privacy" style={{ color: 'var(--color-link)' }}>Privacy Policy</Link>,
        which is incorporated into these Terms by reference.
      </p>

      <h2 style={h2Style}>8. Disclaimers</h2>
      <p style={pStyle}>
        THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; WITHOUT WARRANTIES OF ANY KIND,
        EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT. WE DO NOT WARRANT THAT
        THE SERVICE WILL BE UNINTERRUPTED, ERROR-FREE, OR FREE OF VIRUSES OR OTHER
        HARMFUL COMPONENTS.
      </p>

      <h2 style={h2Style}>9. Limitation of Liability</h2>
      <p style={pStyle}>
        TO THE FULLEST EXTENT PERMITTED BY LAW, {PUBLICATION_NAME.toUpperCase()} SHALL
        NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE
        DAMAGES ARISING OUT OF OR RELATED TO YOUR USE OF THE SERVICE. OUR TOTAL
        CUMULATIVE LIABILITY SHALL NOT EXCEED £100 (OR THE EQUIVALENT IN YOUR LOCAL
        CURRENCY).
      </p>

      <h2 style={h2Style}>10. Modifications to the Service &amp; Terms</h2>
      <p style={pStyle}>
        We reserve the right to modify or discontinue the Service at any time without
        notice. We may update these Terms at any time. Continued use of the Service
        after changes constitutes acceptance of the new Terms.
      </p>

      <h2 style={h2Style}>11. Governing Law</h2>
      <p style={pStyle}>
        These Terms shall be governed by and construed in accordance with the laws of
        England and Wales, without regard to conflict of law principles. Any disputes
        shall be subject to the exclusive jurisdiction of the courts of England and
        Wales, except where local consumer protection laws require otherwise.
      </p>

      <h2 style={h2Style}>12. Contact</h2>
      <p style={pStyle}>
        For questions about these Terms, please contact us via our{' '}
        <Link href="/contact" style={{ color: 'var(--color-link)' }}>contact page</Link>
        {PUBLICATION_DOMAIN && (
          <> or at{' '}
            <a href={`mailto:legal@${PUBLICATION_DOMAIN}`} style={{ color: 'var(--color-link)' }}>
              legal@{PUBLICATION_DOMAIN}
            </a>
          </>
        )}
        .
      </p>
    </div>
  );
}
