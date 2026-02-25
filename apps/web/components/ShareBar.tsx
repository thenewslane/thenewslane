'use client';

/**
 * ShareBar — social sharing affordances for article pages.
 *
 * Platforms: WhatsApp, Snapchat, X (Twitter), Copy Link.
 * Uses native share URLs (no SDKs). Copy Link uses the Clipboard API
 * with a brief "Copied!" confirmation.
 */

import React, { useState, useCallback } from 'react';

interface ShareBarProps {
  url: string;
  title: string;
}

interface ShareButton {
  label: string;
  icon: React.ReactNode;
  getHref: (url: string, title: string) => string;
  color: string;
}

function WhatsAppIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
    </svg>
  );
}

function SnapchatIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12.206.793c.99 0 4.347.276 5.93 3.821.529 1.193.403 3.219.299 4.847l-.003.06c-.012.18-.022.345-.03.51.075.045.203.09.401.09.3-.016.659-.12.922-.214.12-.042.195-.065.273-.065a.56.56 0 01.559.374c.075.18.038.39-.12.54-.39.36-.93.546-1.442.546-.18 0-.36-.03-.51-.06a4.43 4.43 0 00-.583-.06c-.12 0-.24.015-.36.045-.24.06-.42.225-.54.45-.27.48-.676 1.093-1.648 1.575a7.93 7.93 0 01-1.56.553c-.21.053-.42.106-.48.174-.075.09-.045.27.045.555.009.03.015.06.021.09.12.375-.24.75-.735.855-.12.03-.264.045-.42.045-.21 0-.45-.03-.66-.06a4.5 4.5 0 00-.78-.075c-.24 0-.48.03-.72.09-.48.12-.87.42-1.29.75a4.28 4.28 0 01-2.505.975c-.075 0-.15 0-.225-.015a4.29 4.29 0 01-2.55-.99c-.42-.33-.81-.63-1.29-.75a3.45 3.45 0 00-.72-.09c-.3 0-.57.03-.78.075-.21.03-.45.06-.66.06-.15 0-.3-.015-.42-.045-.54-.12-.87-.48-.735-.855.006-.03.012-.06.021-.09.09-.285.12-.465.045-.555-.06-.068-.27-.121-.48-.174a7.93 7.93 0 01-1.56-.553c-.972-.482-1.378-1.095-1.648-1.575-.12-.225-.3-.39-.54-.45a2.07 2.07 0 00-.36-.045c-.195 0-.39.015-.583.06-.15.03-.33.06-.51.06-.54 0-1.065-.195-1.44-.546-.12-.12-.165-.315-.12-.51a.56.56 0 01.56-.374c.078 0 .153.023.273.065.263.094.621.198.921.214.199 0 .327-.045.402-.09a13.3 13.3 0 01-.034-.57c-.1-1.628-.226-3.654.302-4.847C4.64 1.069 7.997.793 8.987.793h.013z" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

const SHARE_BUTTONS: ShareButton[] = [
  {
    label: 'WhatsApp',
    icon: <WhatsAppIcon />,
    getHref: (url, title) =>
      `https://api.whatsapp.com/send?text=${encodeURIComponent(`${title} ${url}`)}`,
    color: '#25D366',
  },
  {
    label: 'Snapchat',
    icon: <SnapchatIcon />,
    getHref: (url) =>
      `https://www.snapchat.com/scan?attachmentUrl=${encodeURIComponent(url)}`,
    color: '#FFFC00',
  },
  {
    label: 'X',
    icon: <XIcon />,
    getHref: (url, title) =>
      `https://x.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`,
    color: '#000000',
  },
];

export function ShareBar({ url, title }: ShareBarProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textArea = document.createElement('textarea');
      textArea.value = url;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [url]);

  return (
    <div
      role="group"
      aria-label="Share this article"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-2)',
        flexWrap: 'wrap',
      }}
    >
      <span
        style={{
          fontSize: 12,
          fontWeight: 600,
          fontFamily: 'var(--font-body)',
          color: 'var(--color-text-muted-light)',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginRight: 'var(--spacing-1)',
        }}
      >
        Share
      </span>

      {SHARE_BUTTONS.map((btn) => (
        <a
          key={btn.label}
          href={btn.getHref(url, title)}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Share on ${btn.label}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            padding: '8px 14px',
            borderRadius: 'var(--radius-full, 9999px)',
            border: '1px solid rgba(0,0,0,.1)',
            backgroundColor: 'var(--color-card-light)',
            color: 'var(--color-text-primary-light)',
            fontSize: 13,
            fontWeight: 600,
            fontFamily: 'var(--font-body)',
            textDecoration: 'none',
            transition: 'all 0.15s ease',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = btn.color;
            e.currentTarget.style.color = btn.label === 'Snapchat' ? '#000' : '#fff';
            e.currentTarget.style.borderColor = btn.color;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--color-card-light)';
            e.currentTarget.style.color = 'var(--color-text-primary-light)';
            e.currentTarget.style.borderColor = 'rgba(0,0,0,.1)';
          }}
        >
          {btn.icon}
          <span className="hidden sm:inline">{btn.label}</span>
        </a>
      ))}

      <button
        onClick={handleCopy}
        aria-label={copied ? 'Link copied!' : 'Copy link'}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6,
          padding: '8px 14px',
          borderRadius: 'var(--radius-full, 9999px)',
          border: copied
            ? '1px solid var(--color-primary)'
            : '1px solid rgba(0,0,0,.1)',
          backgroundColor: copied ? 'var(--color-primary)' : 'var(--color-card-light)',
          color: copied ? '#fff' : 'var(--color-text-primary-light)',
          fontSize: 13,
          fontWeight: 600,
          fontFamily: 'var(--font-body)',
          cursor: 'pointer',
          transition: 'all 0.15s ease',
          whiteSpace: 'nowrap',
        }}
      >
        {copied ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <LinkIcon />
        )}
        <span className="hidden sm:inline">
          {copied ? 'Copied!' : 'Copy link'}
        </span>
      </button>
    </div>
  );
}
