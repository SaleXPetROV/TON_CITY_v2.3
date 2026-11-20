/** Торговля → спот: a resource's order book like a crypto exchange's spot screen.
 *  Left (60%): Buy / Sell, what is available (+ top-up on Buy), Market / Limit, price, amount, order value (all three
 *  recount each other as you type), max buy / sell (money, warehouse room, stock), the button.
 *  Right (40%): the book — asks (red) above, the mid price in the middle (tap → the full order book), bids (green)
 *  below, the buy / sell share. Below: my open orders (buy and sell) with «Отменить»; the button next to them opens
 *  «История операций» with the «Торговля» filter on (purchases and sales).
 *  Server: backend/spot_market.py (/api/market/order, /cancel, /book/{res}, /my-orders/{id}, /my-trades, /spot-info). */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowRight, ChevronDown, History, PlusCircle, Search } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { DepositModal } from '@/components/BalanceModals';
import { getAllResources, getResource } from '@/lib/resourceConfig';
import { useUiText } from '@/lib/uiI18n';
import SPOT from '@/i18n/spot.json';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const STEPS = ['0.01', '0.1', '1', '10'];
const ROWS = 6;

const f = (s, v) => Object.entries(v || {}).reduce((a, [k, x]) => a.split(`{${k}}`).join(String(x)), s || '');
const kfmt = (n) => {
  const v = Number(n) || 0;
  if (v >= 1e6) return `${(v / 1e6).toFixed(v >= 1e7 ? 1 : 2)}M`;
  if (v >= 1e4) return `${(v / 1e3).toFixed(1)}K`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(2)}K`;
  return String(Math.round(v));
};
const money = (v) => (Number(v) || 0).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).replace(/ /g, ' ');
const toCents = (s) => { const n = Number(String(s).replace(',', '.')); return Number.isFinite(n) ? Math.round(n * 100) : NaN; };
const centsStr = (c) => (c / 100).toFixed(2);
const cleanNum = (s, dec) => {
  let x = String(s).replace(',', '.').replace(dec ? /[^0-9.]/g : /[^0-9]/g, '');
  if (dec) { const p = x.split('.'); x = p[0] + (p.length > 1 ? `.${p.slice(1).join('').slice(0, 2)}` : ''); }
  return x.replace(/^0+(?=\d)/, '');
};

/** walk the book: how many units `budget` (cents) / `room` buys, or what selling `units` brings */
function walk(levels, { units = Infinity, budgetC = Infinity }) {
  let u = 0; let c = 0;
  for (const l of levels) {
    const p = l.price_cents;
    let take = Math.min(l.amount, units - u);
    if (budgetC !== Infinity) take = Math.min(take, Math.floor((budgetC - c) / p));
    if (take <= 0) break;
    u += take; c += take * p;
    if (u >= units) break;
  }
  return { units: u, cents: c };
}

function ago(iso, T) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${Math.floor(s)} ${T.secShort}`;
  if (s < 3600) return `${Math.floor(s / 60)} ${T.minShort}`;
  if (s < 86400) return `${Math.floor(s / 3600)} ${T.hShort}`;
  return `${Math.floor(s / 86400)} ${T.dShort}`;
}

/** A drop-down list drawn by the page itself, not the system <select>: inside the Telegram app on Android the system
 *  list did not open in the scrolled part of «Торговля». `up` opens it above the button (near the bottom of the book). */
function MiniSelect({ value, options, onChange, className = '', wrapClass = '', testid, label, up = false }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const away = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('pointerdown', away);
    return () => document.removeEventListener('pointerdown', away);
  }, [open]);
  const cur = options.find((o) => o.value === value) || options[0];
  return (
    <div ref={ref} className={`relative ${wrapClass}`}>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-haspopup="listbox" aria-expanded={open} aria-label={label}
        data-testid={testid} data-value={value} className={`flex items-center justify-between gap-2 text-left ${className}`}>
        <span className="truncate">{cur?.label}</span>
        <ChevronDown className={`w-4 h-4 shrink-0 opacity-70 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div role="listbox" className={`absolute z-40 left-0 right-0 ${up ? 'bottom-full mb-1' : 'top-full mt-1'} rounded-lg border border-white/15 bg-[#11131c] shadow-xl overflow-hidden`}>
          {options.map((o) => (
            <button type="button" role="option" aria-selected={o.value === value} key={o.value} data-testid={`${testid}-opt-${o.value}`}
              onClick={() => { onChange(o.value); setOpen(false); }}
              className={`block w-full text-left px-3 py-2 text-sm ${o.value === value ? 'bg-white/10 text-white font-semibold' : 'text-white/80 active:bg-white/10'}`}>
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SpotTrading({ lang = 'ru', user, initial = {}, onBalanceChanged }) {
  const T = useUiText('spot', lang, SPOT);
  const navigate = useNavigate();
  const all = useMemo(() => getAllResources().filter((r) => !String(r.id).endsWith('_tutorial')), []);
  const [res, setRes] = useState(() => {
    if (initial.res && all.some((r) => r.id === initial.res)) return initial.res;
    try { const v = localStorage.getItem('spot_res'); if (v && all.some((r) => r.id === v)) return v; } catch (e) { /* no storage */ }
    return all.find((r) => r.id === 'quartz') ? 'quartz' : all[0]?.id;
  });
  const [side, setSide] = useState(initial.side === 'sell' ? 'sell' : 'buy');
  const [otype, setOtype] = useState('limit');
  const [price, setPrice] = useState('');
  const [amount, setAmount] = useState(initial.amount ? String(parseInt(initial.amount, 10) || '') : '');
  const [volume, setVolume] = useState('');
  const lastEdit = useRef('amount');
  const [step, setStep] = useState('0.01');
  const [bk, setBk] = useState(null);
  const [info, setInfo] = useState(null);
  const [orders, setOrders] = useState([]);
  const [busy, setBusy] = useState(false);
  const [picker, setPicker] = useState(false);
  const [q, setQ] = useState('');
  const [fullBook, setFullBook] = useState(false);
  const [deposit, setDeposit] = useState(false);
  const [depAddr, setDepAddr] = useState('');
  const priceSet = useRef(false);
  const R = getResource(res, lang);
  const tk = () => localStorage.getItem('token');
  const H = () => ({ Authorization: `Bearer ${tk()}`, 'Content-Type': 'application/json' });

  const loadBook = useCallback(async () => {
    if (!res) return;
    try {
      const r = await fetch(`${API}/market/book/${res}?step=${step}&depth=30`);
      if (r.ok) setBk(await r.json());
    } catch (e) { /* offline */ }
  }, [res, step]);
  const loadInfo = useCallback(async () => {
    if (!res || !tk()) return;
    try { const r = await fetch(`${API}/market/spot-info/${res}`, { headers: H() }); if (r.ok) setInfo(await r.json()); } catch (e) { /* offline */ }
  }, [res]); // eslint-disable-line react-hooks/exhaustive-deps
  const loadOrders = useCallback(async () => {
    if (!tk()) return;
    try { const r = await fetch(`${API}/market/my-orders/me`, { headers: H() }); if (r.ok) setOrders((await r.json()).orders || []); } catch (e) { /* offline */ }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { try { localStorage.setItem('spot_res', res); } catch (e) { /* no storage */ } priceSet.current = false; setPrice(''); setVolume(''); loadInfo(); }, [res]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { loadBook(); const id = setInterval(() => { if (!document.hidden) loadBook(); }, 4000); return () => clearInterval(id); }, [loadBook]);
  useEffect(() => { loadOrders(); const id = setInterval(() => { if (!document.hidden) loadOrders(); }, 15000); return () => clearInterval(id); }, [loadOrders]);
  useEffect(() => { fetch(`${API}/config`).then((r) => r.json()).then((d) => d.deposit_address && setDepAddr(d.deposit_address)).catch(() => {}); }, []);

  // level-0 sellers write their own price and may sell at the market like everybody (owner, 15 Nov 2026)
  // the first price of a resource: the best price on the other side of the book (or the last trade)
  useEffect(() => {
    if (priceSet.current || !bk || !info) return;
    // the best bid counts the City's buy order too (a sell at its price goes through at once)
    const cb = info.city_bid && info.city_bid.amount > 0 ? info.city_bid : null;
    const bestBid = cb && (!bk.best_bid || cb.price_cents > toCents(bk.best_bid)) ? cb.price : bk.best_bid;
    const p = side === 'buy' ? (bk.best_ask || bk.last || bestBid) : (bestBid || bk.last || bk.best_ask);
    const base = R?.basePrice ? Number(R.basePrice).toFixed(2) : '';
    setPrice(p || base);
    priceSet.current = true;
  }, [bk, side, info]); // eslint-disable-line react-hooks/exhaustive-deps

  // my own orders are in the book too, but never trade with me: they are left out of every estimate and maximum
  const ownBy = (sideName) => {
    const m = {};
    const stepC = Math.max(1, Math.round(Number(bk?.step || '0.01') * 100));
    for (const o of orders) {
      if (o.side !== sideName || o.resource_id !== res) continue;
      const c = o.price_cents;
      const k = sideName === 'sell' ? Math.ceil(c / stepC) * stepC : Math.floor(c / stepC) * stepC;
      m[k] = (m[k] || 0) + o.remaining_amount;
    }
    return m;
  };
  const minus = (levels, own) => levels.map((l) => ({ ...l, amount: l.amount - (own[l.price_cents] || 0) })).filter((l) => l.amount > 0);
  const asks = useMemo(() => minus(bk?.asks || [], ownBy('sell')), [bk, orders, res]); // eslint-disable-line react-hooks/exhaustive-deps
  const bookAsks = bk?.asks || [];       // the book as everybody sees it (with my orders)
  // + the City Market's buy order for me (spot-info city_bid: its price and what it still buys today) — a sell at
  //   this price or cheaper is bought at once (backend spot_market._sell_to_city)
  const bookBids = useMemo(() => {
    const base = (bk?.bids || []).map((l) => ({ ...l }));
    const cb = info?.city_bid;
    if (!cb || !(cb.amount > 0)) return base;
    const st = Math.max(1, toCents(step));
    const k = Math.floor(cb.price_cents / st) * st;
    const hit = base.find((l) => l.price_cents === k);
    if (hit) { hit.amount += cb.amount; hit.city = true; } else base.push({ price: centsStr(k), price_cents: k, amount: cb.amount, city: true });
    return base.sort((a, b) => b.price_cents - a.price_cents);
  }, [bk, info, step]);
  const bids = useMemo(() => minus(bookBids, ownBy('buy')), [bookBids, orders, res]); // eslint-disable-line react-hooks/exhaustive-deps
  const amt = parseInt(amount, 10) || 0;
  const priceC = toCents(price);
  // market: the average price the book gives for this amount
  const mk = useMemo(() => {
    if (otype !== 'market') return null;
    const w = walk(side === 'buy' ? asks : bids, { units: amt || 1 });
    return w.units ? { avgC: w.cents / w.units, units: w.units, cents: w.cents } : null;
  }, [otype, side, asks, bids, amt]);
  const effC = otype === 'market' ? (mk ? mk.avgC : NaN) : priceC;

  // max buy / sell
  const availC = Math.round((info?.available_city || 0) * 100);
  // max buy = what the sellers in the book really offer (at my limit price, or at any price for a market order),
  // no more than the free warehouse room and what the money pays for; max sell = my stock (market: what buyers take)
  const maxUnits = useMemo(() => {
    if (!info) return 0;
    if (side === 'sell') {
      const have = info.have || 0;
      if (otype === 'market') return Math.min(have, bids.reduce((a, l) => a + l.amount, 0));
      return have;
    }
    const room = info.room_units || 0;
    const levels = otype === 'market' ? asks : asks.filter((l) => priceC > 0 && l.price_cents <= priceC);
    return walk(levels, { units: room, budgetC: availC }).units;
  }, [info, side, otype, asks, bids, availC, priceC]);

  // a price set by the screen (the first price of a resource, the system price, a tap in the book) recounts the value
  useEffect(() => {
    if (otype === 'limit' && lastEdit.current === 'amount' && amt > 0 && priceC > 0) setVolume(centsStr(amt * priceC));
  }, [price]); // eslint-disable-line react-hooks/exhaustive-deps

  const recount = (nextPriceC, from) => {
    if (!(nextPriceC > 0)) return;
    if (from === 'volume') {
      const v = toCents(volume);
      if (v > 0) setAmount(String(Math.floor(v / nextPriceC)));
    } else if (amt > 0) setVolume(centsStr(Math.round(amt * nextPriceC)));
  };
  const onPrice = (s) => { const x = cleanNum(s, true); setPrice(x); recount(toCents(x), lastEdit.current); };
  // the amount never goes above what fits in my warehouses (buy) or what I have (sell) — whatever the price
  const capUnits = () => (!info ? Infinity : side === 'buy' ? Math.max(0, info.room_units || 0) : Math.max(0, info.have || 0));
  const onAmount = (s) => {
    let x = cleanNum(s, false);
    if ((parseInt(x, 10) || 0) > capUnits()) x = String(capUnits());
    lastEdit.current = 'amount'; setAmount(x);
    const n = parseInt(x, 10) || 0;
    if (!n) { setVolume(''); return; }
    if (otype === 'market') {
      const w = walk(side === 'buy' ? asks : bids, { units: n });
      setVolume(w.units ? centsStr(w.cents) : '');
    } else if (priceC > 0) setVolume(centsStr(n * priceC));
  };
  const onVolume = (s) => {
    const x = cleanNum(s, true); lastEdit.current = 'volume'; setVolume(x);
    const v = toCents(x);
    if (!(v > 0)) { setAmount(''); return; }
    let n = otype === 'market' ? (walk(side === 'buy' ? asks : bids, { budgetC: v }).units || 0) : priceC > 0 ? Math.floor(v / priceC) : 0;
    if (n > capUnits()) { onAmount(String(capUnits())); return; }         // more than fits: the amount and value follow the cap
    setAmount(n ? String(n) : '');
  };
  const setPct = (p) => { const n = Math.floor(maxUnits * p / 100); onAmount(String(n || '')); };
  const pct = maxUnits > 0 ? Math.min(100, Math.round(amt / maxUnits * 100)) : 0;
  useEffect(() => { onAmount(amount); }, [otype, side]); // eslint-disable-line react-hooks/exhaustive-deps

  const taxNet = side === 'sell' && info && amt > 0 && effC > 0 ? (amt * effC / 100) * (1 - (info.tax_rate || 0)) : null;
  const errText = (d) => {
    const s = String(d || '');
    const [code, n] = s.split(':');
    const m = {
      no_business_to_buy: T.noBusiness, no_room: f(T.noRoom, { n }), nothing_to_buy: T.nothingBuy, nothing_to_sell_to: T.nothingSell,
      price_required: T.needPrice, bad_price: T.needPrice, buy_orders_limit: f(T.ordersLimit, { n }),
      zero_level_limit_only: f(T.zeroSeller, { p: info?.system_price || '' }), market_busy: T.busy,
      sell_slots: f(T.sellSlots, { n }), city_skip: f(T.citySkip, { r: s.slice(10) }), not_enough_resource: f(T.notEnough, { n: n ?? info?.have ?? 0 }),
    };
    return m[code] || s;
  };
  const submit = async () => {
    if (!amt) { toast.error(T.needAmount); return; }
    if (otype === 'limit' && !(priceC > 0)) { toast.error(T.needPrice); return; }
    setBusy(true);
    try {
      const body = { resource_id: res, side, order_type: otype, amount: amt, ...(otype === 'limit' ? { price: centsStr(priceC) } : {}) };
      const r = await fetch(`${API}/market/order`, { method: 'POST', headers: H(), body: JSON.stringify(body) });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { toast.error(errText(d.detail?.message || d.detail)); return; }
      if (d.filled >= d.requested) toast.success(f(side === 'buy' ? T.doneBuy : T.doneSell, { n: d.filled, p: d.avg_price }));
      else if (d.filled > 0) toast.success(otype === 'market' ? f(side === 'buy' ? T.doneBuy : T.doneSell, { n: d.filled, p: d.avg_price })
        : f(T.partial, { n: d.filled, p: d.avg_price, r: d.rest }));
      else toast.success(f(T.placed, { n: d.rest, p: centsStr(priceC) }));
      if (d.city_skip) toast.message(f(T.citySkip, { r: d.city_skip }));
      setAmount(''); setVolume('');
      loadBook(); loadInfo(); loadOrders(); if (onBalanceChanged) onBalanceChanged();
    } catch (e) { toast.error(f(T.error, { e: e.message })); } finally { setBusy(false); }
  };
  const cancel = async (id) => {
    try {
      const r = await fetch(`${API}/market/cancel`, { method: 'POST', headers: H(), body: JSON.stringify({ order_id: id }) });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { toast.error(errText(d.detail)); return; }
      toast.success(T.cancelled); loadOrders(); loadBook(); loadInfo(); if (onBalanceChanged) onBalanceChanged();
    } catch (e) { toast.error(f(T.error, { e: e.message })); }
  };
  const pickPrice = (p) => { setOtype('limit'); onPrice(p); priceSet.current = true; };

  // the book's visible rows: asks nearest to the mid at the bottom
  const aRows = bookAsks.slice(0, ROWS).slice().reverse();
  const bRows = bookBids.slice(0, ROWS);
  // my own orders in the book: a dot between the price and the amount of that level («here is my lot»)
  const mineA = ownBy('sell'); const mineB = ownBy('buy');
  const Dot = ({ on }) => (on ? <span className="relative w-1.5 h-1.5 rounded-full bg-amber-300 shrink-0" title={T.mine} data-testid="spot-mine-dot" /> : null);
  const maxA = Math.max(1, ...bookAsks.slice(0, ROWS).map((l) => l.amount));
  const maxB = Math.max(1, ...bookBids.slice(0, ROWS).map((l) => l.amount));
  const ch = bk?.change_24h;
  const midUp = ch == null ? null : ch >= 0;
  const buyC = side === 'buy';

  return (
    <div className="space-y-3" data-testid="spot">
      {/* the resource */}
      <div className="flex items-center justify-between gap-2">
        <button type="button" onClick={() => setPicker(true)} className="flex items-center gap-2 min-w-0 text-left" data-testid="spot-res-picker">
          <span className="text-2xl">{R?.icon}</span>
          <span className="min-w-0">
            <span className="flex items-center gap-1 text-white font-bold text-lg leading-tight truncate">{R?.name}<ChevronDown className="w-4 h-4 shrink-0" /></span>
            <span className="block text-[11px] text-white/45">{f(T.tier, { n: R?.tier || 1 })} · $CITY</span>
          </span>
        </button>
        <div className="text-right shrink-0">
          <div className={`text-lg font-bold tabular-nums ${midUp == null ? 'text-white' : midUp ? 'text-emerald-400' : 'text-red-400'}`}>{bk?.last || bk?.mid || '—'}</div>
          <div className={`text-[11px] tabular-nums ${ch == null ? 'text-white/40' : ch >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{ch == null ? (bk?.last ? T.last : T.noTrades) : `${ch >= 0 ? '+' : ''}${ch}%`}</div>
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-3">
        {/* ── the order form ── */}
        <div className="space-y-2 min-w-0" data-testid="spot-form">
          <div className="grid grid-cols-2 rounded-full bg-white/5 p-0.5">
            <button type="button" onClick={() => setSide('buy')} data-testid="spot-side-buy" data-active={buyC}
              className={`rounded-full py-1.5 text-sm font-bold transition-colors ${buyC ? 'bg-emerald-500/25 text-emerald-300' : 'text-white/50'}`}>{T.buy}</button>
            <button type="button" onClick={() => setSide('sell')} data-testid="spot-side-sell" data-active={!buyC}
              className={`rounded-full py-1.5 text-sm font-bold transition-colors ${!buyC ? 'bg-red-500/25 text-red-300' : 'text-white/50'}`}>{T.sell}</button>
          </div>
          <div className="flex items-center justify-between gap-1 text-[11px]">
            <span className="text-white/50 underline decoration-dotted">{T.available}</span>
            <span className="flex items-center gap-1 text-white tabular-nums truncate" data-testid="spot-available">
              {buyC ? `${money(info?.available_city)} $CITY` : `${info?.have ?? 0} ${R?.icon || ''}`}
              {buyC && (
                <button type="button" onClick={() => setDeposit(true)} aria-label={T.deposit} title={T.deposit} data-testid="spot-deposit"
                  className="text-cyber-cyan shrink-0"><PlusCircle className="w-4 h-4" /></button>
              )}
            </span>
          </div>
          <MiniSelect value={otype} onChange={setOtype} testid="spot-type"
            options={[{ value: 'limit', label: T.limit }, { value: 'market', label: T.market }]}
            className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm font-semibold text-white" />
          {otype === 'limit' ? (
            <label className="block rounded-lg bg-white/5 border border-white/10 px-3 py-1.5" data-testid="spot-price-wrap">
              <span className="block text-[10px] text-white/45">{T.price}</span>
              <span className="flex items-center gap-2">
                <input value={price} onChange={(e) => onPrice(e.target.value)} inputMode="decimal"
                  className="w-full min-w-0 bg-transparent text-white font-semibold tabular-nums outline-none" data-testid="spot-price" placeholder="0.00" />
                <span className="text-xs font-bold text-white/70">$CITY</span>
              </span>
            </label>
          ) : (
            <div className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white/50" data-testid="spot-price-wrap">{T.marketPrice}</div>
          )}
          <label className="block rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 focus-within:border-white/40">
            <span className="block text-[10px] text-white/45">{T.amount}</span>
            <span className="flex items-center gap-2">
              <input value={amount} onChange={(e) => onAmount(e.target.value)} inputMode="numeric" pattern="[0-9]*"
                className="w-full min-w-0 bg-transparent text-white font-semibold tabular-nums outline-none" data-testid="spot-amount-input" placeholder="0" />
              <span className="text-xs font-bold text-white/70">{T.pcs}</span>
            </span>
          </label>
          {/* 0 / 25 / 50 / 75 / 100 % of the maximum */}
          <div className="relative px-1 py-1.5" data-testid="spot-slider">
            <div className="absolute left-2 right-2 top-1/2 h-0.5 -translate-y-1/2 bg-white/15" />
            <div className="absolute left-2 top-1/2 h-0.5 -translate-y-1/2 bg-white/60" style={{ width: `calc((100% - 1rem) * ${pct / 100})` }} />
            <div className="relative flex justify-between">
              {[0, 25, 50, 75, 100].map((p) => (
                <button key={p} type="button" onClick={() => setPct(p)} aria-label={`${p}%`}
                  className={`w-4 h-4 rounded-full border-2 ${pct >= p && (p > 0 || amt > 0) ? 'border-white bg-white/80' : 'border-white/40 bg-void'}`} />
              ))}
            </div>
          </div>
          <label className="block rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 focus-within:border-white/40">
            <span className="block text-[10px] text-white/45">{T.volume}</span>
            <span className="flex items-center gap-2">
              <input value={volume} onChange={(e) => onVolume(e.target.value)} inputMode="decimal"
                className="w-full min-w-0 bg-transparent text-white font-semibold tabular-nums outline-none" data-testid="spot-volume" placeholder="0.00" />
              <span className="text-xs font-bold text-white/70">$CITY</span>
            </span>
          </label>
          <div className="rounded-lg border border-white/10 px-3 py-1.5 flex items-center justify-between text-[11px]" data-testid="spot-max">
            <span className="text-white/50">{buyC ? T.maxBuy : T.maxSell}</span>
            <span className="text-white tabular-nums">{maxUnits} {T.pcs}</span>
          </div>
          {buyC && info && !info.can_buy && <div className="text-[11px] text-amber-300 leading-snug">{T.noBusiness}</div>}
          {buyC && info && info.can_buy && <div className="text-[10px] text-white/40">{f(T.room, { n: info.room_units })}</div>}
          {taxNet != null && <div className="text-[11px] text-white/55 leading-snug" data-testid="spot-tax">{f(T.tax, { p: Math.round((info.tax_rate || 0) * 100), net: money(taxNet) })}</div>}
          <button type="button" onClick={submit} disabled={busy || (buyC && info && !info.can_buy)} data-testid="spot-submit"
            className={`w-full rounded-full py-2.5 font-bold text-white transition-opacity disabled:opacity-40 ${buyC ? 'bg-emerald-500' : 'bg-red-500'}`}>
            {buyC ? T.buy : T.sell} {R?.icon}
          </button>
        </div>

        {/* ── the book ── */}
        <div className="min-w-0 text-[11px]" data-testid="spot-book">
          <div className="flex justify-between text-white/45 mb-1"><span>{T.bookPrice}</span><span>{T.bookAmount}</span></div>
          <div className="space-y-px">
            {Array.from({ length: ROWS - aRows.length }).map((_, i) => <div key={`ea${i}`} className="h-[22px]" />)}
            {aRows.map((l) => (
              <button type="button" key={`a${l.price}`} onClick={() => pickPrice(l.price)} className="relative w-full h-[22px] flex justify-between items-center px-0.5 tabular-nums">
                <span className="absolute right-0 top-0 bottom-0 bg-red-500/15" style={{ width: `${(l.amount / maxA) * 100}%` }} />
                <span className="relative text-red-400">{l.price}</span><Dot on={!!mineA[l.price_cents]} /><span className="relative text-white/85">{kfmt(l.amount)}</span>
              </button>
            ))}
          </div>
          <button type="button" onClick={() => setFullBook(true)} className="w-full flex items-center justify-between py-1.5" data-testid="spot-mid">
            <span className="text-left">
              <span className={`block text-xl font-bold tabular-nums ${midUp == null ? 'text-white' : midUp ? 'text-emerald-400' : 'text-red-400'}`}>{bk?.mid || '—'}</span>
              <span className="block text-[10px] text-white/45 tabular-nums">{bk?.last ? `${T.last} ${bk.last}` : T.mid}</span>
            </span>
            <ArrowRight className="w-4 h-4 text-white/70" />
          </button>
          <div className="space-y-px">
            {bRows.map((l) => (
              <button type="button" key={`b${l.price}`} onClick={() => pickPrice(l.price)} className="relative w-full h-[22px] flex justify-between items-center px-0.5 tabular-nums">
                <span className="absolute right-0 top-0 bottom-0 bg-emerald-500/15" style={{ width: `${(l.amount / maxB) * 100}%` }} />
                <span className="relative text-emerald-400">{l.price}</span><Dot on={!!mineB[l.price_cents]} /><span className="relative text-white/85">{kfmt(l.amount)}</span>
              </button>
            ))}
            {Array.from({ length: ROWS - bRows.length }).map((_, i) => <div key={`eb${i}`} className="h-[22px]" />)}
          </div>
          <div className="mt-1.5 flex items-center gap-1 text-[10px] font-semibold" data-testid="spot-share">
            <span className="px-1 border border-emerald-400 text-emerald-400 rounded">B</span>
            <span className="relative flex-1 h-4 rounded bg-red-500/20 overflow-hidden">
              <span className="absolute left-0 top-0 bottom-0 bg-emerald-500/30" style={{ width: `${bk?.buy_share ?? 50}%` }} />
              <span className="relative flex justify-between px-1 leading-4"><span className="text-emerald-400">{bk?.buy_share ?? 50}%</span><span className="text-red-400">{bk?.sell_share ?? 50}%</span></span>
            </span>
            <span className="px-1 border border-red-400 text-red-400 rounded">S</span>
          </div>
          <MiniSelect value={step} onChange={setStep} testid="spot-step" label={T.step} up
            options={STEPS.map((s) => ({ value: s, label: s }))}
            wrapClass="mt-1.5" className="w-full rounded bg-white/5 border border-white/10 px-2 py-1 text-white" />
        </div>
      </div>

      {/* ── my open orders ── */}
      <div className="border-t border-white/10 pt-2" data-testid="spot-orders">
        <div className="flex items-center justify-between mb-2">
          <span className="text-white font-bold">{T.orders} ({orders.length})</span>
          <button type="button" onClick={() => navigate('/history?group=trade')} aria-label={T.history} title={T.history} data-testid="spot-history-btn"
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-white/10 text-white/80"><History className="w-4 h-4" /></button>
        </div>
        {orders.length === 0 && <div className="text-center text-white/40 text-sm py-6">{T.noOrders}</div>}
        <div className="space-y-2">
          {orders.map((o) => {
            const r = getResource(o.resource_id, lang);
            const buy = o.side === 'buy';
            return (
              <div key={o.order_id} className="rounded-xl bg-white/5 border border-white/10 p-2.5" data-testid={`spot-order-${o.order_id}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 min-w-0">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${buy ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>{buy ? T.sideBuy : T.sideSell}</span>
                    <span className="text-white text-sm font-semibold truncate">{r.icon} {r.name}</span>
                  </span>
                  <span className="text-[10px] text-white/40 shrink-0">{f(T.ago, { t: ago(o.created_at, T) })}</span>
                </div>
                <div className="mt-1.5 grid grid-cols-3 gap-1 text-[11px]">
                  <span><span className="block text-white/40">{T.price}</span><span className="text-white tabular-nums">{o.price_per_item}</span></span>
                  <span><span className="block text-white/40">{T.amount}</span><span className="text-white tabular-nums">{o.remaining_amount} / {o.initial_amount}</span></span>
                  <span><span className="block text-white/40">{T.locked}</span><span className="text-white tabular-nums">{buy ? `${money(o.total_locked_value)} $CITY` : `${o.remaining_amount} ${r.icon}`}</span></span>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded bg-white/10 overflow-hidden"><div className={`h-full ${buy ? 'bg-emerald-400' : 'bg-red-400'}`} style={{ width: `${o.progress_percent}%` }} /></div>
                  <span className="text-[10px] text-white/50 tabular-nums">{f(T.filled, { f: o.filled_amount, i: o.initial_amount })}</span>
                  {o.can_cancel && (
                    <button type="button" onClick={() => cancel(o.order_id)} data-testid={`spot-cancel-${o.order_id}`}
                      className="text-[11px] font-semibold px-2 py-1 rounded border border-white/20 text-white/85">{T.cancel}</button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* the resource picker */}
      <Dialog open={picker} onOpenChange={setPicker}>
        <DialogContent className="bg-void border-white/10 max-w-md max-h-[80vh] overflow-y-auto" data-testid="spot-picker">
          <DialogHeader><DialogTitle className="text-white">{T.pickRes}</DialogTitle></DialogHeader>
          <label className="flex items-center gap-2 rounded-lg bg-white/5 border border-white/10 px-3 py-2">
            <Search className="w-4 h-4 text-white/50" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={T.search} className="flex-1 bg-transparent text-white outline-none text-sm" />
          </label>
          {[1, 2, 3].map((tier) => {
            const items = all.filter((r) => Number(r.tier) === tier).map((r) => getResource(r.id, lang))
              .filter((r) => !q || r.name.toLowerCase().includes(q.toLowerCase()));
            if (!items.length) return null;
            return (
              <div key={tier}>
                <div className="text-[11px] text-white/40 mt-2 mb-1">{f(T.tier, { n: tier })}</div>
                <div className="grid grid-cols-2 gap-1.5">
                  {items.map((r) => (
                    <button type="button" key={r.id} onClick={() => { setRes(r.id); setPicker(false); setQ(''); }} data-testid={`spot-pick-${r.id}`}
                      className={`flex items-center gap-2 rounded-lg px-2 py-2 text-left text-sm ${r.id === res ? 'bg-cyber-cyan/15 border border-cyber-cyan/40 text-white' : 'bg-white/5 border border-white/10 text-white/85'}`}>
                      <span className="text-lg">{r.icon}</span><span className="truncate">{r.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </DialogContent>
      </Dialog>

      {/* the full order book */}
      <Dialog open={fullBook} onOpenChange={setFullBook}>
        <DialogContent className="bg-void border-white/10 max-w-md max-h-[88vh] overflow-y-auto" data-testid="spot-fullbook">
          <DialogHeader><DialogTitle className="text-white">{T.orderBook} · {R?.icon} {R?.name}</DialogTitle></DialogHeader>
          <div className={`text-center text-2xl font-bold tabular-nums ${midUp == null ? 'text-white' : midUp ? 'text-emerald-400' : 'text-red-400'}`}>{bk?.mid || '—'}</div>
          <div className="flex items-center gap-1 text-[11px] font-semibold">
            <span className="px-1 border border-emerald-400 text-emerald-400 rounded">B</span>
            <span className="relative flex-1 h-5 rounded bg-red-500/20 overflow-hidden">
              <span className="absolute left-0 top-0 bottom-0 bg-emerald-500/30" style={{ width: `${bk?.buy_share ?? 50}%` }} />
              <span className="relative flex justify-between px-1.5 leading-5"><span className="text-emerald-400">{bk?.buy_share ?? 50}%</span><span className="text-red-400">{bk?.sell_share ?? 50}%</span></span>
            </span>
            <span className="px-1 border border-red-400 text-red-400 rounded">S</span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-white/50">
            <span>{T.buy}</span><span>{T.sell}</span>
            <MiniSelect value={step} onChange={setStep} testid="spot-step-full" label={T.step}
              options={STEPS.map((s) => ({ value: s, label: s }))}
              className="rounded bg-white/5 border border-white/10 px-2 py-0.5 text-white min-w-[64px]" />
          </div>
          <div className="grid grid-cols-4 text-[10px] text-white/40"><span>{T.bookAmount}</span><span className="text-right pr-1">{T.price}</span><span className="pl-1">{T.price}</span><span className="text-right">{T.bookAmount}</span></div>
          {(() => {
            const n = Math.max(bookBids.length, bookAsks.length);
            const mb = Math.max(1, ...bookBids.map((l) => l.amount)); const ma = Math.max(1, ...bookAsks.map((l) => l.amount));
            if (!n) return <div className="text-center text-white/40 py-6 text-sm">{T.empty}</div>;
            return (
              <div className="space-y-px text-[12px] tabular-nums">
                {Array.from({ length: n }).map((_, i) => {
                  const b = bookBids[i]; const a = bookAsks[i];
                  return (
                    <div key={i} className="grid grid-cols-2 h-6">
                      <button type="button" disabled={!b} onClick={() => { if (b) { pickPrice(b.price); setFullBook(false); } }} className="relative flex justify-between items-center pr-1">
                        {b && <span className="absolute right-0 top-0 bottom-0 bg-emerald-500/15" style={{ width: `${(b.amount / mb) * 100}%` }} />}
                        <span className="relative text-white/85">{b ? kfmt(b.amount) : ''}</span>{b && <Dot on={!!mineB[b.price_cents]} />}<span className="relative text-emerald-400">{b?.price || ''}</span>
                      </button>
                      <button type="button" disabled={!a} onClick={() => { if (a) { pickPrice(a.price); setFullBook(false); } }} className="relative flex justify-between items-center pl-1">
                        {a && <span className="absolute left-0 top-0 bottom-0 bg-red-500/15" style={{ width: `${(a.amount / ma) * 100}%` }} />}
                        <span className="relative text-red-400">{a?.price || ''}</span>{a && <Dot on={!!mineA[a.price_cents]} />}<span className="relative text-white/85">{a ? kfmt(a.amount) : ''}</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            );
          })()}
          <p className="text-[10px] text-white/40">{T.tapPrice}</p>
        </DialogContent>
      </Dialog>

      <DepositModal isOpen={deposit} onClose={() => setDeposit(false)} receiverAddress={depAddr}
        onSuccess={() => { setDeposit(false); loadInfo(); if (onBalanceChanged) onBalanceChanged(); }}
        updateBalance={() => { loadInfo(); if (onBalanceChanged) onBalanceChanged(); }} />
    </div>
  );
}
