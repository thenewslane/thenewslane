import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { theme } from '@platform/theme';

export interface CategoryBadgeProps {
  category: string; // slug or display name
}

function resolveColor(category: string): string {
  const slug = category
    .toLowerCase()
    .replace(/\s*&\s*/g, '-')
    .replace(/\s+/g, '-') as keyof typeof theme.categoryColors;
  return theme.categoryColors[slug] ?? theme.secondaryColor;
}

export function CategoryBadge({ category }: CategoryBadgeProps) {
  const bg = resolveColor(category);
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <Text style={styles.text}>{category.toUpperCase()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: theme.spacing[2],
    paddingVertical:   2,
    borderRadius:      theme.borderRadius.small,
    alignSelf:         'flex-start',
  },
  text: {
    color:       '#fff',
    fontSize:    10,
    fontWeight:  '700',
    letterSpacing: 0.8,
    fontFamily:  theme.fontFamily.body,
  },
});
