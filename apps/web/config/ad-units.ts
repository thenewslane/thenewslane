/**
 * Google Ad Manager unit configurations.
 * Network code: 23173092177
 */

export const GAM_NETWORK_CODE = '23173092177';

type AdSize = [number, number];

export interface AdUnitConfig {
  unitPath: string;
  sizes:    AdSize[];
  /** Intended display context. Used to conditionally render via CSS or JS. */
  device:   'desktop' | 'mobile' | 'all';
}

export const AD_UNITS = {
  /**
   * 728×90 / 970×90 leaderboard shown at the top of desktop pages.
   * Hidden on mobile (max-width < 768px).
   */
  HEADER_LEADERBOARD: {
    unitPath: `/${GAM_NETWORK_CODE}/header_leaderboard`,
    sizes:    [[728, 90], [970, 90]] as AdSize[],
    device:   'desktop',
  },

  /**
   * 300×250 / 300×600 rectangle shown in the article sidebar on desktop.
   */
  ARTICLE_RECTANGLE: {
    unitPath: `/${GAM_NETWORK_CODE}/article_rectangle`,
    sizes:    [[300, 250], [300, 600]] as AdSize[],
    device:   'desktop',
  },

  /**
   * 300×250 / 336×280 unit inserted between article body and FAQ section.
   * Shown on all device sizes.
   */
  IN_CONTENT: {
    unitPath: `/${GAM_NETWORK_CODE}/in_content`,
    sizes:    [[300, 250], [336, 280]] as AdSize[],
    device:   'all',
  },

  /**
   * 320×50 / 320×100 sticky bottom banner — mobile only.
   * Rendered with position:fixed at the bottom of the viewport.
   */
  MOBILE_ANCHOR: {
    unitPath: `/${GAM_NETWORK_CODE}/mobile_anchor`,
    sizes:    [[320, 50], [320, 100]] as AdSize[],
    device:   'mobile',
  },
} as const satisfies Record<string, AdUnitConfig>;
