/**
 * The in-game guide: 62 steps in 10 chapters + screen 63 («План выполнен»).
 *
 * A step is one of
 *   show    — a yellow dashed «view only» frame; the whole screen is shielded, only «Далее» works
 *   action  — a solid frame; ONLY the framed element can be pressed, the guide moves on by itself (`until`)
 *   locked  — like show, for what opens later (level 1 etc.)
 *   card    — a full card of the guide itself (welcome, «Бизнес ваш!», first batch, plan…)
 *
 * Targets are lists of selectors: the first VISIBLE one is used (phone bottom bar vs computer sidebar).
 * `{bid}` / `{lot}` / `{prod}` / `{raw}` are filled from the server facts (GET /api/guide).
 * Texts live in guideI18n.js under the step id, in all 9 languages; the numbers in them come from the facts too.
 */

export const TOTAL = 62;

export const CHAPTERS = [
  { no: 0, from: 1, to: 6 }, { no: 1, from: 7, to: 13 }, { no: 2, from: 14, to: 22 }, { no: 3, from: 23, to: 27 },
  { no: 4, from: 28, to: 38 }, { no: 5, from: 39, to: 43 }, { no: 6, from: 44, to: 50 }, { no: 7, from: 51, to: 55 },
  { no: 8, from: 56, to: 59 }, { no: 9, from: 60, to: 63 },
];
export const chapterOf = (n) => CHAPTERS.find((c) => n >= c.from && n <= c.to) || CHAPTERS[CHAPTERS.length - 1];

// navigation entries: phone bottom bar first, computer sidebar second
const NAV = {
  map: ['[data-testid=bottom-nav-map]', '[data-testid=sidebar-nav-map]'],
  business: ['[data-testid=bottom-nav-business]', '[data-testid=sidebar-nav-my-businesses]'],
  resources: ['[data-testid=bottom-nav-resources]', '[data-testid=sidebar-nav-warehouse]'],
  trading: ['[data-testid=bottom-nav-trading]', '[data-testid=sidebar-nav-trading]'],
};
const at = (p) => (c) => c.path === p;
const startsAt = (p) => (c) => c.path.startsWith(p);

// returning players (they already have a business): these steps are not shown
export const SKIP_RETURNING = new Set([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 22, 27, 30, 31, 32, 33, 34, 44, 52]);

export const STEPS = [
  // ── 0 · Знакомство ── (step 1 is the project's own «Choose your language» window)
  { n: 2, id: 's02', kind: 'card', card: 'welcome', route: '/my-businesses' },
  { n: 3, id: 's03', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=header-city-balance]', '[data-testid=sidebar-balance-city]'] }], why: true, whyOpen: true },
  { n: 4, id: 's04', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=bottom-nav]'], union: ['[data-testid=sidebar-nav-map]', '[data-testid=sidebar-nav-chat]'], rad: 18 }], sheet: 'mid' },
  { n: 5, id: 's05', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=header-burger-btn]', '[data-testid=sidebar-nav-wiki]'] }] },
  { n: 6, id: 's06', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=header-notif-bell]', '[data-testid=sidebar-nav-notifications]'] }, { sel: ['[data-testid=header-referrals-btn]'] }] },
  // ── 1 · Своя земля ──
  { n: 7, id: 's07', kind: 'action', route: '/my-businesses', targets: [{ sel: NAV.map }], sheet: 'mid', until: startsAt('/maps') },
  { n: 8, id: 's08', kind: 'action', route: '/maps', targets: [{ sel: ['[data-testid=city-card-ton_island]', '[data-testid^=city-card-]'] }], until: (c) => c.path === '/ton-island' || c.path === '/island' },
  { n: 9, id: 's09', kind: 'show', route: '/ton-island', sheet: 'top', dim: 0.66, targets: [
    { sel: ['[data-testid=map-tools-find]'], pad: 2, badge: 1 }, { sel: ['[data-testid=map-tools-zoom]'], pad: 2, badge: 2 },
    { minimap: true, pad: 0, badge: 3 }, { sel: ['[data-testid=map-sale-btn]'], rad: 999, pad: 0, badge: 4 }], legend: 4 },
  { n: 10, id: 's10', kind: 'action', route: '/ton-island', sheet: 'top', targets: [{ sel: ['[data-testid=map-sale-btn]'], rad: 999 }, { sel: ['[data-testid=map-sale-hint]'], bare: true }],
    until: (c) => !!document.querySelector('[data-testid=map-sale-sheet]') },
  { n: 11, id: 's11', kind: 'action', route: '/ton-island', sheet: 'bottom', dim: 0.55, targets: [{ sel: ['[data-testid=map-sale-sheet] .overflow-y-auto', '[data-testid=map-sale-sheet]'] }],
    until: (c) => !!document.querySelector('[data-testid=buy-plot-btn]') || c.facts.has_business },
  { n: 12, id: 's12', kind: 'action', route: '/ton-island', sheet: 'top', targets: [{ sel: ['[data-testid=buy-plot-btn]'] }, { sel: ['[data-testid=zero-stake-warning]'], bare: true }],
    until: (c) => c.facts.has_business, needFacts: true },
  { n: 13, id: 's13', kind: 'card', card: 'claimed', route: '/ton-island' },
  // ── 2 · Производство ──
  { n: 14, id: 's14', kind: 'action', route: '/ton-island', targets: [{ sel: NAV.business }], sheet: 'mid', until: at('/my-businesses') },
  { n: 15, id: 's15', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=business-card-{bid}]', '[data-testid^=business-card-]'] }], sheet: 'top' },
  { n: 16, id: 's16', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=work-status-{bid}]'] }], sheet: 'top', why: true },
  { n: 17, id: 's17', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=income-chip-{bid}]'], pad: 2 }, { sel: ['[data-testid=expense-chip-{bid}]'], pad: 2 }], sheet: 'top' },
  { n: 18, id: 's18', kind: 'action', route: '/my-businesses', targets: [{ sel: ['[data-testid=start-shift-btn-{bid}]'] }], sheet: 'top', until: (c) => c.facts.biz?.shift_active, needFacts: true },
  { n: 19, id: 's19', kind: 'card', card: 'batch', route: '/my-businesses' },
  { n: 20, id: 's20', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=durability-value-{bid}]', '[data-testid=work-status-{bid}]'] }, { sel: ['[data-testid=action-repair-{bid}]'] }], sheet: 'top' },
  { n: 21, id: 's21', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=biz-side-tasks]'] }, { sel: ['[data-testid=biz-side-marketplace]'] }, { sel: ['[data-testid=biz-side-analytics]'] }, { sel: ['[data-testid=biz-side-chat]'] }], sheet: 'top' },
  { n: 22, id: 's22', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=zero-lease-timer]'] }, { sel: ['[data-testid=action-upgrade-{bid}]'] }], sheet: 'top', when: (f) => f.biz?.is_zero },
  // ── 3 · Склад ──
  { n: 23, id: 's23', kind: 'action', route: '/my-businesses', targets: [{ sel: NAV.resources }], sheet: 'mid', until: at('/resources') },
  { n: 24, id: 's24', kind: 'show', route: '/resources', targets: [{ sel: ['[data-testid=resources-warehouse]', '[data-testid=resources-open-businesses]'] }, { sel: ['[data-testid=resources-warehouse-value]'] }] },
  { n: 25, id: 's25', kind: 'show', route: '/resources', targets: [{ sel: ['[data-testid=resources-warehouse]'] }], why: true },
  { n: 26, id: 's26', kind: 'show', route: '/resources', targets: [{ sel: ['[data-testid=resources-tab-boosters]'] }], why: true },
  { n: 27, id: 's27', kind: 'show', route: '/resources', targets: [{ sel: ['[data-testid=resource-card-{prod}]'], pad: 1 }, { sel: ['[data-testid=resource-card-{raw}]'], pad: 1 }, { sel: ['[data-testid=resource-card-{raw2}]'], pad: 1 }] },
  // ── 4 · Торговля ──
  { n: 28, id: 's28', kind: 'show', route: '/trading', targets: [{ sel: ['[data-testid=tutorial-trading-tab-buy]'] }, { sel: ['[data-testid=buy-filters-open]'] }] },
  { n: 29, id: 's29', kind: 'show', route: '/trading', targets: [{ sel: ['[data-testid^=market-lot-]'] }] },
  { n: 30, id: 's30', kind: 'action', route: '/trading?tab=my', targets: [{ sel: ['[data-testid=tutorial-create-lot-btn]'] }],
    until: () => !!document.querySelector('[data-testid=sell-confirm-btn]'), when: (f) => f.biz?.tier !== 3 },
  { n: 31, id: 's31', kind: 'show', route: '/trading?tab=my&sell={prodId}&amount={amt}', targets: [{ sel: ['[data-testid=sell-price-wrap]'] }], sheet: 'top', when: (f) => f.biz?.tier !== 3 },
  { n: 32, id: 's32', kind: 'action', route: '/trading?tab=my&sell={prodId}&amount={amt}', targets: [{ sel: ['[data-testid=sell-amount-input]'], pad: 3 }, { sel: ['[data-testid=sell-confirm-btn]'] }], sheet: 'top',
    until: (c) => !!c.facts.lot, needFacts: true, when: (f) => f.biz?.tier !== 3 },
  { n: 33, id: 's33', kind: 'show', route: '/trading?tab=my', targets: [{ sel: ['[data-testid=my-lot-{lot}]', '[data-testid^=my-lot-]'] }], when: (f) => f.biz?.tier !== 3 },
  { n: 34, id: 's34', kind: 'card', card: 'citybuy', route: '/trading?tab=my', when: (f) => f.biz?.city_buys && !!f.lot },
  { n: 35, id: 's35', kind: 'show', route: '/trading', targets: [{ sel: ['[data-testid=operations-tab]'] }] },
  { n: 36, id: 's36', kind: 'show', route: '/trading', targets: [{ sel: ['[data-testid=tenders-tab-exchange]'] }, { sel: ['[data-testid=tenders-tab-purchases]'] }, { sel: ['[data-testid=tenders-tab-supplies]'] }] },
  { n: 37, id: 's37', kind: 'show', route: '/analytics', targets: [] },
  { n: 38, id: 's38', kind: 'card', card: 'maindone', route: '/my-businesses' },
  // ── 5 · Деньги ──
  { n: 39, id: 's39', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=header-city-balance]', '[data-testid=sidebar-balance-city]'] }] },
  { n: 40, id: 's40', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=sidebar-deposit-btn]', '[data-testid=header-city-balance]'] }] },
  { n: 41, id: 's41', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=sidebar-withdraw-btn]', '[data-testid=header-city-balance]'] }] },
  { n: 42, id: 's42', kind: 'show', route: '/security', targets: [{ sel: ['[data-testid=add-passkey-btn]'] }, { sel: ['[data-testid=enable-2fa-btn]'] }], sheet: 'top', why: true },
  { n: 43, id: 's43', kind: 'show', route: '/history', targets: [{ sel: ['[data-testid=tx-type-filter]'] }] },
  // ── 6 · Рост ──
  { n: 44, id: 's44', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=action-upgrade-{bid}]'] }], sheet: 'top', when: (f) => (f.biz?.level || 0) === 0 },
  { n: 45, id: 's45', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=action-repair-{bid}]'] }], sheet: 'top' },
  { n: 46, id: 's46', kind: 'show', route: '/ton-island', targets: [] },
  { n: 47, id: 's47', kind: 'locked', route: '/resources', targets: [{ sel: ['[data-testid=resource-missing-neuro_core]', '[data-testid=resource-card-neuro_core]'] }] },
  { n: 48, id: 's48', kind: 'locked', route: '/marketplace', targets: [{ sel: ['[data-testid=marketplace-tabs]'] }] },
  { n: 49, id: 's49', kind: 'locked', route: '/credit', targets: [{ sel: ['[data-testid=apply-credit-btn]'] }] },
  { n: 50, id: 's50', kind: 'card', card: 'activity', route: '/my-businesses' },
  // ── 7 · Награды ──
  { n: 51, id: 's51', kind: 'show', route: '/tasks', targets: [{ sel: ['[data-testid=daily-login-card]'] }] },
  { n: 52, id: 's52', kind: 'show', route: '/tasks', targets: [{ sel: ['[data-testid=quest-onboarding]', '[data-testid^=quest-progress-]'] }] },
  { n: 53, id: 's53', kind: 'show', route: '/tasks', targets: [{ sel: ['[data-testid=quest-daily]'] }] },
  { n: 54, id: 's54', kind: 'show', route: '/tasks', targets: [{ sel: ['[data-testid=tasks-tab-partners]'] }] },
  { n: 55, id: 's55', kind: 'show', route: '/city-pass', targets: [{ sel: ['[data-testid=pass-header]'] }] },
  // ── 8 · Сообщество ──
  { n: 56, id: 's56', kind: 'show', route: '/chat', targets: [{ sel: ['[data-testid=chat-channels]'] }] },
  { n: 57, id: 's57', kind: 'show', route: '/community', targets: [{ sel: ['[data-testid=league-div-prev]'] }, { sel: ['[data-testid=league-div-next]'] }, { sel: ['[data-testid=league-mode]'] }] },
  { n: 58, id: 's58', kind: 'locked', route: '/community', targets: [{ sel: ['[data-testid=community-tab-alliance]'] }] },
  { n: 59, id: 's59', kind: 'action', route: '/my-businesses', targets: [{ sel: ['[data-testid=header-referrals-btn]'] }],
    until: () => !!document.querySelector('[data-testid=referral-modal]'), skipIfMissing: true },
  // ── 9 · Помощь ──
  { n: 60, id: 's60', kind: 'show', route: '/settings', targets: [{ sel: ['[data-testid=settings-smart-notifications]'] }] },
  { n: 61, id: 's61', kind: 'show', route: '/my-businesses', targets: [{ sel: ['[data-testid=header-burger-btn]', '[data-testid=sidebar-nav-wiki]'] }, { sel: ['[data-testid=sidebar-support-btn]'] }] },
  { n: 62, id: 's62', kind: 'card', card: 'plan', route: '/my-businesses' },
  { n: 63, id: 'p01', kind: 'card', card: 'reward', route: '/my-businesses' },
];

export const stepByN = (n) => STEPS.find((s) => s.n === n);

/** The next step for this player (returning players and tier 2–3 businesses skip some). */
export function nextStep(n, f, path) {
  let k = n + 1;
  while (k <= 63) {
    const s = stepByN(k);
    if (!s) { k += 1; continue; }
    if (path === 'returning' && SKIP_RETURNING.has(k)) { k += 1; continue; }
    if (s.when && !s.when(f || {})) { k += 1; continue; }
    if (k === 62 && path === 'returning' && (f || {}).plan_done) return 63;   // plan already done: straight to 63
    if (k === 63 && !(f || {}).plan_done) return 64;   // the plan is not done yet: the guide ends at 62
    return k;
  }
  return 64;
}
