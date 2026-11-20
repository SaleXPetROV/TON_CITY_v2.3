/**
 * «План на 3 дня» on the «Задания» page (owner, 17 Nov 2026): the 5 goals a newcomer does in his first days, a 3-day
 * timer and the reward — one tier-3 resource of his choice (unsellable, its buff is switched on in «Склад →
 * Усилители»). Done in time → the reward can be taken; the timer ran out → the block is gone and gives nothing.
 * Server: GET /api/guide/plan, POST /api/guide/plan/claim (routes/guide.py).
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getResource, getResourceName } from '@/lib/resourceConfig';
import { tResourceBuff } from '@/lib/translationsExtra';
import { useUiText } from '@/lib/uiI18n';
import L from '@/i18n/earn.json';
import { gt, fill } from './guideI18n';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/guide`;
const LINK = { business: '/ton-island', shift: '/my-businesses', sale: '/trading?tab=spot', repair: '/my-businesses', upgrade: '/my-businesses' };
const ICON = { business: '🏭', shift: '⏱', sale: '💱', repair: '🔧', upgrade: '⬆️' };

async function api(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}`, ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || String(r.status));
  return d;
}

export default function PlanBlock({ lang = 'ru', onClaimed }) {
  const T = useUiText('earn', lang, L);
  const G = (k) => gt(lang, k);
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [items, setItems] = useState([]);
  const [pick, setPick] = useState('neuro_core');
  const [busy, setBusy] = useState(false);
  const [got, setGot] = useState(null);

  const load = useCallback(() => api('/plan').then(setP).catch(() => {}), []);
  useEffect(() => { load(); const id = setInterval(load, 60000); return () => clearInterval(id); }, [load]);
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(id); }, []);
  useEffect(() => { if (p?.can_claim) api('/rewards').then((d) => setItems(d.items || [])).catch(() => {}); }, [p?.can_claim]);

  if (got) {
    return (
      <div className="rounded-2xl border border-emerald-400/40 bg-emerald-500/10 p-4 mb-4" data-testid="plan-got">
        <div className="font-bold text-emerald-300">🏆 {fill(G('p01.got'), { name: getResourceName(got, lang) })}</div>
      </div>
    );
  }
  if (!p || !p.show) return null;
  const ends = new Date(p.ends_at).getTime();
  const left = Math.max(0, ends - now);
  const d = Math.floor(left / 86400000), h = Math.floor((left % 86400000) / 3600000), m = Math.floor((left % 3600000) / 60000);
  const leftTxt = d > 0 ? fill(T.plan_d, { d, h }) : fill(T.plan_h, { h, m });
  const take = async () => {
    setBusy(true);
    try { await api('/plan/claim', { choice: pick }); setGot(pick); if (onClaimed) onClaimed(); } catch { load(); } finally { setBusy(false); }
  };
  return (
    <div className="rounded-2xl border border-cyan-400/35 bg-gradient-to-b from-cyan-500/10 to-transparent p-4 mb-4" data-testid="plan-block">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-unbounded font-bold text-white text-base">{T.plan_t}</div>
          <div className="text-xs text-white/60 mt-1 max-w-md">{T.plan_sub}</div>
        </div>
        {!p.in_time && (
          <div className="shrink-0 rounded-xl border border-amber-400/40 bg-amber-500/10 px-2.5 py-1.5 text-amber-200 font-bold text-sm tabular-nums" data-testid="plan-timer">
            ⏳ {fill(T.plan_left, { t: leftTxt })}
          </div>
        )}
      </div>
      <div className="mt-3 h-1.5 rounded-full bg-white/10 overflow-hidden"><i className="block h-full bg-cyan-400" style={{ width: `${(p.done / p.items.length) * 100}%` }} /></div>
      <div className="text-[11px] text-white/50 mt-1">{fill(T.plan_count, { d: p.done, t: p.items.length })}</div>
      <ul className="mt-2 space-y-1.5">
        {p.items.map((it) => (
          <li key={it.id} className={`flex items-center gap-2 rounded-xl px-3 py-2 ${it.done ? 'bg-emerald-500/10 text-emerald-200' : 'bg-white/[0.04] text-white/85'}`} data-testid={`plan-item-${it.id}`}>
            <span className="w-5 text-center">{it.done ? '✓' : ICON[it.id]}</span>
            <span className="flex-1 text-sm font-semibold">{T[`plan_${it.id}`]}</span>
            {!it.done && !p.in_time && (
              <button type="button" onClick={() => navigate(LINK[it.id])} className="text-xs font-bold text-cyan-300 px-2 py-1 rounded-lg border border-cyan-400/30">{T.plan_go}</button>
            )}
          </li>
        ))}
      </ul>
      {p.can_claim ? (
        <div className="mt-3" data-testid="plan-reward">
          <div className="text-sm font-bold text-emerald-300 mb-2">{T.plan_done}</div>
          <div className="grid gap-1.5">
            {items.map((it) => (
              <button type="button" key={it.resource} onClick={() => setPick(it.resource)} data-testid={`plan-reward-${it.resource}`}
                className={`flex items-center gap-2 text-left rounded-xl px-3 py-2 border ${pick === it.resource ? 'border-emerald-400/70 bg-emerald-500/10' : 'border-white/10 bg-white/[0.03]'}`}>
                <span className="text-xl">{getResource(it.resource, lang)?.icon || it.icon}</span>
                <span className="flex-1 min-w-0"><b className="block text-sm text-white">{getResourceName(it.resource, lang)}</b>
                  <small className="block text-[11px] text-white/55">{tResourceBuff(it.resource, 'description', lang)} · {fill(G('p01.days'), { d: it.days })}</small></span>
                {pick === it.resource && <span className="text-emerald-300">✓</span>}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-white/45 mt-2">{G('p01.note')}</p>
          <button type="button" disabled={busy} onClick={take} data-testid="plan-take"
            className="mt-2 w-full rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-bold py-2.5 disabled:opacity-50">{T.plan_take}</button>
        </div>
      ) : null}
    </div>
  );
}
