/**
 * generate-tokens.ts
 *
 * Orchestrator — runs both web and mobile token generators simultaneously.
 * Usage: tsx generate-tokens.ts
 */

import { generateWebTokens }    from './generate-web-tokens.js';
import { generateMobileTokens } from './generate-mobile-tokens.js';

console.log('[tokens] Generating design tokens from theme.config.ts …');

// Both generators are synchronous — run sequentially but log together.
generateWebTokens();
generateMobileTokens();

console.log('[tokens] Done.');
