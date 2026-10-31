/** Monetag rewarded ads for the Telegram Mini App.
 *  The SDK tag is set by the admin (admin → «Данные» → «Monetag»); /api/ads/config returns what was parsed from it:
 *  sdk_src (e.g. https://libtl.com/sdk.js), zone_id (data-zone) and sdk_fn (data-sdk, e.g. show_10012345).
 *
 *  showRewardedAd(cfg, ymid, requestVar):
 *    1) preload with a timeout — «no ad right now» (Empty feed) or a slow network fails in seconds instead of
 *       leaving the button spinning forever;
 *    2) show (type 'end') with the SAME ymid/requestVar (Monetag reuses the preloaded ad only then);
 *    3) a safety timeout: if the SDK never settles the promise, it rejects with «Timeout».
 *  Resolves with Monetag's result ({reward_event_type: 'valued' | 'non_valued'} on zones with reward postback,
 *  otherwise undefined). Rejects with an Error whose .code is 'no_fill' | 'timeout' | 'sdk' | 'failed'. */
const loaded = {};
let inFlight = null;

// Report what the browser's Content-Security-Policy blocks while ads run (once per host per session) — the admin
// sees it in «Данные» → «Monetag» → errors, e.g. «csp:script-src-elem:yoszi.com» or «csp:script-src:eval».
let cspHooked = false;
const cspSeen = new Set();
function hookCspReports() {
  if (cspHooked || typeof document === 'undefined') return;
  cspHooked = true;
  document.addEventListener('securitypolicyviolation', (e) => {
    try {
      let host = e.blockedURI || '';
      if (host && host !== 'eval' && host !== 'inline') { try { host = new URL(host).host; } catch (_) { /* keep */ } }
      const key = `csp:${e.effectiveDirective || e.violatedDirective}:${host || 'inline'}`;
      if (cspSeen.has(key) || cspSeen.size > 20) return;
      cspSeen.add(key);
      const token = localStorage.getItem('token');
      if (!token) return;
      fetch(`${process.env.REACT_APP_BACKEND_URL || ''}/api/ads/client-error`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: key }),
      }).catch(() => {});
    } catch (_) { /* never break the page */ }
  });
}

function loadSdk({ zone_id: zone, sdk_src: src, sdk_fn: fnName }) {
  hookCspReports();
  const fn = fnName || `show_${zone}`;
  const key = `${src}|${fn}`;
  if (loaded[key]) return loaded[key];
  loaded[key] = new Promise((resolve, reject) => {
    if (typeof window[fn] === 'function') { resolve(window[fn]); return; }
    const s = document.createElement('script');
    s.src = src || 'https://libtl.com/sdk.js';
    s.async = true;
    s.dataset.zone = String(zone);
    s.dataset.sdk = fn;
    s.onload = () => {
      let tries = 0;
      const wait = () => {                      // the SDK defines show_<zone> right after loading
        if (typeof window[fn] === 'function') resolve(window[fn]);
        else if (tries++ > 50) { delete loaded[key]; reject(Object.assign(new Error('sdk'), { code: 'sdk' })); }
        else setTimeout(wait, 100);
      };
      wait();
    };
    s.onerror = () => { delete loaded[key]; s.remove(); reject(Object.assign(new Error('sdk'), { code: 'sdk' })); };
    document.head.appendChild(s);
  });
  return loaded[key];
}

function norm(e) {
  const msg = String((e && e.message) || e || 'failed');
  const low = msg.toLowerCase();
  const code = low.includes('empty') ? 'no_fill' : low.includes('timeout') ? 'timeout' : (e && e.code) || 'failed';
  return Object.assign(new Error(msg), { code });
}

function withTimeout(p, ms) {
  let tm;
  return Promise.race([
    p.finally(() => clearTimeout(tm)),
    new Promise((_, rej) => { tm = setTimeout(() => rej(Object.assign(new Error('Timeout'), { code: 'timeout' })), ms); }),
  ]);
}

/* ───────── early preload (Monetag's advice) ─────────
 * The ad is preloaded in the background when the Mini App opens / the daily-bonus page opens — not at the moment of
 * the press — so it is ready by then. At the press: preloaded → shown at once; still loading → wait a few seconds;
 * preload failed (no ad for this player right now) → no Monetag this time, the next network in the admin's order
 * is used instead of a 25-second «Timeout». The preload is tied to its ymid (the same ymid must be shown). */
const WARM_TTL_MS = 10 * 60 * 1000;
const WARM_WAIT_MS = 8000;
let warm = null;           // {ymid, requestVar, state: 'loading' | 'ready' | 'failed', at, promise, error}

export function warmUpMonetag(cfg, ymid, requestVar = 'daily_bonus') {
  if (!cfg?.zone_id || cfg?.monetag === false || !ymid) return null;
  if (warm && warm.state !== 'failed' && Date.now() - warm.at < WARM_TTL_MS) return warm;
  const w = { ymid, requestVar, state: 'loading', at: Date.now() };
  w.promise = (async () => {
    try {
      const show = await loadSdk(cfg);
      await withTimeout(show({ type: 'preload', ymid, requestVar, timeout: 60 }), 65000);
      w.state = 'ready';
    } catch (e) {
      w.state = 'failed';
      w.error = norm(e);
    }
    return w;
  })();
  warm = w;
  return w;
}

/** The ymid of a fresh early preload for this placement (the caller shows the ad with it), or null. */
export function warmYmid(requestVar = 'daily_bonus') {
  if (!warm || warm.requestVar !== requestVar || Date.now() - warm.at >= WARM_TTL_MS) return null;
  if (warm.state === 'failed' && Date.now() - warm.at > 60000) return null;     // an old failure: try again
  return warm.ymid;
}

/** opts (all optional): onStep(step, data) — the admin's «Проверка рекламы» logs every step with its time;
 *  skipPreload — show at once (type 'end' preloads by itself); preloadTimeout — seconds for the preload. */
function showMonetag(cfg, ymid, requestVar, opts, step) {
  const preloadSec = Number(opts.preloadTimeout) || 25;
  return (async () => {
    let t0 = performance.now();
    step('sdk_load', { src: cfg?.sdk_src, fn: cfg?.sdk_fn || `show_${cfg?.zone_id}`, already: typeof window[cfg?.sdk_fn || `show_${cfg?.zone_id}`] === 'function' });
    const show = await loadSdk(cfg);
    step('sdk_ready', { ms: Math.round(performance.now() - t0) });
    const opts2 = { ymid: ymid || undefined, requestVar };
    let preloaded = false;
    const w = warm && ymid && warm.ymid === ymid ? warm : null;
    if (w) {
      warm = null;                                     // a preload is shown once
      if (w.state === 'loading') {
        step('warm_wait', { s: Math.round((Date.now() - w.at) / 1000) });
        await Promise.race([w.promise, new Promise((ok) => setTimeout(ok, WARM_WAIT_MS))]);
      }
      if (w.state === 'failed') {
        step('warm_failed', { code: w.error?.code, message: w.error?.message });
        throw Object.assign(new Error(w.error?.message || 'no ad'), { code: 'no_fill' });   // → the next network
      }
      step(w.state === 'ready' ? 'warm_ready' : 'warm_still_loading', { s: Math.round((Date.now() - w.at) / 1000) });
      preloaded = w.state === 'ready';
      opts.skipPreload = true;
    }
    if (!opts.skipPreload) {
      t0 = performance.now();
      step('preload_start', { timeout_s: preloadSec });
      try {
        await withTimeout(show({ type: 'preload', ...opts2, timeout: preloadSec }), (preloadSec + 5) * 1000);
        step('preload_ok', { ms: Math.round(performance.now() - t0) });
        preloaded = true;
      } catch (e) {
        const n = norm(e);
        step('preload_error', { ms: Math.round(performance.now() - t0), code: n.code, message: n.message });
        if (n.code === 'no_fill' || n.code === 'timeout') throw n;
        // other preload errors: try to show anyway (older SDK builds)
      }
    }
    t0 = performance.now();
    step('show_start', {});
    try {
      // 'timeout' limits only the loading step (the time on screen is not limited); the ad is already preloaded,
      // so its creative gets 90 s to open on a slow network instead of being cut at 25 s
      const res = await withTimeout(show({ type: 'end', ...opts2, timeout: preloaded ? Math.max(preloadSec, 90) : preloadSec }), 180000);
      step('show_closed', { ms: Math.round(performance.now() - t0), result: res ?? null });
      return res;
    } catch (e) {
      const n = norm(e);
      step('show_error', { ms: Math.round(performance.now() - t0), code: n.code, message: n.message });
      throw n;
    }
  })();
}

/* ───────── AdsGram (ads made for Telegram Mini Apps): https://docs.adsgram.ai ───────── */
const ADSGRAM_SRC = 'https://sad.adsgram.ai/js/sad.min.js';
let adsgramLoading = null;
function loadAdsgram() {
  if (typeof window !== 'undefined' && window.Adsgram) return Promise.resolve(window.Adsgram);
  if (adsgramLoading) return adsgramLoading;
  adsgramLoading = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = ADSGRAM_SRC; s.async = true;
    s.onload = () => (window.Adsgram ? resolve(window.Adsgram) : reject(Object.assign(new Error('sdk'), { code: 'sdk' })));
    s.onerror = () => { adsgramLoading = null; s.remove(); reject(Object.assign(new Error('sdk'), { code: 'sdk' })); };
    document.head.appendChild(s);
  });
  return adsgramLoading;
}
async function showAdsgram(cfg, opts, step) {
  const blockId = String(cfg?.adsgram?.block_id || '');
  let t0 = performance.now();
  if (!window.Telegram?.WebApp?.initData) {
    // AdsGram works only inside a Telegram Mini App (it reads Telegram's launch parameters): in a browser it would
    // spend ~30 s and fail with «Unable to retrieve launch parameters» — skip it at once (the next network is tried)
    step('adsgram_error', { code: 'sdk', description: 'AdsGram работает только внутри Telegram (Mini App) — в браузере пропущен' });
    throw Object.assign(new Error('AdsGram работает только внутри Telegram'), { code: 'sdk', adsgram: { not_telegram: true } });
  }
  step('adsgram_load', { block_id: blockId });
  const A = await loadAdsgram();
  step('adsgram_ready', { ms: Math.round(performance.now() - t0) });
  t0 = performance.now();
  step('adsgram_show', {});
  try {
    const ctrl = A.init({ blockId, ...(opts.adsgramDebug ? { debug: true } : {}) });
    const r = await withTimeout(Promise.resolve(ctrl.show()), 180000);
    step('adsgram_result', { ms: Math.round(performance.now() - t0), result: r });
    if (r && r.done === false) throw Object.assign(new Error(r.description || 'skipped'), { code: 'skipped', adsgram: r });
    return { network: 'adsgram', reward_event_type: 'valued' };
  } catch (e) {
    if (e?.code) throw e;
    const r = e || {};                                   // AdsGram rejects with {done, description, state, error}
    const d = String(r.description || r.message || 'failed');
    const code = /no.*banner|not.*found|no ads|empty/i.test(d) ? 'no_fill' : r.error === false ? 'skipped' : 'failed';
    step('adsgram_error', { ms: Math.round(performance.now() - t0), code, description: d, state: r.state });
    if (/not active|moderation/i.test(d)) {
      // the block is on moderation / switched off: the server stops sending players to AdsGram for 2 hours
      try {
        const token = localStorage.getItem('token');
        if (token) {
          fetch(`${process.env.REACT_APP_BACKEND_URL || ''}/api/ads/adsgram-inactive`, {
            method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ description: d.slice(0, 200) }),
          }).catch(() => {});
        }
      } catch (_) { /* ignore */ }
    }
    throw Object.assign(new Error(d), { code, adsgram: r });
  }
}

/** Shows ONE rewarded ad: the networks are tried in the admin's order («Monetag, если нет рекламы — AdsGram» …);
 *  the next one is used only when the first has no ad / did not load. opts.only = 'monetag' | 'adsgram' (admin tests). */
export function showRewardedAd(cfg, ymid, requestVar = 'daily_bonus', opts = {}) {
  if (inFlight) return inFlight;               // never call the SDK twice at the same time
  const step = (k, d) => { try { if (opts.onStep) opts.onStep(k, d); } catch (_) { /* ignore */ } };
  const hasM = cfg?.monetag !== false && !!(cfg?.zone_id);
  const hasA = !!cfg?.adsgram?.enabled && !!cfg?.adsgram?.block_id;
  const order = cfg?.order || 'monetag_first';
  let nets = order === 'adsgram_first' ? ['adsgram', 'monetag'] : order === 'adsgram' ? ['adsgram'] : order === 'monetag' ? ['monetag'] : ['monetag', 'adsgram'];
  nets = nets.filter((n) => (n === 'monetag' ? hasM : hasA));
  if (opts.only) nets = [opts.only];
  inFlight = (async () => {
    let last = Object.assign(new Error('no_network'), { code: 'sdk' });
    for (const n of nets) {
      try {
        const res = n === 'adsgram' ? await showAdsgram(cfg, opts, step) : await showMonetag(cfg, ymid, requestVar, opts, step);
        return res && typeof res === 'object' ? { network: n, ...res } : { network: n };
      } catch (e) {
        last = e;
        // the player closed / skipped the ad → no second ad; ANY other failure of a network (no ad, timeout, the
        // SDK did not load, «Block … is not active», …) → the next network in the admin's order
        if (e?.code === 'skipped') throw e;
        step('next_network', { failed: n, code: e?.code });
      }
    }
    throw last;
  })().finally(() => { inFlight = null; });
  return inFlight;
}
