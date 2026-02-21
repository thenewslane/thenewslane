import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { theme } from '@platform/theme';
import { formatTimeAgo } from './utils';

export interface AuthorBylineProps {
  authorName:  string;
  publishedAt: string; // ISO-8601
}

export function AuthorByline({ authorName, publishedAt }: AuthorBylineProps) {
  return (
    <View style={styles.row} accessibilityRole="text">
      <Text style={styles.by}>
        By <Text style={styles.author}>{authorName}</Text>
      </Text>

      <View style={styles.aiBadge} accessibilityLabel="AI-assisted article">
        <Text style={styles.aiText}>AI‑assisted</Text>
      </View>

      <Text style={styles.dot} aria-hidden>·</Text>

      <Text style={styles.time}>{formatTimeAgo(publishedAt)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems:    'center',
    flexWrap:      'wrap',
    gap:           theme.spacing[2],
  },
  by: {
    fontSize:   13,
    fontFamily: theme.fontFamily.body,
    color:      theme.textColor.secondary.light,
  },
  author: {
    fontWeight: '600',
    color:      theme.linkColor,
  },
  aiBadge: {
    paddingHorizontal: 6,
    paddingVertical:   2,
    borderRadius:      theme.borderRadius.small,
    backgroundColor:   `${theme.accentColor}20`,
  },
  aiText: {
    fontSize:     10,
    fontWeight:   '700',
    fontFamily:   theme.fontFamily.body,
    color:        theme.accentColor,
    letterSpacing: 0.5,
    textTransform: 'uppercase' as const,
  },
  dot: {
    fontSize:  13,
    color:     theme.textColor.muted.light,
    opacity:   0.4,
  },
  time: {
    fontSize:  13,
    fontFamily: theme.fontFamily.body,
    color:     theme.textColor.secondary.light,
    opacity:   0.75,
  },
});
