/**
 * «Как заработать в GRAM City» — the guide since 17 Nov 2026 (owner): one window of 9 illustrated steps that opens by
 * itself the first time a player enters the game (and again after «Пройти гид заново», or from the «?» of any page).
 * Nothing is clicked for the player: each step says what to do and offers a button to the right page.
 * Texts: src/i18n/earn.json (the server's LibreTranslate text wins for every language but Russian, backend/ui_i18n.py).
 * Pictures: the game's own business, resource and truck sprites (public/sprites).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUiText } from '@/lib/uiI18n';
import L from '@/i18n/earn.json';
import './earn.css';

const SP = '/sprites';
const f = (s, v) => Object.entries(v || {}).reduce((a, [k, x]) => a.split(`{${k}}`).join(String(x)), String(s || ''));

// step → the page its button opens (step 1 and 9 have none: 1 is the overview, 9 closes the window)
const CTA = { 2: '/ton-island', 3: '/my-businesses', 4: '/resources', 5: '/trading?tab=spot', 6: '/trading?tab=operations', 7: '/my-businesses', 8: '/tasks' };
const N = 9;

function Coin() {
  return <span className="ei-coin" aria-hidden="true">$</span>;
}

/** The picture of a step: the game's own sprites, arranged per step. */
function Art({ n, T }) {
  switch (n) {
    case 1: return (
      <div className="ei-loop">
        <img src={`${SP}/city/bio_farm/stage2.webp`} alt="" className="ei-b" />
        <span className="ei-arrow">→</span>
        <img src={`${SP}/resources/biomass.webp`} alt="" className="ei-r" />
        <span className="ei-arrow">→</span>
        <Coin />
      </div>
    );
    case 2: return (
      <div className="ei-plot">
        <div className="ei-tile" />
        <img src={`${SP}/city/bio_farm/stage1.webp`} alt="" className="ei-b big" />
        <span className="ei-chip cyan">{T.i_free}</span>
      </div>
    );
    case 3: return (
      <div className="ei-shift">
        <svg viewBox="0 0 120 120" className="ei-ring" aria-hidden="true">
          <circle cx="60" cy="60" r="54" className="bg" /><circle cx="60" cy="60" r="54" className="fg" />
        </svg>
        <img src={`${SP}/city/quartz_mine/stage3.webp`} alt="" className="ei-b" />
        <span className="ei-chip green">⏱ {T.i_shift}</span>
      </div>
    );
    case 4: return (
      <div className="ei-store">
        <div className="ei-grid">
          {['quartz', 'energy', 'biomass', 'chips', 'cooling', 'traffic'].map((r) => (
            <span key={r} className="ei-cell"><img src={`${SP}/resources/${r}.webp`} alt="" /></span>
          ))}
        </div>
        <div className="ei-cap"><i /><span>{T.i_store} 72%</span></div>
      </div>
    );
    case 5: return (
      <div className="ei-book" aria-hidden="true">
        {[['3.30', '4.5K', 90], ['3.20', '820', 40], ['3.05', '310', 22]].map(([p, a, w]) => (
          <div key={p} className="row ask"><i style={{ width: `${w}%` }} /><b>{p}</b><span>{a}</span></div>
        ))}
        <div className="mid">2.98</div>
        {[['2.95', '1.2K', 60, false], ['2.80', '2.0K', 100, true], ['2.60', '140', 18, false]].map(([p, a, w, c]) => (
          <div key={p} className={`row bid ${c ? 'city' : ''}`}><i style={{ width: `${w}%` }} /><b>{p}</b><span>{a}</span>{c && <em>{T.i_city}</em>}</div>
        ))}
      </div>
    );
    case 6: return (
      <div className="ei-route">
        <img src={`${SP}/city/logistics_hub/stage2.webp`} alt="" className="ei-b sm l" />
        <svg viewBox="0 0 200 40" className="ei-dash" aria-hidden="true"><path d="M5 30 Q100 -10 195 30" /></svg>
        <img src={`${SP}/trucks/truck_dr.webp`} alt="" className="ei-truck" />
        <img src={`${SP}/city/chips_factory/stage2.webp`} alt="" className="ei-b sm r" />
      </div>
    );
    case 7: return (
      <div className="ei-up">
        <img src={`${SP}/city/chips_factory/stage1.webp`} alt="" className="ei-b sm dim" />
        <span className="ei-arrow">→</span>
        <img src={`${SP}/city/chips_factory/stage3.webp`} alt="" className="ei-b" />
        <div className="ei-chips"><span className="ei-chip cyan">{T.i_lvl}</span><span className="ei-chip green">📈 {T.i_pay}</span></div>
      </div>
    );
    case 8: return (
      <div className="ei-free">
        {[['🎁', T.i_daily], ['🎯', T.i_goals], ['⭐', T.i_pass]].map(([e, t]) => <span key={t} className="ei-gift"><b>{e}</b>{t}</span>)}
        <span className="ei-gift gold"><img src={`${SP}/resources/gold_bill.webp`} alt="" />{T.i_plan}</span>
      </div>
    );
    default: return (
      <div className="ei-bank">
        <img src={`${SP}/city/gram_bank/stage3.webp`} alt="" className="ei-b wide" />
        <div className="ei-chips col"><span className="ei-chip cyan">↗ {T.i_main}</span><span className="ei-chip yellow">🎮 {T.i_bonus}</span></div>
      </div>
    );
  }
}

export default function EarnIntro({ lang, onClose }) {
  const T = useUiText('earn', lang, L);
  const navigate = useNavigate();
  const [n, setN] = useState(1);
  const touch = useRef(null);
  const close = useCallback((to) => { onClose(); if (to) navigate(to); }, [onClose, navigate]);
  const go = useCallback((k) => setN((v) => Math.min(N, Math.max(1, v + k))), []);

  useEffect(() => {
    const key = (e) => {
      if (e.key === 'ArrowRight') go(1);
      else if (e.key === 'ArrowLeft') go(-1);
      else if (e.key === 'Escape') close();
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  }, [go, close]);
  // the pictures of all steps load once, so a step never opens empty
  useEffect(() => {
    ['bio_farm/stage1', 'quartz_mine/stage3', 'chips_factory/stage1', 'chips_factory/stage3', 'gram_bank/stage3', 'logistics_hub/stage2']
      .forEach((p) => { const i = new Image(); i.src = `${SP}/city/${p}.webp`; });
  }, []);

  const last = n === N;
  return (
    <div className="ei-root" data-testid="earn-intro">
      <div className="ei-bg" onClick={() => close()} />
      <div className="ei-card" role="dialog" aria-modal="true" aria-label={T.head}
        onTouchStart={(e) => { touch.current = e.touches[0].clientX; }}
        onTouchEnd={(e) => {
          if (touch.current == null) return;
          const dx = e.changedTouches[0].clientX - touch.current;
          touch.current = null;
          if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
        }}>
        <div className="ei-top">
          <span>{T.head}</span>
          <button type="button" onClick={() => close()} aria-label={T.close} data-testid="earn-close">✕</button>
        </div>
        <div className={`ei-stage s${n}`} key={n}>
          <span className="ei-num" aria-hidden="true">{n}</span>
          <Art n={n} T={T} />
        </div>
        <div className="ei-body" key={`b${n}`}>
          <div className="ei-step">{f(T.step, { n, t: N })}</div>
          <h2 className="ei-title" data-testid="earn-title">{T[`t${n}`]}</h2>
          <p className="ei-text">{T[`x${n}`]}</p>
          {CTA[n] && (
            <button type="button" className="ei-cta" onClick={() => close(CTA[n])} data-testid={`earn-cta-${n}`}>{T[`c${n}`]}</button>
          )}
        </div>
        <div className="ei-foot">
          <div className="ei-dots" role="tablist">
            {Array.from({ length: N }).map((_, i) => (
              <button type="button" key={i} role="tab" aria-selected={i + 1 === n} aria-label={f(T.step, { n: i + 1, t: N })}
                className={i + 1 === n ? 'on' : i + 1 < n ? 'done' : ''} onClick={() => setN(i + 1)} />
            ))}
          </div>
          <div className="ei-btns">
            {n > 1 ? <button type="button" className="ei-btn ghost" onClick={() => go(-1)} data-testid="earn-back">{T.back}</button>
              : <button type="button" className="ei-btn ghost" onClick={() => close()} data-testid="earn-skip">{T.skip}</button>}
            <button type="button" className="ei-btn" onClick={() => (last ? close() : go(1))} data-testid="earn-next">{last ? T.start : T.next}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
