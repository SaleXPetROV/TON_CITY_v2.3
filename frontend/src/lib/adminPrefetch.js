/**
 * Admin panel: while the loading screen is shown, the data of EVERY section is really loaded — not only the main
 * page. Each section's first request (the one it makes when it opens) is answered from this preload at once, so a
 * section shows its data immediately instead of a spinner.
 *
 *   • SECTIONS — the requests every section makes when it opens (recorded from the panel itself);
 *   • prefetchAdminSections() — loads them all (a few at a time), reporting each section to the loading screen;
 *   • an axios interceptor answers a GET from the preload ONCE (later «Обновить» / polls go to the server as before);
 *     the preload is valid for TTL and is dropped entirely by any admin change (POST / PUT / PATCH / DELETE).
 */
import axios from 'axios';

const TTL = 10 * 60 * 1000;
const PARALLEL = 6;

// key → [label, [paths after /api]]
export const SECTIONS = [
  ['pfRevenue', 'Доходы и настройки', ['/admin/ledger/summary?period=30d', '/admin/ledger/entries?kind=&limit=100&before=',
    '/admin/maintenance', '/admin/settings/sender-wallet', '/admin/settings/email-2fa', '/admin/settings/deposit-address',
    '/admin/settings/telegram-bot', '/admin/transactions?skip=0&limit=50&lang=ru']],
  ['pfPromo', 'Промокоды: реферальный забег', ['/admin/promo/referral-rally/current', '/admin/promo/referral-rally/history']],
  ['pfContent', 'FAQ и дорожная карта', ['/admin/rules', '/admin/roadmap']],
  ['pfPlayers', 'Данные: игроки', ['/economy/config', '/admin/players/filter-options', '/admin/players/search?query=&skip=0&limit=100&sort=new']],
  ['pfPrices', 'Данные: цены, нагрузка, TG-бот', ['/admin/market/prices', '/admin/market/bot-listings', '/admin/load-stats', '/admin/telegram-bot-stats']],
  ['pfRegs', 'Данные: регистрации и рефералы', ['/admin/registrations', '/admin/settings/telegram-registration', '/admin/referrals?sort=active&offset=0&limit=100']],
  ['pfPresale', 'Данные: пресейл и выкуп', ['/admin/presale/inventory?map_id=ton_island', '/admin/presale', '/admin/presale/ready-buyers',
    '/admin/buyout/overview?search=&resource=all&status=with_lots&sort=units_desc', '/admin/buyout/nicks']],
  ['pfSkins', 'Данные: скины', ['/city-sprites/tuning', '/admin/skins/groups']],
  ['pfAds', 'Данные: реклама и альянсы', ['/admin/ads', '/island', '/city/districts', '/admin/alliances/config', '/admin/alliances?q=&status=active']],
  ['pfRetention', 'Удержание', ['/admin/analytics/overview?days=30&group=all']],
  ['pfMarket', 'Городской рынок', ['/admin/market-maker/analytics?days=7', '/admin/market-maker/trades?limit=30', '/admin/market-maker/catalog',
    '/admin/market-maker/stock/writeoffs?limit=20']],
  ['pfComeback', 'Бонус возвращения и лиги', ['/admin/comeback/stats?days=30', '/admin/leagues/analytics']],
  ['pfRecon', 'Сверка', ['/admin/reconciliation/report']],
  ['pfPass', 'City Pass и Founder Pass', ['/admin/pass/analytics', '/admin/founder-pass/settings', '/admin/founder-pass/applications?status=open',
    '/admin/founder-pass/holdings', '/admin/founder-pass/investors?q=&tier=&status=']],
  ['pfArcade', 'Игры (Аркада)', ['/admin/arcade', '/arcade?preview=true']],
  ['pfRental', 'Аренда', ['/admin/rental/config', '/admin/rental/stats?days=30']],
  ['pfContract', 'Контракт', ['/admin/contract-deployer', '/admin/contract-info', '/admin/settings/withdrawal-wallet']],
  ['pfSupport', 'Поддержка', ['/admin/support/agents', '/admin/support/settings']],
  ['pfTasks', 'Задания', ['/admin/offers', '/admin/tasks', '/admin/tasks/daily-rewards']],
  ['pfBiz', 'Бизнесы', ['/admin/business-config']],
];

const cache = new Map();          // normalized path → { res, t }
let installed = false;

/** The same request written two ways (params object / query string, any order) → one key. */
function keyOf(url) {
  try {
    const u = new URL(url, window.location.origin);
    const q = [...u.searchParams.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    const qs = q.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
    return `${u.pathname}${qs ? `?${qs}` : ''}`;
  } catch (_) {
    return url;
  }
}

export function installAdminCache() {
  if (installed) return;
  installed = true;
  axios.interceptors.request.use((config) => {
    const method = (config.method || 'get').toLowerCase();
    if (method !== 'get') {
      // an admin change — the preload may be stale (player-side calls such as the heartbeat do not count)
      if (cache.size && String(config.url || '').includes('/admin/')) cache.clear();
      return config;
    }
    if (!cache.size || config.__noPreload) return config;
    let full;
    try { full = axios.getUri(config); } catch (_) { return config; }
    const k = keyOf(full);
    const hit = cache.get(k);
    if (!hit) return config;
    cache.delete(k);                                 // answered once; the next request goes to the server
    if (Date.now() - hit.t > TTL) return config;
    return {
      ...config,
      adapter: () => Promise.resolve({ data: hit.res.data, status: hit.res.status, statusText: hit.res.statusText,
        headers: hit.res.headers, config, request: {} }),
    };
  });
}

export function clearAdminPreload() { cache.clear(); }

/**
 * Load every section. `onStep(key, status)` gets 'loading' / 'done' / 'error' for each section.
 * A section counts as done when all its requests have settled (a failed one is simply not preloaded).
 */
export async function prefetchAdminSections(api, headers, onStep) {
  installAdminCache();
  const queue = [...SECTIONS];
  const worker = async () => {
    while (queue.length) {
      const [key, , paths] = queue.shift();
      if (onStep) onStep(key, 'loading');
      const results = await Promise.allSettled(paths.map(async (p) => {
        const url = `${api}${p}`;
        const res = await axios.get(url, { headers, __noPreload: true });
        cache.set(keyOf(axios.getUri({ url })), { res, t: Date.now() });
      }));
      if (onStep) onStep(key, results.every((r) => r.status === 'rejected') ? 'error' : 'done');
    }
  };
  await Promise.all(Array.from({ length: PARALLEL }, worker));
}
