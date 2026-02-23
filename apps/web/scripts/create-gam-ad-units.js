#!/usr/bin/env node
/**
 * Create the four theNewslane ad units in Google Ad Manager via the API.
 *
 * Prerequisites:
 *   - Google Cloud project with Ad Manager API enabled
 *   - Service account or OAuth2 with access to the GAM network
 *   - Set GOOGLE_APPLICATION_CREDENTIALS (service account JSON) or run `gcloud auth application-default login`
 *
 * Usage:
 *   node scripts/create-gam-ad-units.js
 *   GAM_NETWORK_CODE=23173092177 node scripts/create-gam-ad-units.js
 *
 * The script uses the Ad Manager API (Beta) REST endpoints. If @google-ads/admanager
 * is not installed or the API is unavailable, create the units manually — see
 * docs/GAM_AD_UNITS_SETUP.md.
 */

const NETWORK_CODE = process.env.GAM_NETWORK_CODE || '23173092177';

const AD_UNITS = [
  { name: 'Header Leaderboard', path: 'header_leaderboard', sizes: [[728, 90], [970, 90]] },
  { name: 'Article Rectangle', path: 'article_rectangle', sizes: [[300, 250], [300, 600]] },
  { name: 'In Content', path: 'in_content', sizes: [[300, 250], [336, 280]] },
  { name: 'Mobile Anchor', path: 'mobile_anchor', sizes: [[320, 50], [320, 100]] },
];

async function getAccessToken() {
  const credsPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (!credsPath) {
    console.warn('GOOGLE_APPLICATION_CREDENTIALS not set. Use a service account JSON or run: gcloud auth application-default login');
    return null;
  }
  try {
    const { GoogleAuth } = await import('google-auth-library');
    const auth = new GoogleAuth({ scopes: ['https://www.googleapis.com/auth/dfp'] });
    const client = await auth.getClient();
    const token = await client.getAccessToken();
    return token.token;
  } catch (e) {
    console.error('Failed to get access token:', e.message);
    return null;
  }
}

async function createAdUnits(accessToken) {
  const baseUrl = `https://admanager.googleapis.com/v1/networks/${NETWORK_CODE}`;
  const created = [];

  for (const unit of AD_UNITS) {
    const parent = `networks/${NETWORK_CODE}`;
    const body = {
      name: unit.name,
      adUnitCode: unit.path,
      targetWindow: 'TOP',
      appliedTeamIds: [],
      size: { width: unit.sizes[0][0], height: unit.sizes[0][1] },
      // API may require parent ad unit id; use root if needed
    };

    try {
      const res = await fetch(`${baseUrl}/adUnits`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const data = await res.json();
        created.push({ name: unit.name, path: unit.path, id: data.name });
        console.log('Created:', unit.name, '→', unit.path);
      } else {
        const text = await res.text();
        console.warn(`Failed to create ${unit.name}: ${res.status} ${text}`);
      }
    } catch (e) {
      console.warn(`Error creating ${unit.name}:`, e.message);
    }
  }

  return created;
}

async function main() {
  console.log('GAM Ad Unit creation — network', NETWORK_CODE);
  console.log('');

  const token = await getAccessToken();
  if (!token) {
    console.log('Could not obtain credentials. Create ad units manually — see docs/GAM_AD_UNITS_SETUP.md');
    process.exit(1);
  }

  const created = await createAdUnits(token);
  console.log('');
  console.log('Created', created.length, 'of', AD_UNITS.length, 'ad units.');
  if (created.length < AD_UNITS.length) {
    console.log('Create any missing units manually in GAM UI. Paths:', AD_UNITS.map(u => `/${NETWORK_CODE}/${u.path}`).join(', '));
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
