/**
 * watch.ts
 *
 * Watch mode — regenerates tokens whenever theme.config.ts is saved.
 * Usage: tsx watch.ts
 *
 * Uses chokidar for reliable cross-platform file watching.
 */

import chokidar from 'chokidar';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_PATH = resolve(__dirname, 'theme.config.ts');

async function runGenerators(): Promise<void> {
  // Re-import with a cache-busting query param so Node picks up the new file.
  const bust = `?t=${Date.now()}`;
  const { generateWebTokens }    = await import(`./generate-web-tokens.js${bust}`);
  const { generateMobileTokens } = await import(`./generate-mobile-tokens.js${bust}`);
  generateWebTokens();
  generateMobileTokens();
}

console.log(`[watch] Watching ${CONFIG_PATH}`);
console.log('[watch] Press Ctrl+C to stop.\n');

// Generate once on start.
runGenerators().catch(console.error);

const watcher = chokidar.watch(CONFIG_PATH, {
  persistent:    true,
  ignoreInitial: true,
  awaitWriteFinish: {
    stabilityThreshold: 200,
    pollInterval:       50,
  },
});

watcher.on('change', (path) => {
  console.log(`\n[watch] ${path} changed — regenerating tokens…`);
  runGenerators().catch(console.error);
});

watcher.on('error', (err) => {
  console.error('[watch] Error:', err);
});
