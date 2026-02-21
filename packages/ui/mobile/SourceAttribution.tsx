import React from 'react';
import { StyleSheet, Text, View, Image } from 'react-native';
import { theme } from '@platform/theme';
import { formatTimeAgo } from './utils';

export interface SourceAttributionProps {
  sourceName:  string;
  sourceUrl?:  string;
  publishedAt: string; // ISO-8601
}

export function SourceAttribution({ sourceName, sourceUrl, publishedAt }: SourceAttributionProps) {
  const hostname = sourceUrl
    ? (() => { try { return new URL(sourceUrl).hostname; } catch { return null; } })()
    : null;
  const faviconUri = hostname
    ? `https://www.google.com/s2/favicons?sz=16&domain=${hostname}`
    : null;

  return (
    <View style={styles.row} accessibilityRole="text">
      {faviconUri && (
        <Image
          source={{ uri: faviconUri }}
          style={styles.favicon}
          accessibilityLabel={`${sourceName} favicon`}
        />
      )}
      <Text style={styles.source}>{sourceName}</Text>
      <Text style={styles.dot} aria-hidden>·</Text>
      <Text style={styles.time}>{formatTimeAgo(publishedAt)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems:    'center',
    gap:           theme.spacing[1],
  },
  favicon: {
    width:        14,
    height:       14,
    borderRadius: 2,
  },
  source: {
    fontSize:   12,
    fontWeight: '500',
    fontFamily: theme.fontFamily.body,
    color:      theme.textColor.secondary.light,
  },
  dot: {
    fontSize:  12,
    color:     theme.textColor.muted.light,
    opacity:   0.5,
  },
  time: {
    fontSize:  12,
    fontFamily: theme.fontFamily.body,
    color:     theme.textColor.secondary.light,
    opacity:   0.75,
  },
});
