'use client';

/**
 * NavigableTopicCard
 *
 * TopicCard wrapper that navigates to the article page on press.
 * Used in the "Related Topics" section of the article page.
 */

import { useRouter } from 'next/navigation';
import { TopicCard } from '@platform/ui/web';
import type { TrendingTopic } from '@platform/types';

export function NavigableTopicCard({ topic }: { topic: TrendingTopic }) {
  const router = useRouter();

  return (
    <TopicCard
      topic={topic}
      onPress={t => router.push(`/trending/${t.slug}`)}
    />
  );
}
