'use client';

import React, { useState } from 'react';

export interface AgeGateProps {
  /**
   * Called when the user's age is ≥ 13.
   * `isMinor` is true for ages 13–17, false for 18+.
   */
  onVerified: (isMinor: boolean) => void;
  /** Called when the user is under 13 (access blocked). */
  onBlocked:  () => void;
}

const CURRENT_YEAR = new Date().getFullYear();
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function calcAge(birthMonth: number, birthYear: number): number {
  const now   = new Date();
  const bDay  = new Date(birthYear, birthMonth - 1, 1);
  let   age   = now.getFullYear() - bDay.getFullYear();
  const hasBirthMonthPassed = now.getMonth() + 1 >= birthMonth;
  if (!hasBirthMonthPassed) age -= 1;
  return age;
}

const labelStyle: React.CSSProperties = {
  display:    'block',
  fontSize:   '13px',
  fontWeight: 600,
  fontFamily: 'var(--font-body)',
  color:      'var(--color-text-primary-light)',
  marginBottom: 'var(--spacing-1)',
};

const selectStyle: React.CSSProperties = {
  width:           '100%',
  padding:         'var(--spacing-2) var(--spacing-3)',
  borderRadius:    'var(--radius-small)',
  border:          '1px solid rgba(0,0,0,.18)',
  backgroundColor: 'var(--color-card-light)',
  color:           'var(--color-text-primary-light)',
  fontSize:        '14px',
  fontFamily:      'var(--font-body)',
  appearance:      'none' as const,
  cursor:          'pointer',
};

export function AgeGate({ onVerified, onBlocked }: AgeGateProps) {
  const [month, setMonth]     = useState<string>('');
  const [year,  setYear]      = useState<string>('');
  const [error, setError]     = useState<string | null>(null);
  const [blocked, setBlocked] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const m = parseInt(month, 10);
    const y = parseInt(year,  10);

    if (!month || !year) {
      setError('Please select your birth month and year.');
      return;
    }

    if (y > CURRENT_YEAR || y < CURRENT_YEAR - 120) {
      setError('Please enter a valid birth year.');
      return;
    }

    const age = calcAge(m, y);

    if (age < 13) {
      setBlocked(true);
      onBlocked();
      return;
    }

    onVerified(age < 18);
  }

  if (blocked) {
    return (
      <div
        role="alert"
        style={{
          padding:         'var(--spacing-8)',
          textAlign:       'center',
          fontFamily:      'var(--font-body)',
          color:           'var(--color-text-primary-light)',
          backgroundColor: 'var(--color-card-light)',
          borderRadius:    'var(--radius-large)',
          maxWidth:        400,
          margin:          '0 auto',
        }}
      >
        <svg width="40" height="40" viewBox="0 0 24 24" fill="var(--color-primary)" aria-hidden style={{ marginBottom: 'var(--spacing-3)' }}>
          <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm-1-5h2v2h-2zm0-8h2v6h-2z"/>
        </svg>
        <h2 style={{ margin: '0 0 var(--spacing-2)', fontSize: '18px', fontFamily: 'var(--font-heading)', fontWeight: 700 }}>
          Access Restricted
        </h2>
        <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-text-secondary-light)', lineHeight: 1.6 }}>
          You must be at least 13 years old to access this content.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        padding:         'var(--spacing-8)',
        fontFamily:      'var(--font-body)',
        backgroundColor: 'var(--color-card-light)',
        borderRadius:    'var(--radius-large)',
        maxWidth:        360,
        margin:          '0 auto',
        boxShadow:       '0 4px 24px rgba(0,0,0,.1)',
      }}
    >
      <h2
        style={{
          margin:     '0 0 var(--spacing-1)',
          fontSize:   '20px',
          fontFamily: 'var(--font-heading)',
          fontWeight: 700,
          color:      'var(--color-text-primary-light)',
        }}
      >
        Age Verification
      </h2>
      <p
        style={{
          margin:     '0 0 var(--spacing-6)',
          fontSize:   '13px',
          lineHeight: 1.6,
          color:      'var(--color-text-secondary-light)',
        }}
      >
        Please enter your date of birth to continue.
      </p>

      <form onSubmit={handleSubmit} noValidate>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-3)', marginBottom: 'var(--spacing-4)' }}>
          {/* Month */}
          <div>
            <label htmlFor="age-gate-month" style={labelStyle}>Month</label>
            <select
              id="age-gate-month"
              value={month}
              onChange={e => setMonth(e.target.value)}
              style={selectStyle}
            >
              <option value="">Month</option>
              {MONTHS.map((m, i) => (
                <option key={m} value={String(i + 1)}>{m}</option>
              ))}
            </select>
          </div>

          {/* Year */}
          <div>
            <label htmlFor="age-gate-year" style={labelStyle}>Year</label>
            <select
              id="age-gate-year"
              value={year}
              onChange={e => setYear(e.target.value)}
              style={selectStyle}
            >
              <option value="">Year</option>
              {Array.from({ length: 110 }, (_, i) => CURRENT_YEAR - 13 - i).map(y => (
                <option key={y} value={String(y)}>{y}</option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <p
            role="alert"
            style={{
              margin:     '0 0 var(--spacing-3)',
              fontSize:   '12px',
              color:      'var(--color-viral-tier-1)',
              fontWeight: 500,
            }}
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          style={{
            width:           '100%',
            padding:         'var(--spacing-3)',
            borderRadius:    'var(--radius-small)',
            border:          'none',
            backgroundColor: 'var(--color-primary)',
            color:           '#fff',
            fontSize:        '14px',
            fontWeight:      700,
            fontFamily:      'var(--font-body)',
            cursor:          'pointer',
            letterSpacing:   '0.02em',
          }}
        >
          Continue
        </button>
      </form>
    </div>
  );
}
