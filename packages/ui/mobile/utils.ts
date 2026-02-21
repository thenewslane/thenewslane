/** Shared utilities for mobile UI components. */

export function formatTimeAgo(dateStr: string): string {
  const diff  = Date.now() - new Date(dateStr).getTime();
  const secs  = Math.floor(diff / 1_000);
  const mins  = Math.floor(secs  / 60);
  const hours = Math.floor(mins  / 60);
  const days  = Math.floor(hours / 24);
  if (secs  <  60) return 'just now';
  if (mins  <  60) return `${mins}m ago`;
  if (hours <  24) return `${hours}h ago`;
  if (days  <   7) return `${days}d ago`;
  const d = new Date(dateStr);
  return `${d.toLocaleString('default', { month: 'short' })} ${d.getDate()}`;
}

export function truncateWords(text: string, maxWords: number): string {
  const words = text.trim().split(/\s+/);
  if (words.length <= maxWords) return text;
  return words.slice(0, maxWords).join(' ') + '\u2026';
}

export function extractYouTubeId(urlOrId: string): string {
  const match = urlOrId.match(
    /(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/,
  );
  return match ? match[1] : urlOrId;
}

export function extractVimeoId(urlOrId: string): string {
  const match = urlOrId.match(/vimeo\.com\/(?:video\/)?(\d+)/);
  return match ? match[1] : urlOrId;
}
