/**
 * VideoPlayer — React Native
 *
 * Uses react-native-webview (peer dep) to embed YouTube / Vimeo iframes, and
 * builds an inline HTML page with an HTML5 <video> for kling_generated assets.
 * Falls back to a pressable thumbnail placeholder when no video is available.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  StyleSheet,
  useWindowDimensions,
} from 'react-native';
// WebView is a peer dependency — imported lazily so the package resolves even
// in projects that haven't installed react-native-webview yet.
import type { WebViewProps } from 'react-native-webview';
let WebView: React.ComponentType<WebViewProps> | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  WebView = require('react-native-webview').WebView;
} catch {
  // react-native-webview not installed — video will use fallback UI.
}

import { theme }              from '@platform/theme';
import { extractYouTubeId, extractVimeoId } from './utils';

export interface VideoPlayerProps {
  videoType:    'youtube_embed' | 'vimeo_embed' | 'kling_generated' | null;
  videoId?:     string;
  videoUrl?:    string;
  thumbnailUrl?: string;
  title:        string;
}

function PlayOverlay({ onPress }: { onPress: () => void }) {
  return (
    <TouchableOpacity
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel="Play video"
      style={styles.playOverlay}
      activeOpacity={0.85}
    >
      <View style={styles.playBtn}>
        <Text style={styles.playIcon}>▶</Text>
      </View>
    </TouchableOpacity>
  );
}

function buildKlingHtml(videoUrl: string, posterUrl?: string): string {
  const poster = posterUrl ? `poster="${posterUrl}"` : '';
  return `<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#000}video{width:100%;height:100vh;object-fit:cover}</style></head><body><video src="${videoUrl}" ${poster} controls playsinline autoplay></video></body></html>`;
}

export function VideoPlayer({
  videoType,
  videoId,
  videoUrl,
  thumbnailUrl,
  title,
}: VideoPlayerProps) {
  const { width }       = useWindowDimensions();
  const height          = Math.round(width * 0.5625); // 16:9
  const [playing, setPlaying] = useState(false);

  const containerStyle = [styles.container, { height }];

  // ── Missing WebView ────────────────────────────────────────────────────────
  if (!WebView && (videoType === 'youtube_embed' || videoType === 'vimeo_embed' || videoType === 'kling_generated')) {
    return (
      <View style={[containerStyle, styles.errorBox]}>
        <Text style={styles.errorText}>
          Install react-native-webview to enable video playback.
        </Text>
      </View>
    );
  }

  // ── YouTube ───────────────────────────────────────────────────────────────
  if (videoType === 'youtube_embed' && videoId) {
    const ytId = extractYouTubeId(videoId);

    if (!playing) {
      return (
        <View style={containerStyle}>
          {thumbnailUrl && <Image source={{ uri: thumbnailUrl }} style={styles.fill} resizeMode="cover" />}
          <View style={styles.fill}>
            <PlayOverlay onPress={() => setPlaying(true)} />
          </View>
        </View>
      );
    }

    const embedUrl = `https://www.youtube-nocookie.com/embed/${ytId}?autoplay=1&rel=0&modestbranding=1&playsinline=1`;
    return (
      <View style={containerStyle}>
        <WebView!
          source={{ uri: embedUrl }}
          allowsInlineMediaPlayback
          mediaPlaybackRequiresUserAction={false}
          style={styles.fill}
          accessibilityLabel={title}
        />
      </View>
    );
  }

  // ── Vimeo ─────────────────────────────────────────────────────────────────
  if (videoType === 'vimeo_embed' && videoId) {
    const vimeoId  = extractVimeoId(videoId);

    if (!playing) {
      return (
        <View style={containerStyle}>
          {thumbnailUrl && <Image source={{ uri: thumbnailUrl }} style={styles.fill} resizeMode="cover" />}
          <View style={styles.fill}>
            <PlayOverlay onPress={() => setPlaying(true)} />
          </View>
        </View>
      );
    }

    const embedUrl = `https://player.vimeo.com/video/${vimeoId}?autoplay=1&title=0&byline=0&portrait=0&playsinline=1`;
    return (
      <View style={containerStyle}>
        <WebView!
          source={{ uri: embedUrl }}
          allowsInlineMediaPlayback
          mediaPlaybackRequiresUserAction={false}
          style={styles.fill}
          accessibilityLabel={title}
        />
      </View>
    );
  }

  // ── AI-generated (Kling) ──────────────────────────────────────────────────
  if (videoType === 'kling_generated' && videoUrl) {
    const html = buildKlingHtml(videoUrl, thumbnailUrl);
    return (
      <View style={containerStyle}>
        <WebView!
          source={{ html }}
          allowsInlineMediaPlayback
          mediaPlaybackRequiresUserAction={false}
          style={styles.fill}
          accessibilityLabel={title}
          scrollEnabled={false}
        />
      </View>
    );
  }

  // ── Fallback / thumbnail only ─────────────────────────────────────────────
  return (
    <View style={containerStyle}>
      {thumbnailUrl ? (
        <Image source={{ uri: thumbnailUrl }} style={styles.fill} resizeMode="cover" accessibilityLabel={title} />
      ) : (
        <View style={[styles.fill, styles.placeholder]}>
          <Text style={styles.placeholderIcon}>▶</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width:           '100%',
    backgroundColor: theme.backgroundColor.dark,
    borderRadius:    theme.borderRadius.medium,
    overflow:        'hidden',
    position:        'relative',
  },
  fill: {
    position: 'absolute',
    top:      0,
    left:     0,
    right:    0,
    bottom:   0,
  },
  playOverlay: {
    flex:            1,
    alignItems:      'center',
    justifyContent:  'center',
    backgroundColor: 'rgba(0,0,0,.38)',
  },
  playBtn: {
    width:           56,
    height:          56,
    borderRadius:    28,
    backgroundColor: theme.primaryColor,
    alignItems:      'center',
    justifyContent:  'center',
  },
  playIcon: {
    color:    '#fff',
    fontSize: 20,
    left:     2,  // optical centre for triangle
  },
  placeholder: {
    backgroundColor: '#111',
    alignItems:      'center',
    justifyContent:  'center',
  },
  placeholderIcon: {
    color:    'rgba(255,255,255,.25)',
    fontSize: 40,
  },
  errorBox: {
    alignItems:     'center',
    justifyContent: 'center',
    backgroundColor: theme.backgroundColor.dark,
  },
  errorText: {
    color:      theme.textColor.muted.dark,
    fontSize:   12,
    fontFamily: theme.fontFamily.body,
    textAlign:  'center',
    padding:    theme.spacing[4],
  },
});
