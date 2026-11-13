/**
 * The in-game guide (62 steps + screen 63) drawn over the real pages of the project.
 *
 *  • progress lives on the server (/api/guide): closing the app resumes on the same step; no «Skip» button
 *  • «show» / «locked» steps: everything is shielded, only «Далее» works; «action» steps: ONLY the framed elements
 *    react (a capture-phase listener cancels every other press), the guide moves on by itself
 *  • texts adapt to the business the player took (name, goods, raw materials, numbers) — guideI18n.js, 9 languages
 *  • after the guide: when the 3-day plan gets done (a business of level 1+), screen 63 opens by itself
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLanguage } from '@/context/LanguageContext';
import { getResourceName, getResource } from '@/lib/resourceConfig';
import { tResourceBuff } from '@/lib/translationsExtra';
import { STEPS, TOTAL, chapterOf, nextStep, stepByN } from './guideData';
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

export default function Guide({ user }) {
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const loc = useLocation();
  const [data, setData] = useState(null);          // {state, facts}
  const [n, setN] = useState(null);                 // current step number
  const [whyOpen, setWhyOpen] = useState(false);
  const sheetRef = useRef(null);
  const routedRef = useRef(null);
  const ready = !!user?.id && !user?.is_blocked && (user.language_chosen || explicitLang());

  const load = useCallback(async () => {
    try { const d = await api(''); setData(d); return d; } catch { return null; }
  }, []);

  // first load
  useEffect(() => {
    if (!ready) return;
    load().then((d) => {
      if (!d) return;
      const s = d.state || {};
      if (s.active) setN(Math.max(2, s.step || 2));
      else if (d.facts?.plan_done && !d.facts?.reward_claimed) setN(63);   // plan done after the guide → screen 63
    });
  }, [ready, load]);

  // after the guide: check now and then whether the plan got done (upgrade to level 1) → screen 63
  useEffect(() => {
    if (!ready || n || !data || data.state?.active) return undefined;
    if (data.facts?.reward_claimed) return undefined;
    const id = setInterval(async () => {
      const d = await load();
      if (d?.facts?.plan_done && !d.facts.reward_claimed) setN(63);
    }, 60000);
    return () => clearInterval(id);
  }, [ready, n, data, load]);

  const facts = useMemo(() => data?.facts || {}, [data]);
  const path = data?.state?.path || 'new';
  const step = n ? stepByN(n) : null;
  const vars = useVars(facts, lang);
  const rects = useRects(step && step.kind !== 'card' ? step : null, vars);
  const T = (k) => gt(lang, k);
  const F = (k, extra) => fill(T(k), { ...vars, ...(extra || {}) });

  const go = useCallback(async (to, extra = {}) => {
    setWhyOpen(false);
    if (to >= 64) {
      setN(null);
      try { await api('/finish', {}); } catch { /* offline: the next load continues */ }
      load();
      return;
    }
    setN(to);
    if (extra.path) setData((d) => (d ? { ...d, state: { ...(d.state || {}), path: extra.path } } : d));
    try { await api('/step', { step: to, ...extra }); } catch { /* offline */ }
  }, [load]);

  const next = useCallback(() => {
    if (!n) return;
    if (n === 9) {                                  // after the map: a player who already has a business skips 10–19
      if (facts.has_business) { go(20, { path: 'returning' }); return; }
      go(10, { path: 'new' }); return;
    }
    go(nextStep(n, facts, path));
  }, [n, facts, path, go]);

  // open the step's page once when the step starts
  useEffect(() => {
    if (!step || !step.route || routedRef.current === step.n) return;
    const route = fill(step.route, vars);
    if (/\{\w+\}/.test(route)) return;                 // facts not loaded yet
    routedRef.current = step.n;
    const [p, q] = route.split('?');
    // already there (the sell window of step 30 is open with the same query) → stay
    if (loc.pathname !== p || (q && !q.split('&').every((kv) => loc.search.includes(kv)))) navigate(route);
  }, [step, vars]); // eslint-disable-line react-hooks/exhaustive-deps

  // a step not for this player (tier 3, level 1…) is passed over
  useEffect(() => {
    if (step && step.when && data && !step.when(facts)) go(nextStep(step.n - 1, facts, path));
  }, [step, data]); // eslint-disable-line react-hooks/exhaustive-deps

  // action steps move on by themselves; facts are re-read while a step waits for one
  useEffect(() => {
    if (!step || !step.until) return undefined;
    let alive = true, lastFacts = 0;
    const tick = async () => {
      if (!alive) return;
      let f = facts;
      if (step.needFacts && Date.now() - lastFacts > 2500) { lastFacts = Date.now(); const d = await load(); if (d) f = d.facts; }
      if (alive && step.until({ path: window.location.pathname, search: window.location.search, facts: f || {} })) next();
    };
    const id = setInterval(tick, 400);
    return () => { alive = false; clearInterval(id); };
  }, [step, facts, next, load]);

  // an action whose button is not on this screen (e.g. no referral button on a computer) does not block the guide
  useEffect(() => {
    if (!step || !step.skipIfMissing) return undefined;
    const id = setTimeout(() => { if (!rects.some((r) => !r.bare)) next(); }, 6000);
    return () => clearTimeout(id);
  }, [step, rects, next]);

  // presses: only the sheet (and for action steps the framed elements) react
  useEffect(() => {
    if (!step) return undefined;
    const allowed = (t) => {
      if (sheetRef.current && sheetRef.current.contains(t)) return true;
      if (step.kind !== 'action') return false;
      return rects.some((r) => !r.bare && r.el && (r.el === t || r.el.contains(t)));
    };
    const sell30 = () => navigate(`/trading?tab=my&sell=${vars.prodId}&amount=${facts.biz?.tier === 1 ? TIER1_MIN_LOT : 1}`);
    const block = (e) => {
      if (allowed(e.target)) {
        // step 30: «Продать ресурс» opens the sell window with the player's goods and the minimum lot already filled
        if (step.n === 30 && e.type === 'click' && vars.prodId) { e.preventDefault(); e.stopPropagation(); sell30(); }
        return;
      }
      e.preventDefault(); e.stopPropagation();
      // something lies over the framed element (a toast, a hint): a press inside the frame still presses the element
      if (step.kind === 'action' && e.type === 'click' && typeof e.clientX === 'number') {
        const hit = rects.find((r) => !r.bare && r.el && e.clientX >= r.x && e.clientX <= r.x + r.w && e.clientY >= r.y && e.clientY <= r.y + r.h);
        if (hit) { if (step.n === 30 && vars.prodId) sell30(); else if (/INPUT|TEXTAREA/.test(hit.el.tagName)) hit.el.focus(); else hit.el.click(); }
      }
    };
    const evs = ['pointerdown', 'mousedown', 'click', 'dblclick', 'contextmenu'];
    evs.forEach((ev) => document.addEventListener(ev, block, true));
    return () => evs.forEach((ev) => document.removeEventListener(ev, block, true));
  }, [step, rects, vars.prodId, facts, navigate]);

  if (!ready || !n || !step || !data) return null;

  // ── cards ──
  if (step.kind === 'card') {
    return (
      <div className="gcg-root gcg-cardwrap" data-testid={`guide-card-${step.id}`}>
        <div className="gcg-dim" />
        <div ref={sheetRef} className="gcg-card" {...keep}>
          <Card step={step} T={T} F={F} vars={vars} facts={facts} path={path} lang={lang} n={n} next={next} go={go} load={load} />
        </div>
      </div>
    );
  }

  // ── overlay: dim with holes, frames, labels, sheet ──
  const VW = window.innerWidth, VH = window.innerHeight;
  const ch = chapterOf(n);
  const chName = (T('ui.chapters') || [])[ch.no] || '';
  const total = path === 'returning' ? TOTAL : TOTAL;
  const view = step.kind !== 'action';
  const textKey = (k) => {
    if (step.n === 27 && facts.biz?.tier === 3) return k === 'x' ? 'x3' : k;
    if (step.n === 31 && !facts.biz?.city_buys) return k === 'x' ? 'x2' : k;
    if (step.n === 32 && facts.biz?.tier !== 1) return k === 'x' ? 'x2' : k;
    return k;
  };
  const title = F(`${step.id}.t`);
  const text = F(`${step.id}.${textKey('x')}`);
  const why = T(`${step.id}.y`);
  const whyTitle = T(`${step.id}.w`) || T('ui.why');
  let btn = T('ui.next');
  if (step.n === 27) btn = facts.biz?.tier === 3 ? T('s27.b3') : F('s27.b', { prod: vars.prod });
  const main = rects.find((r) => !r.bare);
  const sheetPos = step.sheet || (main && main.y + main.h / 2 > VH * 0.55 ? 'top' : 'bottom');
  const dim = step.dim == null ? 0.72 : step.dim;
  let tap = null;
  if (!view && main) {
    const below = main.y + main.h + 50 < VH - 240;
    tap = { x: Math.min(VW - 120, Math.max(8, main.x + main.w / 2 - 50)), y: below ? main.y + main.h + 10 : Math.max(6, main.y - 40) };
  }
  let eye = null;
  if (view && main) eye = { x: Math.min(VW - 130, Math.max(6, main.x + main.w - 122)), y: main.y > 24 ? main.y - 11 : main.y + main.h - 11 };
  const legend = step.legend ? T(`${step.id}.legend`) : null;

  return (
    <div className="gcg-root" data-testid={`guide-step-${step.id}`} data-kind={step.kind}>
      <svg className="gcg-svg" width={VW} height={VH} aria-hidden="true">
        <defs><mask id="gcg-mask"><rect width={VW} height={VH} fill="white" />
          {rects.map((r) => <rect key={r.i} x={r.x} y={r.y} width={r.w} height={r.h} rx={r.rad} fill="black" />)}
        </mask></defs>
        <rect width={VW} height={VH} fill={`rgba(3,6,14,${dim})`} mask="url(#gcg-mask)" />
      </svg>
      {rects.filter((r) => !r.bare).map((r) => (
        <div key={r.i} className={`gcg-ring ${view ? 'view' : ''}`} style={{ left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: r.rad }} />
      ))}
      {rects.filter((r) => r.badge).map((r) => (
        <div key={`b${r.i}`} className="gcg-num" style={{ left: Math.max(4, r.x - 24), top: r.y + r.h / 2 - 11 }}>{r.badge}</div>
      ))}
      {eye && <div className="gcg-eye" style={{ left: eye.x, top: eye.y }}>{T('ui.view')}</div>}
      {tap && <div className="gcg-tap" style={{ left: tap.x, top: tap.y }}>{T('ui.tap')}</div>}
      <div ref={sheetRef} className={`gcg-sheet ${sheetPos}`} data-testid="guide-sheet" {...keep}>
        <div className="gcg-top">
          <span className="gcg-chap">{fill(T('ui.chapter'), { no: ch.no, name: chName })}</span>
          <span className={`gcg-kind k-${step.kind}`}>{(T('ui.kind') || {})[step.kind] || ''}</span>
        </div>
        <div className="gcg-bar"><i style={{ width: `${Math.round((Math.min(n, total) / total) * 100)}%` }} /></div>
        <h3 className="gcg-title" dangerouslySetInnerHTML={{ __html: title }} />
        <p className="gcg-text" dangerouslySetInnerHTML={{ __html: text }} />
        {Array.isArray(legend) && (
          <ul className="gcg-leg">{legend.map((l, i) => <li key={i}><i>{i + 1}</i><span dangerouslySetInnerHTML={{ __html: l }} /></li>)}</ul>
        )}
        {step.why && why && (
          <div className={`gcg-why ${whyOpen || step.whyOpen ? 'open' : ''}`}>
            <button type="button" className="gcg-why-h" onClick={() => setWhyOpen((v) => !v)}>{whyTitle}<span>{whyOpen || step.whyOpen ? '▴' : '▾'}</span></button>
            {(whyOpen || step.whyOpen) && <div className="gcg-why-b" dangerouslySetInnerHTML={{ __html: why }} />}
          </div>
        )}
        <div className="gcg-foot">
          <span className="gcg-prog">{fill(T('ui.step'), { n: Math.min(n, total), total })}</span>
          {view && <button type="button" className="gcg-btn" onClick={next} data-testid="guide-next">{btn}</button>}
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────────── cards ───────────────────────────── */

function Card({ step, T, F, vars, facts, path, lang, n, next, go, load }) {
  const c = step.card;
  if (c === 'welcome') return <WelcomeCard T={T} next={next} />;
  if (c === 'claimed') return <ClaimedCard T={T} F={F} vars={vars} next={next} />;
  if (c === 'batch') return <BatchCard T={T} F={F} vars={vars} facts={facts} next={next} load={load} />;
  if (c === 'citybuy') return <CityBuyCard T={T} F={F} vars={vars} facts={facts} next={next} load={load} lang={lang} />;
  if (c === 'maindone') return <MainDoneCard T={T} F={F} facts={facts} path={path} n={n} next={next} />;
  if (c === 'activity') return <ActivityCard T={T} F={F} facts={facts} next={next} />;
  if (c === 'plan') return <PlanCard T={T} F={F} facts={facts} next={next} />;
  if (c === 'reward') return <RewardCard T={T} F={F} facts={facts} lang={lang} done={() => go(64)} load={load} />;
  return null;
}

function Head({ T, n }) {
  const ch = chapterOf(n);
  return (
    <div className="gcg-top">
      <span className="gcg-chap">{fill(T('ui.chapter'), { no: ch.no, name: (T('ui.chapters') || [])[ch.no] || '' })}</span>
      <span className="gcg-prog">{fill(T('ui.step'), { n: Math.min(n, TOTAL), total: TOTAL })}</span>
    </div>
  );
}

function WelcomeCard({ T, next }) {
  const cards = T('s02.cards') || [];
  const [i, setI] = useState(0);
  const touch = useRef(null);
  const last = i >= cards.length - 1;
  const c = cards[i] || {};
  return (
    <div className="gcg-welcome" onTouchStart={(e) => { touch.current = e.touches[0].clientX; }}
      onTouchEnd={(e) => { const d = e.changedTouches[0].clientX - (touch.current || 0); if (d < -40) setI((v) => Math.min(cards.length - 1, v + 1)); if (d > 40) setI((v) => Math.max(0, v - 1)); }}>
      <div className="gcg-wicon">{c.icon}</div>
      <h3 className="gcg-title">{c.t}</h3>
      <p className="gcg-text">{c.x}</p>
      <div className="gcg-dots">{cards.map((_, k) => <button type="button" key={k} className={k === i ? 'on' : ''} onClick={() => setI(k)} aria-label={String(k + 1)} />)}</div>
      <button type="button" className="gcg-btn wide" data-testid="guide-next" onClick={() => (last ? next() : setI(i + 1))}>{last ? T('s02.b') : T('ui.next')}</button>
    </div>
  );
}

function ClaimedCard({ T, F, vars, next }) {
  return (
    <div>
      <div className="gcg-bigicon">{vars.bicon}</div>
      <h3 className="gcg-title center">{T('s13.t')}</h3>
      <p className="gcg-sub center">{vars.biz}</p>
      <div className="gcg-rows">
        <div><span>{T('s13.lease')}</span><b>{F('s13.leaseV')}</b></div>
        {vars.uses && <div><span>{T('s13.stock')}</span><b>{F('s13.stockV')}</b></div>}
        <div><span>{T('s13.makes')}</span><b>{F('s13.makesV')}</b></div>
      </div>
      <button type="button" className="gcg-btn wide" data-testid="guide-next" onClick={next}>{T('s13.b')}</button>
    </div>
  );
}

function BatchCard({ T, F, vars, facts, next, load }) {
  const tier = facts.biz?.tier || 1;
  const units = tier === 1 ? 10 : tier === 2 ? 1 : 0;
  const [left, setLeft] = useState(units ? 10 : 0);
  const [res, setRes] = useState(null);
  useEffect(() => {
    if (!units) return undefined;
    if (left <= 0) {
      api('/trial-batch', {}).then((r) => { setRes(r); load(); }).catch(() => setRes({ units: 0 }));
      return undefined;
    }
    const id = setTimeout(() => setLeft((v) => v - 1), 1000);
    return () => clearTimeout(id);
  }, [left, units]); // eslint-disable-line react-hooks/exhaustive-deps
  const done = !units || !!res;
  return (
    <div>
      <Head T={T} n={19} />
      <div className="gcg-bigicon">{vars.pi || '📦'}</div>
      <h3 className="gcg-title center">{T('s19.t')}</h3>
      {units ? (
        <>
          <p className="gcg-text center">{T('s19.x')}</p>
          <div className="gcg-meter"><i style={{ width: `${Math.round(((10 - left) / 10) * 100)}%` }} /><span>{Math.round(((10 - left) / 10) * units)} / {units}</span></div>
          {done && <p className="gcg-text center ok">{F('s19.done', { units: res?.units || units })}</p>}
          <p className="gcg-sub center">{F('s19.after')}</p>
        </>
      ) : <p className="gcg-text center">{F('s19.t3')}</p>}
      <button type="button" className="gcg-btn wide" data-testid="guide-next" disabled={!done} onClick={next}>{T('s19.b')}</button>
    </div>
  );
}

function CityBuyCard({ T, F, vars, facts, next, load, lang }) {
  const lot = facts.lot;
  const created = lot?.created_at ? new Date(lot.created_at).getTime() : Date.now();
  const [now, setNow] = useState(Date.now());
  const [sold, setSold] = useState(null);
  const [late, setLate] = useState(false);
  const left = Math.max(0, Math.ceil((created + 10000 - now) / 1000));
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(id); }, []);
  useEffect(() => {
    if (left > 0 || sold || late || !lot) return;
    let tries = 0, alive = true;
    const attempt = async () => {
      tries += 1;
      try {
        const r = await api('/first-sale', { listing_id: lot.id });
        if (!alive) return;
        if (r.sold || r.status === 'sold') { const d = await load(); setSold(d?.facts?.city_trade || { units: lot.amount }); return; }
        if (r.wait_sec) { setTimeout(attempt, r.wait_sec * 1000); return; }
      } catch { /* retry */ }
      if (tries < 3) setTimeout(attempt, 2000); else setLate(true);
    };
    attempt();
    return () => { alive = false; };
  }, [left, sold, late, lot]); // eslint-disable-line react-hooks/exhaustive-deps
  const num = (v) => Number(v || 0).toLocaleString(LOCALE[lang] || 'en-US', { maximumFractionDigits: 2 });
  if (sold) {
    return (
      <div data-testid="guide-city-bought">
        <Head T={T} n={34} />
        <div className="gcg-bigicon">🏙</div>
        <h3 className="gcg-title center">{T('s34.bought')}</h3>
        <p className="gcg-text center" dangerouslySetInnerHTML={{ __html: F('s34.boughtX', { units: sold.units, total: num(sold.total_city), got: num(sold.received_city) }) }} />
        <button type="button" className="gcg-btn wide" data-testid="guide-next" onClick={next}>{T('ui.next')}</button>
      </div>
    );
  }
  return (
    <div>
      <Head T={T} n={34} />
      <div className="gcg-bigicon">🏙</div>
      <h3 className="gcg-title center">{T('s34.t')}</h3>
      <p className="gcg-sub center">{T('s34.x')}</p>
      <p className="gcg-text center">{vars.pi} {vars.prod} · {lot?.amount || ''} {T('ui.units')}</p>
      {late ? <p className="gcg-text center">{T('s34.late')}</p>
        : <div className="gcg-count">{left}<small> {T('s34.sec')}</small></div>}
      {late && <button type="button" className="gcg-btn wide" data-testid="guide-next" onClick={next}>{T('ui.next')}</button>}
    </div>
  );
}

function MainDoneCard({ T, F, facts, path, n, next }) {
  const left = TOTAL - 38;
  const items = path === 'returning' ? [] : [
    [!!facts.has_business, F('s38.d1')], [!!facts.biz?.shift_active, T('s38.d2')],
    [!!facts.sold_once || !!facts.lot, facts.sold_once ? T('s38.d3') : T('s38.d3b')],
  ];
  return (
    <div>
      <div className="gcg-top"><span className="gcg-chap">{T('s38.head')}</span><span className="gcg-prog">38/{TOTAL}</span></div>
      <div className="gcg-bigicon">🎉</div>
      <h3 className="gcg-title center">{T('s38.t')}</h3>
      <p className="gcg-sub center">{T('s38.sub')}</p>
      {items.length > 0 && <ul className="gcg-check">{items.map(([ok, txt], i) => <li key={i} className={ok ? 'ok' : ''}><i>{ok ? '✓' : '·'}</i>{txt}</li>)}</ul>}
      <div className="gcg-gift"><b>🎁 {T('s38.gift')}</b><span>{T('s38.giftX')}</span></div>
      <button type="button" className="gcg-btn wide" data-testid="guide-next" onClick={next}>{fill(T('s38.b'), { left })}</button>
    </div>
  );
}

function ActivityCard({ T, F, facts, next }) {
  const a = facts.activity || { bought: 0, sold: 0, buy_min: 40, sell_min: 100, days: 10 };
  const Bar = ({ label, v, max }) => (
    <div className="gcg-act"><div><span>{label}</span><b>{v} / {max}</b></div><i><u style={{ width: `${Math.min(100, Math.round((v / max) * 100))}%` }} /></i></div>
  );
  return (
    <div>
      <Head T={T} n={50} />
      <h3 className="gcg-title">{T('s50.t')}</h3>
      <p className="gcg-text" dangerouslySetInnerHTML={{ __html: F('s50.x') }} />
      <Bar label={F('s50.bought')} v={a.bought} max={a.buy_min} />
      <Bar label={F('s50.sold')} v={a.sold} max={a.sell_min} />
      <p className="gcg-sub">{T('s50.note')}</p>
      <button type="button" className="gcg-btn wide" data-testid="guide-next" onClick={next}>{T('s50.b')}</button>
    </div>
  );
}

function PlanCard({ T, F, facts, next }) {
  const b = facts.biz || {};
  const items = [
    [!!facts.has_business, F('s62.i1')], [!!facts.trial_batch_done || !!b.shift_active, T('s62.i2')], [!!facts.sold_once, T('s62.i3')],
    [false, T('s62.i4'), T('s62.i4n')], [false, T('s62.i5')], [!!facts.plan_done, T('s62.i6'), F('s62.i6n')],
  ];
  const done = items.filter((x) => x[0]).length;
  return (
    <div>
      <div className="gcg-top"><span className="gcg-chap">{T('s62.head')}</span><span className="gcg-prog">{TOTAL}/{TOTAL}</span></div>
      <h3 className="gcg-title">{T('s62.t')}</h3>
      <p className="gcg-sub">{T('s62.sub')}</p>
      <ul className="gcg-check">{items.map(([ok, txt, note], i) => <li key={i} className={ok ? 'ok' : ''}><i>{ok ? '✓' : '☐'}</i>{txt}{note && <em> · {note}</em>}</li>)}</ul>
      <p className="gcg-sub">{fill(T('s62.count'), { done })}</p>
      <div className="gcg-gift locked"><b>🔒 {T('s62.lock')}</b><span>{T('s62.lockX')}</span></div>
      <button type="button" className="gcg-btn wide" data-testid="guide-next" onClick={next}>{T('s62.b')}</button>
    </div>
  );
}

function RewardCard({ T, F, facts, lang, done, load }) {
  const [items, setItems] = useState([]);
  const [pick, setPick] = useState('neuro_core');
  const [busy, setBusy] = useState(false);
  const [got, setGot] = useState(facts.reward_claimed ? 'had' : null);
  useEffect(() => { api('/rewards').then((d) => setItems(d.items || [])).catch(() => {}); }, []);
  const name = (r) => getResourceName(r, lang);
  const effect = (it) => {
    // the same effect wording as the boosters tab and the resource card
    return tResourceBuff(it.resource, 'description', lang) + ' · ' + fill(T('p01.days'), { d: it.days });
  };
  const take = async () => {
    setBusy(true);
    try { const r = await api('/reward', { choice: pick }); setGot(r.already ? 'had' : 'ok'); load(); } catch { setBusy(false); }
  };
  return (
    <div data-testid="guide-reward">
      <div className="gcg-top"><span className="gcg-chap">{T('p01.t')}</span><span className="gcg-prog">✓</span></div>
      <div className="gcg-bigicon">🏆</div>
      <h3 className="gcg-title center">{T('p01.big')}</h3>
      {got ? (
        <>
          <p className="gcg-text center ok">{got === 'had' ? T('p01.had') : fill(T('p01.got'), { name: name(pick) })}</p>
          <button type="button" className="gcg-btn wide" data-testid="guide-next" onClick={done}>{T('p01.b2')}</button>
        </>
      ) : (
        <>
          <p className="gcg-sub center">{T('p01.pick')}</p>
          <div className="gcg-rewards">
            {items.map((it) => (
              <button type="button" key={it.resource} className={pick === it.resource ? 'on' : ''} onClick={() => setPick(it.resource)} data-testid={`guide-reward-${it.resource}`}>
                <span className="ri">{getResource(it.resource, lang)?.icon || it.icon}</span>
                <span className="rt"><b>{name(it.resource)}</b><small>{effect(it)}</small></span>
                {pick === it.resource && <span className="rk">✓</span>}
              </button>
            ))}
          </div>
          <p className="gcg-sub">{T('p01.note')}</p>
          <button type="button" className="gcg-btn wide" data-testid="guide-reward-take" disabled={busy} onClick={take}>{fill(T('p01.b'), { name: name(pick) })}</button>
        </>
      )}
    </div>
  );
}

export { STEPS };
