/**
 * «Блэкаут острова» — the page of the event (/blackout).
 * The centre of it is the night skyline: one tower per district, its windows light up one by one as the players
 * give resources; a lit tower carries the names of its top suppliers. Under it — what the chosen district needs,
 * how much the player has, and «Сдать». Live: leaders, the grid feed, the countdown.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { ChevronLeft, Zap, Crown, Radio, Info } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { getResource } from '@/lib/resourceConfig';
import { bt, dName } from '@/components/blackout/blackoutI18n';
import { useBlackout, refreshBlackout, setBlackoutState, serverNow, fmtLeft, useTick } from '@/components/blackout/useBlackout';
import Fireworks from '@/components/blackout/Fireworks';
import '@/components/blackout/blackout.css';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const FLOORS = { 1: 13, 2: 10, 3: 9, 4: 11 };
const COLS = 4;
const ORDER = [3, 2, 1, 4];               // left → right on the skyline: the Core in the middle-right, tallest

function seeded(n, seed) {               // a stable shuffled order of the windows of one tower
  const a = [...Array(n).keys()];
  let x = seed * 9301 + 49297;
  for (let i = n - 1; i > 0; i--) { x = (x * 9301 + 49297) % 233280; const j = Math.floor((x / 233280) * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

function Tower({ d, info, tower, selected, onPick, lang, flash }) {
  const floors = FLOORS[d] || 10, n = floors * COLS;
  const order = useMemo(() => seeded(n, d * 7 + 3), [n, d]);
  const pct = info ? info.pct : 100;
  const isLit = !info || !!info.lit_at;
  const on = isLit ? n : Math.round((pct / 100) * n);
  const litSet = useMemo(() => new Set(order.slice(0, on)), [order, on]);
  const names = (info?.lit_at ? (info.heroes || []).map((h) => h.username) : tower?.names) || [];
  return (
    <button type="button" onClick={() => onPick(d)} data-testid={`bo-tower-${d}`}
      className={`bo-tower ${isLit ? 'is-lit' : ''} ${selected ? 'is-sel' : ''} ${flash ? 'is-flash' : ''}`} aria-pressed={selected}>
      <div className="bo-names">{names.slice(0, 3).map((nm, i) => <span key={i} className={i === 0 ? 'first' : ''}>{i === 0 ? '👑 ' : ''}@{nm}</span>)}</div>
      <div className="bo-mast" />
      <div className="bo-body" style={{ gridTemplateColumns: `repeat(${COLS}, 1fr)` }}>
        {Array.from({ length: n }, (_, i) => <i key={i} className={litSet.has(i) ? 'on' : ''} style={{ animationDelay: `${(i % 7) * 0.37}s` }} />)}
      </div>
    </button>
  );
}

function Need({ res, need, got, have, lang, onGive, busy, disabled }) {
  const r = getResource(res, lang) || {};
  const left = Math.max(0, need - got);
  const pct = need ? Math.min(100, (got / need) * 100) : 100;
  const max = Math.min(left, have);
  const step = r.tier === 1 || !r.tier ? [10, 50] : [1, 5];
  return (
    <div className="bo-need" data-testid={`bo-need-${res}`}>
      <div className="bo-need-top">
        <span className="ico">{r.icon || '📦'}</span>
        <span className="nm">{r.name || res}</span>
        <span className="cnt"><b>{got.toLocaleString()}</b> / {need.toLocaleString()}</span>
      </div>
      <div className="bo-bar"><div style={{ width: `${pct}%` }} /></div>
      {left > 0 ? (
        <div className="bo-need-act">
          <span className="have">{bt(lang, 'have')}: <b>{have.toLocaleString()}</b></span>
          {max > 0 ? (
            <div className="btns">
              {step.filter((q) => q < max).map((q) => (
                <button key={q} type="button" disabled={busy || disabled} onClick={() => onGive(res, q)}>+{q}</button>
              ))}
              <button type="button" className="all" disabled={busy || disabled} onClick={() => onGive(res, max)} data-testid={`bo-give-all-${res}`}>
                <Zap className="w-3.5 h-3.5" />{bt(lang, 'give')} {max.toLocaleString()}
              </button>
            </div>
          ) : <span className="none">{bt(lang, 'noRes')}</span>}
        </div>
      ) : <div className="bo-need-ok">✓ {bt(lang, 'filled')}</div>}
    </div>
  );
}

// «1 участник / 2 участника / 5 участников»
function plural(lang, n) {
  if (lang === 'ru') {
    const f = new Intl.PluralRules('ru-RU').select(n);
    return `${n} ${f === 'one' ? 'участник' : f === 'few' ? 'участника' : 'участников'}`;
  }
  return `${n} ${bt(lang, 'participants')}`;
}

export default function BlackoutPage({ user, refreshBalance }) {
  const navigate = useNavigate();
  const { language: lang } = useLanguage();
  const bo = useBlackout(user, { fast: true });
  const ev = bo?.active || null;
  const shown = ev || bo?.last || null;
  useTick(!!ev);
  const [sel, setSel] = useState(null);
  const [busy, setBusy] = useState(false);
  const [boom, setBoom] = useState(null);           // {d, at}: fireworks over a tower
  const [rulesOpen, setRulesOpen] = useState(false);
  const prevLit = useRef({});

  // choose a district: the first still dark one
  useEffect(() => {
    if (!ev || sel) return;
    const isDark = (d) => ev.districts[String(d)] && !ev.districts[String(d)].lit_at;
    const mine = (bo?.my_districts || []).find(isDark);   // the player's own district first
    setSel(mine || ORDER.find(isDark) || 1);
  }, [ev, sel, bo?.my_districts]);

  // a district lit (by anyone): fireworks + toast
  useEffect(() => {
    if (!ev) return;
    Object.entries(ev.districts).forEach(([d, x]) => {
      if (x.lit_at && prevLit.current[d] === false) {
        setBoom({ d: Number(d), at: Date.now() });
        toast.success(bt(lang, 'litToast', { d: dName(lang, d) }));
        try { window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success'); } catch (e) { /* not in Telegram */ }
      }
      prevLit.current[d] = !!x.lit_at;
    });
  }, [ev, lang]);

  const give = async (res, qty) => {
    if (!ev || !sel) return;
    setBusy(true);
    try {
      const r = await axios.post(`${API}/blackout/contribute`, { district: sel, resource: res, qty },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token') || localStorage.getItem('ton_city_token')}` } });
      if (r.data?.state) setBlackoutState(r.data.state);
      const name = getResource(res, lang)?.name || res;
      toast.success(bt(lang, 'gave', { qty: r.data.qty, res: name, d: dName(lang, sel) }));
      try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('medium'); } catch (e) { /* not in Telegram */ }
      if (r.data?.lit && refreshBalance) setTimeout(refreshBalance, 1500);
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error((d && (d.message || d)) || 'Error');
      refreshBlackout();
    }
    setBusy(false);
  };

  const left = ev ? new Date(ev.ends_at).getTime() - serverNow() : 0;
  const sd = ev && sel ? ev.districts[String(sel)] : null;
  const st = (shown && shown.settings) || {};
  const me = bo?.me;
  const won = shown && !ev && Object.values(shown.districts || {}).every((x) => x.lit_at);
  // the race for a tower is per district: the leaders of the chosen one (the island total when calm)
  const boardFor = ev && sel ? ((bo?.board_by_district || {})[String(sel)] || []) : (bo?.board || []);

  return (
    <div className={`bo-page ${ev ? 'is-dark' : 'is-calm'}`} data-testid="blackout-page">
      <div className="bo-wrap tg-header-pad">
        <div className="bo-head">
          <button type="button" className="bo-back" onClick={() => navigate(-1)} aria-label="back"><ChevronLeft className="w-5 h-5" /></button>
          <div>
            <div className="bo-kick">{ev ? <><Radio className="w-3.5 h-3.5" />{bt(lang, 'live')}</> : bt(lang, 'calm')}</div>
            <h1>{bt(lang, 'title')}</h1>
          </div>
          {ev && (
            <div className="bo-clock" data-testid="bo-clock">
              <b>{fmtLeft(left)}</b><span>{bt(lang, 'left')}</span>
            </div>
          )}
        </div>

        {ev && (
          <div className="bo-island" data-testid="bo-island">
            <span>{bt(lang, 'island')}</span>
            <div className="bo-bar big"><div style={{ width: `${ev.pct}%` }} /></div>
            <b>{Math.floor(ev.pct)}%</b>
            <em>{plural(lang, ev.participants)}</em>
          </div>
        )}

        <div className="bo-sky" data-testid="bo-sky">
          <div className="bo-stars" />
          {ORDER.map((d) => (
            <Tower key={d} d={d} lang={lang} info={shown ? shown.districts[String(d)] : null} tower={bo?.towers?.[String(d)]}
              selected={!!ev && sel === d} onPick={(x) => ev && setSel(x)} flash={boom && boom.d === d && Date.now() - boom.at < 4000} />
          ))}
          <div className="bo-ground" />
          {boom && <Fireworks key={boom.at} index={ORDER.indexOf(boom.d)} of={ORDER.length} />}
        </div>
        <div className="bo-caps">
          {ORDER.map((d) => {
            const x = shown ? shown.districts[String(d)] : null;
            const isLit = !x || !!x.lit_at;
            return (
              <button type="button" key={d} className={`bo-cap ${isLit ? 'is-lit' : ''} ${ev && sel === d ? 'is-sel' : ''}`} onClick={() => ev && setSel(d)}>
                <b>{dName(lang, d)}</b>
                <span>{isLit ? `✨ ${bt(lang, 'lit')}` : `${Math.floor(x.pct)}%`}</span>
                {(bo?.my_districts || []).includes(d) && <i className="mine">🏠 {bt(lang, 'myDistrict')}</i>}
              </button>
            );
          })}
        </div>

        {ev && <p className="bo-sub">{bt(lang, 'subtitle')}</p>}

        {ev && sd && (
          <section className="bo-card" data-testid="bo-district">
            <div className="bo-card-h">
              <h2>{dName(lang, sel)}</h2>
              <span className={sd.lit_at ? 'ok' : ''}>{sd.lit_at ? `✨ ${bt(lang, 'lit')}` : `${Math.floor(sd.pct)}%`}</span>
            </div>
            {sd.lit_at ? (
              <div className="bo-litbox">
                <Crown className="w-5 h-5" />
                <div>{bt(lang, 'heroes')}: {(sd.heroes || []).map((h) => `@${h.username}`).join(' · ') || '—'}</div>
              </div>
            ) : (
              <>
                <div className="bo-label">{bt(lang, 'need')}</div>
                {Object.keys(sd.need).map((r) => (
                  <Need key={r} res={r} need={sd.need[r]} got={sd.got[r] || 0} have={(me?.have || {})[r] || 0} lang={lang}
                    onGive={give} busy={busy} disabled={left <= 0} />
                ))}
                <button type="button" className="bo-link" onClick={() => navigate('/trading')}>{bt(lang, 'buy')} →</button>
              </>
            )}
          </section>
        )}

        {!ev && (
          <section className="bo-card bo-calm" data-testid="bo-calm">
            <p>{bt(lang, 'calmText')}</p>
            {bo?.next_at && <p className="muted">{bt(lang, 'next', { when: new Date(bo.next_at).toLocaleDateString(lang, { day: 'numeric', month: 'long' }) })}</p>}
            {shown && <p className="muted">{won ? bt(lang, 'lastWon') : bt(lang, 'lastLost')}</p>}
            {bo?.multipliers && Object.keys(bo.multipliers).length > 0 && (
              <div className="bo-mults">
                {Object.entries(bo.multipliers).map(([d, m]) => (
                  <span key={d} className={m > 1 ? 'up' : 'down'}>{dName(lang, d)}: {m > 1 ? bt(lang, 'bonusNow', { pct: Math.round((m - 1) * 100) }) : bt(lang, 'darkNow', { pct: Math.round((1 - m) * 100) })}</span>
                ))}
              </div>
            )}
          </section>
        )}

        {me && me.points > 0 && (
          <section className="bo-card bo-me" data-testid="bo-me">
            <div className="bo-label">{bt(lang, 'mine')}{sel && ev ? ` · ${dName(lang, sel)}: ${Math.round((me.by_district || {})[String(sel)] || 0).toLocaleString()} $CITY` : ''}</div>
            <div className="row"><b>{me.units.toLocaleString()}</b> <span>· {Math.round(me.points).toLocaleString()} $CITY</span>
              {(me.reward > 0 || me.refund > 0) && <em>{bt(lang, 'earned')}: +{(me.reward + me.refund).toLocaleString(undefined, { maximumFractionDigits: 2 })} $CITY{me.xp ? ` · +${me.xp} XP` : ''}</em>}
            </div>
          </section>
        )}

        {shown && (
          <div className="bo-two">
            <section className="bo-card">
              <div className="bo-label"><Crown className="w-3.5 h-3.5" />{bt(lang, 'leaders')}{sel && ev ? ` · ${dName(lang, sel)}` : ''}</div>
              {(boardFor || []).length ? (
                <ol className="bo-board" data-testid="bo-board">
                  {boardFor.map((p, i) => (
                    <li key={i} className={p.me ? 'me' : ''}><span>{i + 1}</span><b>@{p.username}{p.me ? ` · ${bt(lang, 'you')}` : ''}</b><em>{Math.round(p.points).toLocaleString()}</em></li>
                  ))}
                </ol>
              ) : <p className="muted">{bt(lang, 'nobody')}</p>}
            </section>
            <section className="bo-card">
              <div className="bo-label"><Radio className="w-3.5 h-3.5" />{bt(lang, 'feed')}</div>
              <ul className="bo-feed" data-testid="bo-feed">
                {(bo?.feed || []).slice(0, 12).map((f, i) => {
                  const r = getResource(f.resource, lang) || {};
                  return <li key={`${f.at}-${i}`}><b>@{f.username}</b> +{f.qty} {r.icon} <span>→ {dName(lang, f.district)}</span></li>;
                })}
              </ul>
            </section>
          </div>
        )}

        {shown && (
          <section className="bo-card">
            <button type="button" className="bo-rules-t" onClick={() => setRulesOpen((x) => !x)}><Info className="w-4 h-4" />{bt(lang, 'rules')}</button>
            {rulesOpen && (
              <div className="bo-rules">
                <p>{bt(lang, 'reward', { reward: st.reward_pct ?? 120 })}</p>
                <p>{bt(lang, 'risk', { days: st.fail_days ?? 7, pct: st.fail_penalty_pct ?? 10, refund: st.refund_pct ?? 60, bonus: st.lit_bonus_pct ?? 5, bdays: st.lit_bonus_days ?? 3 })}</p>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
