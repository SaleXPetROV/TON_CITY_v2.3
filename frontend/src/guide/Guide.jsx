/**
 * The guide since 17 Nov 2026 (owner: «уменьши гид до 9 шагов… остальное — что и где находится на каждой странице»):
 *
 *  • EarnIntro — one window of 9 illustrated steps «как заработать», opens by itself the first time (server flag
 *    guide.intro_seen_at), again after «Пройти гид заново» or from the «?» of a page (event gc:earn-open)
 *  • page hints — the first time a player opens a page, its main parts are framed one by one with what they are for
 *    (the texts of the old guide steps, guideI18n.js, 9 languages); seen pages: guide.tours_seen; the «?» of a page
 *    replays them (event gc:page-tour). Nothing is pressed for the player, «Без подсказок» closes them.
 *  • the 3-day plan with its reward lives on the «Задания» page (PlanBlock.jsx)
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { ADMIN_PATH } from '@/lib/adminPath';
import { useLanguage } from '@/context/LanguageContext';
import { getResourceName, getResource } from '@/lib/resourceConfig';
import { useUiText } from '@/lib/uiI18n';
import L from '@/i18n/earn.json';
import { STEPS } from './guideData';
import EarnIntro from './EarnIntro';
import { gt, fill } from './guideI18n';
import './guide.css';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const TIER1_MIN_LOT = 10;   // the guide suggests a first lot of 10 units (any number can be listed since v2.3)
const LOCALE = { ru: 'ru-RU', en: 'en-US', es: 'es-ES', zh: 'zh-CN', fr: 'fr-FR', de: 'de-DE', ja: 'ja-JP', ko: 'ko-KR', id: 'id-ID' };

async function api(path, body) {
  const token = localStorage.getItem('token');
  const r = await fetch(`${API}/guide${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${token}`, ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

const explicitLang = () => { try { return !!localStorage.getItem('ton_city_lang_explicit'); } catch { return false; } };
// presses on the guide must not reach the page: an open dialog (the sell window…) would close as «pressed outside»;
// mousedown's default is cancelled so the focus stays where it is (a dialog's focus trap would also close it)
const keep = {
  onPointerDown: (e) => e.stopPropagation(),
  onMouseDown: (e) => { e.stopPropagation(); if (!/INPUT|TEXTAREA/.test(e.target.tagName)) e.preventDefault(); },
  onTouchStart: (e) => e.stopPropagation(),
};

const visible = (el) => {
  if (!el) return false;
  const b = el.getBoundingClientRect();
  if (b.width <= 2 || b.height <= 2 || b.bottom < 0 || b.right < 0 || b.top > window.innerHeight || b.left > window.innerWidth) return false;
  const st = window.getComputedStyle(el);
  return st.visibility !== 'hidden' && st.display !== 'none' && Number(st.opacity || 1) > 0.05;
};

/** Facts → text variables (names in the player's language, numbers in their locale). */
function useVars(facts, lang) {
  return useMemo(() => {
    const f = facts || {}, b = f.biz || {};
    const num = (v, d = 2) => Number(v || 0).toLocaleString(LOCALE[lang] || 'en-US', { maximumFractionDigits: d });
    const icon = (r) => getResource(r, lang)?.icon || '📦';
    const uses = Object.entries(b.uses || {});
    const ends = b.expires_at ? new Date(b.expires_at).toLocaleString(LOCALE[lang] || 'en-US', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—';
    return {
      biz: (b.name && (b.name[lang] || b.name.en || b.name.ru)) || '',
      bicon: b.icon || '🏭',
      prod: b.produces ? getResourceName(b.produces, lang) : '',
      pi: b.produces ? icon(b.produces) : '',
      rate: num(b.per_hour, 2), perday: num(b.per_day, 0),
      uses: uses.map(([r, v]) => `${num(v, 0)} ${icon(r)}`).join(' + '),
      raws: uses.map(([r]) => `${icon(r)} ${getResourceName(r, lang)}`).join(', '),
      price: num(f.system_price_city, 2), n: TIER1_MIN_LOT, up: num(b.upgrade_city, 0), ends,
      hours: b.per_hour ? Math.max(1, Math.round(1 / b.per_hour)) : '—',
      days: f.activity?.days ?? 10, bmin: f.activity?.buy_min ?? 40, smin: f.activity?.sell_min ?? 100,
      amt: (b.tier || 1) === 1 ? TIER1_MIN_LOT : 1, prodId: b.produces || '', raw: uses[0]?.[0] || '', raw2: uses[1]?.[0] || '', bid: b.id || '', lot: f.lot?.id || '',
    };
  }, [facts, lang]);
}

/** Rectangles of the step's targets, re-measured while the step is open (layout, scroll, dialogs opening). */
function useRects(step, vars) {
  const [rects, setRects] = useState([]);
  useEffect(() => {
    if (!step || !step.targets || !step.targets.length) { setRects([]); return undefined; }
    let scrolled = false;
    const measure = () => {
      const out = [];
      // the first target lies below or above the screen: bring it into view once (then measure again)
      if (!scrolled && step.targets[0] && !step.targets[0].minimap) {
        for (const s0 of step.targets[0].sel || []) {
          const q0 = fill(s0, { bid: vars.bid, lot: vars.lot, prod: vars.prodId, raw: vars.raw, raw2: vars.raw2 });
          if (/\{\w+\}/.test(q0)) continue;
          const el0 = document.querySelector(q0);
          if (el0) {
            const b0 = el0.getBoundingClientRect();
            if (b0.height > 0 && (b0.top < 0 || b0.bottom > window.innerHeight - 90) && window.getComputedStyle(el0).position !== 'fixed') {
              scrolled = true;
              el0.scrollIntoView({ block: 'center', behavior: 'auto' });
            }
            break;
          }
        }
      }
      step.targets.forEach((t, i) => {
        let r = null, el = null;
        if (t.minimap) r = window.__gcMap?.minimapRect?.() || null;
        else {
          for (const s of t.sel || []) {
            const q = fill(s, { bid: vars.bid, lot: vars.lot, prod: vars.prodId, raw: vars.raw, raw2: vars.raw2 });
            if (/\{\w+\}/.test(q)) continue;
            const cand = [...document.querySelectorAll(q)].find(visible);
            if (cand) { el = cand; break; }
          }
          if (el) { const b = el.getBoundingClientRect(); r = { left: b.left, top: b.top, width: b.width, height: b.height }; }
          else if (t.union) {                          // a group without its own box (the computer sidebar's sections)
            const bs = t.union.map((q) => document.querySelector(q)).filter(visible).map((x) => x.getBoundingClientRect());
            if (bs.length) {
              const l = Math.min(...bs.map((b) => b.left)), tp = Math.min(...bs.map((b) => b.top));
              r = { left: l, top: tp, width: Math.max(...bs.map((b) => b.right)) - l, height: Math.max(...bs.map((b) => b.bottom)) - tp };
            }
          }
        }
        if (r) {
          const p = t.pad == null ? 6 : t.pad;
          out.push({ i, el, x: r.left - p, y: r.top - p, w: r.width + 2 * p, h: r.height + 2 * p, rad: t.rad == null ? 14 : Math.min(t.rad, (r.height + 2 * p) / 2), bare: t.bare, badge: t.badge });
        }
      });
      setRects((prev) => (JSON.stringify(prev.map((o) => [o.i, Math.round(o.x), Math.round(o.y), Math.round(o.w), Math.round(o.h)]))
        === JSON.stringify(out.map((o) => [o.i, Math.round(o.x), Math.round(o.y), Math.round(o.w), Math.round(o.h)])) ? prev : out));
    };
    measure();
    const id = setInterval(measure, 250);
    window.addEventListener('resize', measure); window.addEventListener('scroll', measure, true);
    return () => { clearInterval(id); window.removeEventListener('resize', measure); window.removeEventListener('scroll', measure, true); };
  }, [step, vars.bid, vars.lot, vars.prodId, vars.raw, vars.raw2]); // eslint-disable-line react-hooks/exhaustive-deps
  return rects;
}

/** page → the hints shown on it (the old guide steps that describe that page; a hint whose element is not on the
 *  screen — no business yet, a desktop layout… — is passed over by itself) */
const TOURS = {
  '/my-businesses': ['s03', 's04', 's05', 's15', 's17', 's21'],
  '/maps': ['s08'],
  '/ton-island': ['s09', 's10', 's46'],
  '/resources': ['s24', 's25', 's26', 's27'],
  '/trading': ['s28', 's29', 's31', 's33'],
  '/trading:ops': ['s35', 's36'],
  '/analytics': ['s37'],
  '/security': ['s42'],
  '/history': ['s43'],
  '/tasks': ['s51', 's52', 's53', 's54'],
  '/city-pass': ['s55'],
  '/chat': ['s56'],
  '/community': ['s57', 's58'],
  '/settings': ['s60'],
  '/marketplace': ['s48'],
  '/credit': ['s49'],
};
const byId = (id) => STEPS.find((s) => s.id === id);
export const tourKey = (pathname, search) => {
  if (pathname === '/trading' && /tab=(operations|contracts|tenders)/.test(search || '')) return '/trading:ops';
  return TOURS[pathname] ? pathname : null;
};
const SEEN = 'gc_tours_seen';
const localSeen = () => { try { return JSON.parse(localStorage.getItem(SEEN) || '[]'); } catch { return []; } };

export default function Guide({ user }) {
  const { lang } = useLanguage();
  const loc = useLocation();
  const E = useUiText('earn', lang, L);
  const [data, setData] = useState(null);          // {state, facts}
  const [intro, setIntro] = useState(false);
  const [tour, setTour] = useState(null);           // {key, ids, i}
  const sheetRef = useRef(null);
  const ready = !!user?.id && !user?.is_blocked && (user.language_chosen || explicitLang());

  const load = useCallback(async () => {
    try { const d = await api(''); setData(d); return d; } catch { return null; }
  }, []);

  // first load: the 9-step window opens by itself once
  useEffect(() => {
    if (!ready) return;
    load().then((d) => { if (d && !d.state?.intro_seen) setIntro(true); });
  }, [ready, load]);

  // «?» of a page → the 9 steps / this page's hints again
  useEffect(() => {
    const open = () => { setTour(null); setIntro(true); };
    const replay = () => {
      const key = tourKey(window.location.pathname, window.location.search);
      if (key) setTour({ key, ids: TOURS[key], i: 0, manual: true });
    };
    window.addEventListener('gc:earn-open', open);
    window.addEventListener('gc:page-tour', replay);
    return () => { window.removeEventListener('gc:earn-open', open); window.removeEventListener('gc:page-tour', replay); };
  }, []);

  const closeIntro = useCallback(() => {
    setIntro(false);
    setData((d) => (d ? { ...d, state: { ...(d.state || {}), intro_seen: true } } : d));
    api('/intro-seen', {}).catch(() => {});
  }, []);

  // a page opened for the first time → its hints (a moment later, when the page has drawn itself)
  const seen = useMemo(() => new Set([...(data?.state?.tours_seen || []), ...localSeen()]), [data]);
  useEffect(() => {
    if (!ready || !data || intro || tour) return undefined;
    const key = tourKey(loc.pathname, loc.search);
    if (!key || seen.has(key)) return undefined;
    const t = setTimeout(() => setTour({ key, ids: TOURS[key], i: 0 }), 1200);
    return () => clearTimeout(t);
  }, [ready, data, intro, tour, loc.pathname, loc.search, seen]);
  // leaving the page ends its hints
  useEffect(() => {
    if (tour && tourKey(loc.pathname, loc.search) !== tour.key) setTour(null);
  }, [loc.pathname, loc.search]); // eslint-disable-line react-hooks/exhaustive-deps

  const finishTour = useCallback((all) => {
    setTour((t) => {
      if (t) {
        const keys = all ? Object.keys(TOURS) : [t.key];
        try { localStorage.setItem(SEEN, JSON.stringify([...new Set([...localSeen(), ...keys])])); } catch { /* private mode */ }
        keys.forEach((key) => api('/tour-seen', { key }).catch(() => {}));
        setData((d) => (d ? { ...d, state: { ...(d.state || {}), tours_seen: [...new Set([...(d.state?.tours_seen || []), ...keys])] } } : d));
      }
      return null;
    });
  }, []);

  const facts = useMemo(() => data?.facts || {}, [data]);
  const step = tour ? byId(tour.ids[tour.i]) : null;
  const vars = useVars(facts, lang);
  const rects = useRects(step && (step.targets || []).length ? step : null, vars);
  const T = (k) => gt(lang, k);
  const F = (k, extra) => fill(T(k), { ...vars, ...(extra || {}) });
  const next = useCallback(() => setTour((t) => {
    if (!t) return t;
    if (t.i + 1 >= t.ids.length) { setTimeout(() => finishTour(false), 0); return t; }
    return { ...t, i: t.i + 1 };
  }), [finishTour]);

  // a hint whose element is not on this screen (no business yet, another layout) is passed over by itself
  useEffect(() => {
    if (!step || !(step.targets || []).length) return undefined;
    const id = setTimeout(() => { if (!rects.some((r) => !r.bare)) next(); }, 1600);
    return () => clearTimeout(id);
  }, [step, rects, next]);

  // while a hint is open the page underneath does not react (only the hint's own buttons do)
  useEffect(() => {
    if (!step) return undefined;
    const block = (e) => {
      if (sheetRef.current && sheetRef.current.contains(e.target)) return;
      e.preventDefault(); e.stopPropagation();
    };
    const evs = ['pointerdown', 'mousedown', 'click', 'dblclick', 'contextmenu'];
    evs.forEach((ev) => document.addEventListener(ev, block, true));
    return () => evs.forEach((ev) => document.removeEventListener(ev, block, true));
  }, [step]);

  if (!ready) return null;
  // not over the admin panel, the landing or the sign-in screens: they are not the game
  if (loc.pathname === '/' || loc.pathname.startsWith('/auth') || (ADMIN_PATH && loc.pathname.startsWith(ADMIN_PATH))) return null;
  if (intro) return <EarnIntro lang={lang} onClose={closeIntro} />;
  if (!step || !tour) return null;

  const VW = window.innerWidth, VH = window.innerHeight;
  const textKey = (k) => {
    if (step.n === 27 && facts.biz?.tier === 3) return k === 'x' ? 'x3' : k;
    if (step.n === 31 && !facts.biz?.city_buys) return k === 'x' ? 'x2' : k;
    return k;
  };
  // the map hints have their own describing texts (the old steps said «press …», a hint only shows)
  const title = E[`h_${step.id}_t`] || F(`${step.id}.t`);
  const text = E[`h_${step.id}_x`] || F(`${step.id}.${textKey('x')}`);
  const main = rects.find((r) => !r.bare);
  const sheetPos = main ? (main.y + main.h / 2 > VH * 0.55 ? 'top' : 'bottom') : 'mid';
  const legend = step.legend ? T(`${step.id}.legend`) : null;
  const last = tour.i + 1 >= tour.ids.length;
  return (
    <div className="gcg-root" data-testid={`page-hint-${step.id}`}>
      <svg className="gcg-svg" width={VW} height={VH} aria-hidden="true">
        <defs><mask id="gcg-mask"><rect width={VW} height={VH} fill="white" />
          {rects.map((r) => <rect key={r.i} x={r.x} y={r.y} width={r.w} height={r.h} rx={r.rad} fill="black" />)}
        </mask></defs>
        <rect width={VW} height={VH} fill={`rgba(3,6,14,${step.dim == null ? 0.72 : step.dim})`} mask="url(#gcg-mask)" />
      </svg>
      {rects.filter((r) => !r.bare).map((r) => (
        <div key={r.i} className="gcg-ring view" style={{ left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: r.rad }} />
      ))}
      {rects.filter((r) => r.badge).map((r) => (
        <div key={`b${r.i}`} className="gcg-num" style={{ left: Math.max(4, r.x - 24), top: r.y + r.h / 2 - 11 }}>{r.badge}</div>
      ))}
      <div ref={sheetRef} className={`gcg-sheet ${sheetPos}`} data-testid="guide-sheet" {...keep}>
        <div className="gcg-top">
          <span className="gcg-chap">{fill(E.tour, { n: tour.i + 1, t: tour.ids.length })}</span>
          <button type="button" className="gcg-skip" onClick={() => finishTour(!tour.manual)} data-testid="page-hint-off">{E.tour_skip}</button>
        </div>
        <div className="gcg-bar"><i style={{ width: `${Math.round(((tour.i + 1) / tour.ids.length) * 100)}%` }} /></div>
        <h3 className="gcg-title" dangerouslySetInnerHTML={{ __html: title }} />
        <p className="gcg-text" dangerouslySetInnerHTML={{ __html: text }} />
        {Array.isArray(legend) && (
          <ul className="gcg-leg">{legend.map((l, i) => <li key={i}><i>{i + 1}</i><span dangerouslySetInnerHTML={{ __html: l }} /></li>)}</ul>
        )}
        <div className="gcg-foot">
          <span className="gcg-prog" />
          <button type="button" className="gcg-btn" onClick={next} data-testid="guide-next">{last ? E.tour_ok : E.next}</button>
        </div>
      </div>
    </div>
  );
}

export { STEPS };
