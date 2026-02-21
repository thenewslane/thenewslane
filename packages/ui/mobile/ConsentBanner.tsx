import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  SafeAreaView,
  ScrollView,
  Switch,
} from 'react-native';
import { theme } from '@platform/theme';

export interface ConsentState {
  necessary:   boolean;
  analytics:   boolean;
  advertising: boolean;
  functional:  boolean;
}

export interface ConsentBannerProps {
  onConsent: (state: ConsentState) => void;
}

const PREFS_INIT: Omit<ConsentState, 'necessary'> = {
  analytics:   false,
  advertising: false,
  functional:  false,
};

const PREFERENCE_ITEMS: {
  key:   keyof Omit<ConsentState, 'necessary'>;
  label: string;
  desc:  string;
}[] = [
  { key: 'analytics',   label: 'Analytics',   desc: 'Helps us understand how you use the app (analytics & crash reports).' },
  { key: 'advertising', label: 'Advertising',  desc: 'Personalised ads via Google AdMob.' },
  { key: 'functional',  label: 'Functional',   desc: 'Remembers your preferences and personalises your experience.' },
];

export function ConsentBanner({ onConsent }: ConsentBannerProps) {
  const [visible,   setVisible]   = useState(true);
  const [managing,  setManaging]  = useState(false);
  const [prefs,     setPrefs]     = useState(PREFS_INIT);

  if (!visible) return null;

  function acceptAll() {
    const s: ConsentState = { necessary: true, analytics: true, advertising: true, functional: true };
    setVisible(false);
    onConsent(s);
  }

  function rejectAll() {
    const s: ConsentState = { necessary: true, analytics: false, advertising: false, functional: false };
    setVisible(false);
    onConsent(s);
  }

  function savePrefs() {
    const s: ConsentState = { necessary: true, ...prefs };
    setVisible(false);
    setManaging(false);
    onConsent(s);
  }

  function togglePref(key: keyof typeof prefs) {
    setPrefs(p => ({ ...p, [key]: !p[key] }));
  }

  return (
    <>
      {/* ── Main banner ─────────────────────────────────────────────────── */}
      <View style={styles.banner} accessibilityRole="alert">
        <Text style={styles.bannerTitle}>We value your privacy</Text>
        <Text style={styles.bannerBody}>
          We use cookies and similar technologies to improve your experience,
          analyse traffic, and serve personalised ads.{' '}
          <Text style={styles.link}>Privacy policy</Text>
        </Text>

        <TouchableOpacity style={styles.btnPrimary} onPress={acceptAll} activeOpacity={0.85}>
          <Text style={styles.btnPrimaryText}>Accept All</Text>
        </TouchableOpacity>

        <View style={styles.secondaryRow}>
          <TouchableOpacity style={styles.btnSecondary} onPress={rejectAll} activeOpacity={0.8}>
            <Text style={styles.btnSecondaryText}>Reject All</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.btnSecondary, styles.btnGhost]}
            onPress={() => setManaging(true)}
            activeOpacity={0.8}
          >
            <Text style={[styles.btnSecondaryText, styles.btnGhostText]}>
              Manage
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ── Manage preferences modal ────────────────────────────────────── */}
      <Modal
        visible={managing}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setManaging(false)}
      >
        <SafeAreaView style={styles.sheet}>
          <View style={styles.sheetHeader}>
            <Text style={styles.sheetTitle}>Cookie Preferences</Text>
            <TouchableOpacity
              onPress={() => setManaging(false)}
              accessibilityRole="button"
              accessibilityLabel="Close preferences"
              style={styles.closeBtn}
            >
              <Text style={styles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.sheetScroll} contentContainerStyle={styles.sheetContent}>
            {/* Necessary — always on */}
            <View style={styles.prefRow}>
              <View style={styles.prefInfo}>
                <Text style={styles.prefLabel}>Necessary</Text>
                <Text style={styles.prefDesc}>
                  Required for the app to function. Cannot be disabled.
                </Text>
              </View>
              <Switch
                value
                disabled
                trackColor={{ false: 'rgba(0,0,0,.15)', true: theme.primaryColor }}
                thumbColor="#fff"
              />
            </View>

            {PREFERENCE_ITEMS.map(({ key, label, desc }) => (
              <View key={key} style={styles.prefRow}>
                <View style={styles.prefInfo}>
                  <Text style={styles.prefLabel}>{label}</Text>
                  <Text style={styles.prefDesc}>{desc}</Text>
                </View>
                <Switch
                  value={prefs[key]}
                  onValueChange={() => togglePref(key)}
                  trackColor={{ false: 'rgba(0,0,0,.15)', true: theme.primaryColor }}
                  thumbColor="#fff"
                />
              </View>
            ))}
          </ScrollView>

          <View style={styles.sheetFooter}>
            <TouchableOpacity style={styles.btnPrimary} onPress={savePrefs} activeOpacity={0.85}>
              <Text style={styles.btnPrimaryText}>Save Preferences</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: theme.cardBackground.light,
    padding:         theme.spacing[6],
    shadowColor:     '#000',
    shadowOffset:    { width: 0, height: -2 },
    shadowOpacity:   0.08,
    shadowRadius:    8,
    elevation:       8,
    borderTopLeftRadius:  theme.borderRadius.large,
    borderTopRightRadius: theme.borderRadius.large,
  },
  bannerTitle: {
    fontSize:     16,
    fontFamily:   theme.fontFamily.heading,
    fontWeight:   '700',
    color:        theme.textColor.primary.light,
    marginBottom: theme.spacing[2],
  },
  bannerBody: {
    fontSize:     13,
    fontFamily:   theme.fontFamily.body,
    color:        theme.textColor.secondary.light,
    lineHeight:   20,
    marginBottom: theme.spacing[4],
  },
  link: {
    color:           theme.linkColor,
    textDecorationLine: 'underline' as const,
  },
  btnPrimary: {
    width:           '100%',
    padding:         theme.spacing[3],
    borderRadius:    theme.borderRadius.small,
    backgroundColor: theme.primaryColor,
    alignItems:      'center',
    marginBottom:    theme.spacing[2],
  },
  btnPrimaryText: {
    color:      '#fff',
    fontSize:   14,
    fontWeight: '700',
    fontFamily: theme.fontFamily.body,
  },
  secondaryRow: {
    flexDirection: 'row',
    gap:           theme.spacing[2],
  },
  btnSecondary: {
    flex:            1,
    padding:         theme.spacing[3],
    borderRadius:    theme.borderRadius.small,
    backgroundColor: 'rgba(0,0,0,.06)',
    alignItems:      'center',
  },
  btnSecondaryText: {
    fontSize:   13,
    fontWeight: '600',
    fontFamily: theme.fontFamily.body,
    color:      theme.textColor.primary.light,
  },
  btnGhost: {
    backgroundColor: 'transparent',
  },
  btnGhostText: {
    color: theme.linkColor,
  },
  // Manage modal
  sheet: {
    flex:            1,
    backgroundColor: theme.backgroundColor.light,
  },
  sheetHeader: {
    flexDirection:    'row',
    alignItems:       'center',
    justifyContent:   'space-between',
    padding:          theme.spacing[6],
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,.08)',
  },
  sheetTitle: {
    fontSize:   18,
    fontFamily: theme.fontFamily.heading,
    fontWeight: '700',
    color:      theme.textColor.primary.light,
  },
  closeBtn: {
    padding: theme.spacing[2],
  },
  closeBtnText: {
    fontSize:  16,
    color:     theme.textColor.muted.light,
    fontFamily: theme.fontFamily.body,
  },
  sheetScroll: {
    flex: 1,
  },
  sheetContent: {
    padding: theme.spacing[6],
    gap:     theme.spacing[2],
  },
  prefRow: {
    flexDirection:  'row',
    alignItems:     'flex-start',
    justifyContent: 'space-between',
    paddingVertical: theme.spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,.07)',
    gap:             theme.spacing[4],
  },
  prefInfo: {
    flex: 1,
  },
  prefLabel: {
    fontSize:     14,
    fontWeight:   '600',
    fontFamily:   theme.fontFamily.body,
    color:        theme.textColor.primary.light,
    marginBottom: 4,
  },
  prefDesc: {
    fontSize:  12,
    fontFamily: theme.fontFamily.body,
    color:     theme.textColor.muted.light,
    lineHeight: 18,
  },
  sheetFooter: {
    padding:        theme.spacing[6],
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,.08)',
  },
});
