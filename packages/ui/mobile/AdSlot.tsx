/**
 * AdSlot — React Native
 *
 * A consent-aware wrapper for mobile ad placements.
 * When advertising consent is granted, renders an <AdSlotRenderer> slot that
 * apps wire up to their chosen SDK (react-native-google-mobile-ads / AdMob).
 * Without consent, renders a size-preserving placeholder.
 *
 * The actual ad SDK component is injected via the `renderAd` prop so that
 * @platform/ui has no direct dependency on any ad SDK.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme } from '@platform/theme';

export interface ConsentState {
  necessary:   boolean;
  analytics:   boolean;
  advertising: boolean;
  functional:  boolean;
}

export interface AdSlotProps {
  /** Ad Manager unit path, e.g. "/1234567/app-banner" */
  unitPath:     string;
  /** Ad sizes array: [[width, height], ...] */
  sizes:        [number, number][];
  consentState: ConsentState;
  /**
   * App-provided render function called only when advertising consent is
   * granted. Receives the unit path so the app can pass it to the SDK.
   *   renderAd={({ unitPath }) => <BannerAd unitId={unitPath} size="BANNER" />}
   */
  renderAd?: (props: { unitPath: string }) => React.ReactNode;
}

export function AdSlot({ unitPath, sizes, consentState, renderAd }: AdSlotProps) {
  const [w, h] = sizes[0] ?? [320, 50];

  if (!consentState.advertising) {
    return (
      <View
        accessible
        accessibilityLabel="Advertisement placeholder — consent required"
        style={[styles.placeholder, { width: w, height: h }]}
      >
        <Text style={styles.placeholderText}>Advertisement</Text>
      </View>
    );
  }

  if (!renderAd) {
    // Consent granted but no renderer provided — reserve the space.
    return <View style={{ width: w, height: h }} />;
  }

  return (
    <View style={{ width: w, height: h, overflow: 'hidden' }}>
      {renderAd({ unitPath })}
    </View>
  );
}

const styles = StyleSheet.create({
  placeholder: {
    backgroundColor: theme.adSlotBackground,
    borderRadius:    theme.borderRadius.small,
    alignItems:      'center',
    justifyContent:  'center',
    overflow:        'hidden',
  },
  placeholderText: {
    fontSize:     11,
    fontFamily:   theme.fontFamily.body,
    color:        theme.textColor.muted.light,
    letterSpacing: 0.5,
    textTransform: 'uppercase' as const,
  },
});
