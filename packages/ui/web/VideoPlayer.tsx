import React, { useState } from 'react';
import { extractYouTubeId, extractVimeoId } from './utils';

export interface VideoPlayerProps {
  videoType:    'youtube_embed' | 'vimeo_embed' | 'kling_generated' | null;
  /** YouTube/Vimeo URL or bare video ID. Required when videoType is youtube_embed or vimeo_embed. */
  videoId?:     string;
  /** Direct video file URL. Required when videoType is kling_generated. */
  videoUrl?:    string;
  thumbnailUrl?: string;
  title:        string;
  /** Aspect ratio as a percentage (paddingTop trick). Default: 56.25 = 16/9. */
  aspectRatio?: number;
}

function PlayButton({ onClick }: { onClick: () => void }) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label="Play video"
      style={{
        position:        'absolute',
        inset:           0,
        display:         'flex',
        alignItems:      'center',
        justifyContent:  'center',
        background:      'none',
        border:          'none',
        cursor:          'pointer',
        backgroundColor: hovered ? 'rgba(0,0,0,.55)' : 'rgba(0,0,0,.35)',
        transition:      'background-color 0.15s ease',
      }}
    >
      <span
        style={{
          display:         'flex',
          alignItems:      'center',
          justifyContent:  'center',
          width:           56,
          height:          56,
          borderRadius:    '50%',
          backgroundColor: 'var(--color-primary)',
          transition:      'transform 0.15s ease',
          transform:       hovered ? 'scale(1.08)' : 'scale(1)',
        }}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="#fff" aria-hidden>
          <path d="M8 5v14l11-7z"/>
        </svg>
      </span>
    </button>
  );
}

function Shell({
  aspectRatio = 56.25,
  children,
}: {
  aspectRatio?: number;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        position:        'relative',
        width:           '100%',
        paddingTop:      `${aspectRatio}%`,
        backgroundColor: 'var(--color-background-dark)',
        borderRadius:    'var(--radius-medium)',
        overflow:        'hidden',
      }}
    >
      <div style={{ position: 'absolute', inset: 0 }}>{children}</div>
    </div>
  );
}

export function VideoPlayer({
  videoType,
  videoId,
  videoUrl,
  thumbnailUrl,
  title,
  aspectRatio = 56.25,
}: VideoPlayerProps) {
  const [playing, setPlaying] = useState(false);

  // ── YouTube ──────────────────────────────────────────────────────────────
  if (videoType === 'youtube_embed' && videoId) {
    const ytId = extractYouTubeId(videoId);
    const embedUrl = `https://www.youtube-nocookie.com/embed/${ytId}?autoplay=${playing ? 1 : 0}&rel=0&modestbranding=1`;

    if (!playing) {
      return (
        <Shell aspectRatio={aspectRatio}>
          {thumbnailUrl && (
            <img
              src={thumbnailUrl}
              alt={title}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          )}
          <PlayButton onClick={() => setPlaying(true)} />
        </Shell>
      );
    }

    return (
      <Shell aspectRatio={aspectRatio}>
        <iframe
          src={embedUrl}
          title={title}
          width="100%"
          height="100%"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          style={{ border: 'none', width: '100%', height: '100%' }}
        />
      </Shell>
    );
  }

  // ── Vimeo ─────────────────────────────────────────────────────────────────
  if (videoType === 'vimeo_embed' && videoId) {
    const vimeoId  = extractVimeoId(videoId);
    const embedUrl = `https://player.vimeo.com/video/${vimeoId}?autoplay=${playing ? 1 : 0}&title=0&byline=0&portrait=0`;

    if (!playing) {
      return (
        <Shell aspectRatio={aspectRatio}>
          {thumbnailUrl && (
            <img
              src={thumbnailUrl}
              alt={title}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          )}
          <PlayButton onClick={() => setPlaying(true)} />
        </Shell>
      );
    }

    return (
      <Shell aspectRatio={aspectRatio}>
        <iframe
          src={embedUrl}
          title={title}
          width="100%"
          height="100%"
          allow="autoplay; fullscreen; picture-in-picture"
          allowFullScreen
          style={{ border: 'none', width: '100%', height: '100%' }}
        />
      </Shell>
    );
  }

  // ── AI-generated (Kling) — HTML5 video ──────────────────────────────────
  if (videoType === 'kling_generated' && videoUrl) {
    return (
      <Shell aspectRatio={aspectRatio}>
        <video
          src={videoUrl}
          poster={thumbnailUrl}
          controls
          playsInline
          preload="metadata"
          aria-label={title}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
      </Shell>
    );
  }

  // ── Fallback / no video yet ──────────────────────────────────────────────
  return (
    <Shell aspectRatio={aspectRatio}>
      {thumbnailUrl ? (
        <img
          src={thumbnailUrl}
          alt={title}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
      ) : (
        <div
          style={{
            width:           '100%',
            height:          '100%',
            display:         'flex',
            alignItems:      'center',
            justifyContent:  'center',
            backgroundColor: '#111',
          }}
        >
          <svg width="40" height="40" viewBox="0 0 24 24" fill="rgba(255,255,255,.25)" aria-hidden>
            <path d="M8 5v14l11-7z"/>
          </svg>
        </div>
      )}
    </Shell>
  );
}
