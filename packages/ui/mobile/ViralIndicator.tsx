import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { theme } from '@platform/theme';

export interface ViralIndicatorProps {
  tier:       1 | 2 | 3;
  score:      number;  // 0.0 – 1.0
  showScore?: boolean; // default true
  showLabel?: boolean; // default true
}

const TIER_COLOR: Record<1 | 2 | 3, string> = {
  1: theme.viralTierColors.tier1,
  2: theme.viralTierColors.tier2,
  3: theme.viralTierColors.tier3,
};

const TIER_LABEL: Record<1 | 2 | 3, string> = {
  1: 'Viral',
  2: 'Trending',
  3: 'Emerging',
};

// Simple Unicode stand-ins for the icon glyphs
const TIER_ICON: Record<1 | 2 | 3, string> = {
  1: '🔥',
  2: '↑',
  3: '•',
};

export function ViralIndicator({
  tier,
  score,
  showScore = true,
  showLabel = true,
}: ViralIndicatorProps) {
  const color = TIER_COLOR[tier];
  const pct   = Math.round(score * 100);

  return (
    <View style={styles.row} accessibilityLabel={`${TIER_LABEL[tier]} ${pct}%`}>
      <Text style={[styles.icon, { color }]}>{TIER_ICON[tier]}</Text>
      {showScore && <Text style={[styles.score, { color }]}>{pct}%</Text>}
      {showLabel && <Text style={[styles.label, { color }]}>{TIER_LABEL[tier]}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems:    'center',
    gap:           3,
  },
  icon: {
    fontSize: 12,
  },
  score: {
    fontSize:  11,
    fontWeight: '700',
    fontFamily: theme.fontFamily.body,
  },
  label: {
    fontSize:  11,
    fontWeight: '400',
    fontFamily: theme.fontFamily.body,
    opacity:    0.85,
  },
});
