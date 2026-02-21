import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  FlatList,
  SafeAreaView,
} from 'react-native';
import { theme } from '@platform/theme';

export interface AgeGateProps {
  onVerified: (isMinor: boolean) => void;
  onBlocked:  () => void;
}

const CURRENT_YEAR = new Date().getFullYear();

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const YEARS = Array.from({ length: 110 }, (_, i) => CURRENT_YEAR - 13 - i);

function calcAge(birthMonth: number, birthYear: number): number {
  const now = new Date();
  let age = now.getFullYear() - birthYear;
  if (now.getMonth() + 1 < birthMonth) age -= 1;
  return age;
}

type PickerField = 'month' | 'year' | null;

export function AgeGate({ onVerified, onBlocked }: AgeGateProps) {
  const [month,        setMonth]        = useState<number | null>(null);
  const [year,         setYear]         = useState<number | null>(null);
  const [pickerOpen,   setPickerOpen]   = useState<PickerField>(null);
  const [error,        setError]        = useState<string | null>(null);
  const [blocked,      setBlocked]      = useState(false);

  function handleSubmit() {
    setError(null);
    if (!month || !year) {
      setError('Please select your birth month and year.');
      return;
    }
    const age = calcAge(month, year);
    if (age < 13) {
      setBlocked(true);
      onBlocked();
      return;
    }
    onVerified(age < 18);
  }

  if (blocked) {
    return (
      <View style={styles.container} accessibilityLiveRegion="polite">
        <Text style={styles.blockedIcon}>⛔</Text>
        <Text style={styles.blockedTitle}>Access Restricted</Text>
        <Text style={styles.blockedBody}>
          You must be at least 13 years old to access this content.
        </Text>
      </View>
    );
  }

  const pickerData: string[] =
    pickerOpen === 'month'
      ? MONTHS
      : YEARS.map(String);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Age Verification</Text>
      <Text style={styles.subtitle}>
        Please enter your date of birth to continue.
      </Text>

      {/* Selectors */}
      <View style={styles.row}>
        <TouchableOpacity
          style={styles.selector}
          onPress={() => setPickerOpen('month')}
          accessibilityRole="button"
          accessibilityLabel={`Birth month: ${month ? MONTHS[month - 1] : 'not selected'}`}
        >
          <Text style={[styles.selectorText, !month && styles.placeholder]}>
            {month ? MONTHS[month - 1] : 'Month'}
          </Text>
          <Text style={styles.chevron}>▾</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.selector}
          onPress={() => setPickerOpen('year')}
          accessibilityRole="button"
          accessibilityLabel={`Birth year: ${year ?? 'not selected'}`}
        >
          <Text style={[styles.selectorText, !year && styles.placeholder]}>
            {year ? String(year) : 'Year'}
          </Text>
          <Text style={styles.chevron}>▾</Text>
        </TouchableOpacity>
      </View>

      {error && (
        <Text style={styles.error} accessibilityRole="alert">{error}</Text>
      )}

      <TouchableOpacity
        style={styles.submitBtn}
        onPress={handleSubmit}
        accessibilityRole="button"
        activeOpacity={0.85}
      >
        <Text style={styles.submitText}>Continue</Text>
      </TouchableOpacity>

      {/* Picker modal */}
      <Modal
        visible={pickerOpen !== null}
        transparent
        animationType="slide"
        onRequestClose={() => setPickerOpen(null)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setPickerOpen(null)}
        >
          <SafeAreaView style={styles.sheet}>
            <View style={styles.sheetHandle} />
            <FlatList
              data={pickerData}
              keyExtractor={(item, i) => `${item}-${i}`}
              style={styles.pickerList}
              renderItem={({ item, index }) => {
                const isSelected =
                  pickerOpen === 'month'
                    ? month === index + 1
                    : year === Number(item);
                return (
                  <TouchableOpacity
                    onPress={() => {
                      if (pickerOpen === 'month') setMonth(index + 1);
                      else setYear(Number(item));
                      setPickerOpen(null);
                    }}
                    style={[styles.pickerItem, isSelected && styles.pickerItemSelected]}
                  >
                    <Text
                      style={[
                        styles.pickerItemText,
                        isSelected && styles.pickerItemTextSelected,
                      ]}
                    >
                      {item}
                    </Text>
                  </TouchableOpacity>
                );
              }}
            />
          </SafeAreaView>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: theme.cardBackground.light,
    borderRadius:    theme.borderRadius.large,
    padding:         theme.spacing[8],
    alignItems:      'center',
    shadowColor:     '#000',
    shadowOffset:    { width: 0, height: 4 },
    shadowOpacity:   0.1,
    shadowRadius:    12,
    elevation:       6,
  },
  title: {
    fontSize:     20,
    fontFamily:   theme.fontFamily.heading,
    fontWeight:   '700',
    color:        theme.textColor.primary.light,
    marginBottom: theme.spacing[1],
    textAlign:    'center',
  },
  subtitle: {
    fontSize:     13,
    fontFamily:   theme.fontFamily.body,
    color:        theme.textColor.secondary.light,
    lineHeight:   20,
    textAlign:    'center',
    marginBottom: theme.spacing[6],
  },
  row: {
    flexDirection: 'row',
    gap:           theme.spacing[3],
    width:         '100%',
    marginBottom:  theme.spacing[4],
  },
  selector: {
    flex:            1,
    flexDirection:   'row',
    alignItems:      'center',
    justifyContent:  'space-between',
    padding:         theme.spacing[3],
    borderRadius:    theme.borderRadius.small,
    borderWidth:     1,
    borderColor:     'rgba(0,0,0,.18)',
    backgroundColor: theme.backgroundColor.light,
  },
  selectorText: {
    fontSize:   14,
    fontFamily: theme.fontFamily.body,
    color:      theme.textColor.primary.light,
  },
  placeholder: {
    color: theme.textColor.muted.light,
  },
  chevron: {
    fontSize:  12,
    color:     theme.textColor.muted.light,
  },
  error: {
    fontSize:     12,
    fontFamily:   theme.fontFamily.body,
    color:        theme.viralTierColors.tier1,
    fontWeight:   '500',
    marginBottom: theme.spacing[3],
    alignSelf:    'flex-start',
  },
  submitBtn: {
    width:           '100%',
    padding:         theme.spacing[3],
    borderRadius:    theme.borderRadius.small,
    backgroundColor: theme.primaryColor,
    alignItems:      'center',
  },
  submitText: {
    color:      '#fff',
    fontSize:   14,
    fontWeight: '700',
    fontFamily: theme.fontFamily.body,
    letterSpacing: 0.3,
  },
  // Blocked state
  blockedIcon: {
    fontSize:     40,
    marginBottom: theme.spacing[3],
  },
  blockedTitle: {
    fontSize:     18,
    fontFamily:   theme.fontFamily.heading,
    fontWeight:   '700',
    color:        theme.textColor.primary.light,
    marginBottom: theme.spacing[2],
  },
  blockedBody: {
    fontSize:   14,
    fontFamily: theme.fontFamily.body,
    color:      theme.textColor.secondary.light,
    lineHeight: 22,
    textAlign:  'center',
  },
  // Picker modal
  modalOverlay: {
    flex:            1,
    justifyContent:  'flex-end',
    backgroundColor: 'rgba(0,0,0,.45)',
  },
  sheet: {
    backgroundColor: theme.cardBackground.light,
    borderTopLeftRadius:  theme.borderRadius.large,
    borderTopRightRadius: theme.borderRadius.large,
    maxHeight:            '55%',
    paddingTop:           theme.spacing[2],
  },
  sheetHandle: {
    width:           40,
    height:          4,
    borderRadius:    2,
    backgroundColor: 'rgba(0,0,0,.15)',
    alignSelf:       'center',
    marginBottom:    theme.spacing[2],
  },
  pickerList: {
    flex: 1,
  },
  pickerItem: {
    paddingVertical:   theme.spacing[3],
    paddingHorizontal: theme.spacing[6],
  },
  pickerItemSelected: {
    backgroundColor: `${theme.primaryColor}14`,
  },
  pickerItemText: {
    fontSize:   16,
    fontFamily: theme.fontFamily.body,
    color:      theme.textColor.primary.light,
  },
  pickerItemTextSelected: {
    color:      theme.primaryColor,
    fontWeight: '700',
  },
});
