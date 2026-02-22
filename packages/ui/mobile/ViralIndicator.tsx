import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { theme } from '@platform/theme';

export interface ViralIndicatorProps {
  tier:       1 | 2 | 3;
  score:      number;  // 0.0 – 1.0
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

export function ViralIndicator({
  tier,
  score,
  showLabel = true,
}: ViralIndicatorProps) {
  const color = TIER_COLOR[tier];
  const isHot = score >= 0.8;

  return (
    <View style={styles.row} accessibilityLabel={TIER_LABEL[tier]}>
      <Text style={[styles.icon, { color }]}>{isHot ? '🔥' : '↗'}</Text>
      {showLabel && (
        <Text style={[styles.label, { color }]}>{TIER_LABEL[tier]}</Text>
      )}
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
  label: {
    fontSize:   11,
    fontWeight: '400',
    fontFamily: theme.fontFamily.body,
    opacity:    0.85,
  },
});
