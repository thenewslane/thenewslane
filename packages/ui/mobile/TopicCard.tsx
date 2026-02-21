import React from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Image,
  AccessibilityInfo,
} from 'react-native';
import type { TrendingTopic } from '@platform/types';
import { theme }             from '@platform/theme';
import { CategoryBadge }     from './CategoryBadge';
import { ViralIndicator }    from './ViralIndicator';
import { SourceAttribution } from './SourceAttribution';
import { truncateWords }     from './utils';

export interface TopicCardProps {
  topic:    TrendingTopic;
  onPress:  (topic: TrendingTopic) => void;
  disabled?: boolean;
}

export function TopicCard({ topic, onPress, disabled = false }: TopicCardProps) {
  const summary      = topic.summary ? truncateWords(topic.summary, 80) : null;
  const categoryName = topic.category?.name ?? null;

  return (
    <TouchableOpacity
      accessibilityRole="button"
      accessibilityLabel={topic.title}
      accessibilityState={{ disabled }}
      onPress={() => !disabled && onPress(topic)}
      disabled={disabled}
      activeOpacity={0.75}
      style={styles.card}
    >
      {/* Thumbnail */}
      {topic.thumbnail_url && (
        <Image
          source={{ uri: topic.thumbnail_url }}
          style={styles.thumbnail}
          resizeMode="cover"
          accessibilityLabel={`Thumbnail for ${topic.title}`}
        />
      )}

      {/* Content */}
      <View style={styles.content}>
        {/* Badges row */}
        <View style={styles.badgeRow}>
          {topic.viral_tier != null && topic.viral_score != null && (
            <ViralIndicator tier={topic.viral_tier} score={topic.viral_score} />
          )}
          {categoryName && (
            <CategoryBadge category={topic.category!.slug} />
          )}
        </View>

        {/* Title — 2-line clamp via numberOfLines */}
        <Text style={styles.title} numberOfLines={2}>
          {topic.title}
        </Text>

        {/* Summary — 3 lines */}
        {summary && (
          <Text style={styles.summary} numberOfLines={3}>
            {summary}
          </Text>
        )}

        {/* Footer */}
        <View style={styles.footer}>
          <SourceAttribution
            sourceName="theNewslane"
            publishedAt={topic.published_at ?? topic.created_at}
          />
        </View>
      </View>
    </TouchableOpacity>
  );
}

const THUMBNAIL_ASPECT = 16 / 8.4;

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.cardBackground.light,
    borderRadius:    theme.borderRadius.medium,
    overflow:        'hidden',
    shadowColor:     '#000',
    shadowOffset:    { width: 0, height: 1 },
    shadowOpacity:   0.08,
    shadowRadius:    4,
    elevation:       2,
  },
  thumbnail: {
    width:           '100%',
    aspectRatio:     THUMBNAIL_ASPECT,
    backgroundColor: theme.backgroundColor.dark,
  },
  content: {
    padding:        theme.spacing[3],
    gap:            theme.spacing[2],
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems:    'center',
    gap:           theme.spacing[2],
    flexWrap:      'wrap',
  },
  title: {
    fontSize:   16,
    fontWeight: '700',
    fontFamily: theme.fontFamily.heading,
    color:      theme.textColor.primary.light,
    lineHeight: 22,
  },
  summary: {
    fontSize:   13,
    lineHeight: 19,
    fontFamily: theme.fontFamily.body,
    color:      theme.textColor.secondary.light,
  },
  footer: {
    marginTop: theme.spacing[1],
  },
});
