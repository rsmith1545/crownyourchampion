/* ───────────────────────────────────────────────────────────────
   setlist-proxy.js  —  Cloudflare Worker for Crown Your Champion
   Proxies setlist.fm's "search/setlists" API so the browser can use it
   without ever exposing the API key.

   SETUP:
     1. Cloudflare → Workers & Pages → Create Worker → paste this file.
     2. Worker → Settings → Variables and Secrets → add a SECRET:
            Name:  SETLISTFM_KEY
            Value: <your setlist.fm API key>
     3. Save & Deploy, then copy the Worker URL (…workers.dev) and
        send it to me to wire into the site.
   ─────────────────────────────────────────────────────────────── */

export default {
  async fetch(request, env) {
    // Only allow our own site to use this proxy (protects your quota).
    const origin = request.headers.get('Origin') || '';
    const allowOrigin = /^https:\/\/(www\.)?crownyourchampion\.com$/.test(origin)
      ? origin
      : 'https://crownyourchampion.com';

    const cors = {
      'Access-Control-Allow-Origin': allowOrigin,
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Accept, Content-Type',
      'Access-Control-Max-Age': '86400',
    };

    if (request.method === 'OPTIONS') return new Response(null, { headers: cors });
    if (request.method !== 'GET') return new Response('Method not allowed', { status: 405, headers: cors });

    // Forward only supported search params to setlist.fm
    const incoming = new URL(request.url).searchParams;
    const out = new URLSearchParams();
    for (const key of ['artistName', 'artistMbid', 'venueName', 'cityName', 'stateCode', 'year', 'date', 'p']) {
      const v = incoming.get(key);
      if (v) out.set(key, v);
    }

    const apiUrl = 'https://api.setlist.fm/rest/1.0/search/setlists?' + out.toString();

    let upstream;
    try {
      upstream = await fetch(apiUrl, {
        headers: { 'Accept': 'application/json', 'x-api-key': env.SETLISTFM_KEY },
        cf: { cacheTtl: 300, cacheEverything: true },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: 'upstream_fetch_failed' }), {
        status: 502, headers: { ...cors, 'Content-Type': 'application/json; charset=utf-8' },
      });
    }

    // setlist.fm returns 404 (with a body) when no results — pass through as-is
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: { ...cors, 'Content-Type': 'application/json; charset=utf-8' },
    });
  },
};
