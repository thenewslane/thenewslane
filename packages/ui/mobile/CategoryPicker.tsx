import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
} from 'react-native';
import type { Category } from '@platform/types';
import { theme }         from '@platform/theme';

export interface CategoryPickerProps {
  categories:    Category[];
  selected:      number[];
  onChange:      (ids: number[]) => void;
  maxSelections?: number; // default 3
}

export function CategoryPicker({
  categories,
  selected,
  onChange,
  maxSelections = 3,
}: CategoryPickerProps) {
  const atMax = selected.length >= maxSelections;

  function toggle(id: number) {
    if (selected.includes(id)) {
      onChange(selected.filter(s => s !== id));
    } else if (!atMax) {
      onChange([...selected, id]);
    }
  }

  function resolveColor(slug: string): string {
    return theme.categoryColors[slug as keyof typeof theme.categoryColors]
      ?? theme.secondaryColor;
  }

  return (
    <View>
      <Text style={styles.hint}>
        {selected.length}/{maxSelections} selected
      </Text>

      <FlatList
        data={categories}
        keyExtractor={item => String(item.id)}
        numColumns={2}
        scrollEnabled={false}
        columnWrapperStyle={styles.row}
        renderItem={({ item }) => {
          const isSelected = selected.includes(item.id);
          const isDisabled = !isSelected && atMax;
          const accentColor = resolveColor(item.slug);

          return (
            <TouchableOpacity
              accessibilityRole="checkbox"
              accessibilityState={{ checked: isSelected, disabled: isDisabled }}
              accessibilityLabel={item.name}
              onPress={() => toggle(item.id)}
              disabled={isDisabled}
              activeOpacity={0.7}
              style={[
                styles.card,
                {
                  borderColor:     isSelected ? accentColor : 'transparent',
                  opacity:         isDisabled ? 0.4 : 1,
                },
              ]}
            >
              {/* Colour swatch */}
              <View style={[styles.swatch, { backgroundColor: accentColor }]} />

              <Text
                style={[
                  styles.name,
                  { fontWeight: isSelected ? '700' : '500' },
                ]}
                numberOfLines={2}
              >
                {item.name}
              </Text>

              {isSelected && (
                <Text style={[styles.check, { color: accentColor }]}>✓</Text>
              )}
            </TouchableOpacity>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  hint: {
    fontSize:     13,
    fontFamily:   theme.fontFamily.body,
    color:        theme.textColor.secondary.light,
    marginBottom: theme.spacing[3],
  },
  row: {
    gap:          theme.spacing[2],
    marginBottom: theme.spacing[2],
  },
  card: {
    flex:            1,
    padding:         theme.spacing[3],
    borderRadius:    theme.borderRadius.medium,
    backgroundColor: theme.cardBackground.light,
    borderWidth:     2,
    shadowColor:     '#000',
    shadowOffset:    { width: 0, height: 1 },
    shadowOpacity:   0.06,
    shadowRadius:    3,
    elevation:       1,
    gap:             theme.spacing[1],
  },
  swatch: {
    width:        24,
    height:       3,
    borderRadius: 2,
  },
  name: {
    fontSize:   13,
    fontFamily: theme.fontFamily.body,
    color:      theme.textColor.primary.light,
    lineHeight: 18,
  },
  check: {
    fontSize:   13,
    fontWeight: '700',
    alignSelf:  'flex-end',
    marginTop:  'auto',
  },
});
