/**
 * Format article/summary text for display:
 * - Countries and organisations in all caps (US, UK, WNBA, NBA, etc.)
 * - Currency symbols: ensure common symbols are used (optional normalization)
 */

// Terms that should always display in ALL CAPS (case-insensitive match, word boundary).
const ALL_CAPS_TERMS = new Set([
  // Countries / regions
  'us', 'usa', 'uk', 'uae', 'eu', 'nato', 'un', 'who', 'unesco', 'fifa', 'uefa',
  // Sports / orgs
  'wnba', 'nba', 'nfl', 'nhl', 'mlb', 'mls', 'ncaa', 'espn', 'fbi', 'cia', 'ceo', 'cfo', 'cto',
  'ai', 'api', 'rss', 'faq', 'faqs', 'pdf', 'url', 'html', 'css', 'nyc', 'la', 'dc',
  // Indian legal / government acronyms
  'pocso', 'hc', 'sc', 'fir', 'pil', 'cbi', 'nia', 'ed', 'ipc', 'bns', 'crpc', 'bnss',
  'bjp', 'inc', 'aap', 'rss', 'mla', 'mp', 'pm', 'cm',
  'rti', 'ngt', 'sebi', 'rbi', 'isro', 'drdo', 'bcci',
  // International government / institutions
  'imf', 'wto', 'icc', 'icj', 'ecb', 'fed', 'sec', 'doj', 'nhs', 'gop',
  'gdp', 'ipo', 'etf', 'nyse', 'ftse', 'cpi', 'gst', 'vat',
  // Tech
  'llm', 'gpu', 'cpu', 'ram', 'ssd', 'ios', 'usb', 'nft', 'dao', 'defi',
]);

const ALL_CAPS_REGEX = (() => {
  const escaped = [...ALL_CAPS_TERMS].map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  return new RegExp(`\\b(${escaped})\\b`, 'gi');
})();

/**
 * Replaces known abbreviations with uppercase (e.g. "us" → "US", "wnba" → "WNBA").
 */
export function formatArticleText(text: string): string {
  if (!text || typeof text !== 'string') return text;
  return text.replace(ALL_CAPS_REGEX, (match) => match.toUpperCase());
}

/**
 * Normalize currency display: ensure common symbols are present.
 * Use when the source might have broken encoding (e.g. "Â£" → "£").
 */
const CURRENCY_FIXES: [RegExp, string][] = [
  [/Â£/g, '£'],
  [/â‚¬/g, '€'],
  [/Â¥/g, '¥'],
  [/â€"/g, '–'],
];

export function normalizeCurrencyInText(text: string): string {
  if (!text || typeof text !== 'string') return text;
  let out = text;
  for (const [re, replacement] of CURRENCY_FIXES) {
    out = out.replace(re, replacement);
  }
  return out;
}

/**
 * Apply both formatting and currency normalization.
 */
export function formatAndNormalizeArticleText(text: string): string {
  return formatArticleText(normalizeCurrencyInText(text));
}
