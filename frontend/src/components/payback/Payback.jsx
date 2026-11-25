/** «Окупаемость при идеальных условиях»: one line (button) with the number of days, a tap opens the breakdown.
 *  Server: backend/payback.py — /api/payback/business/{id} (my business) and /api/payback/type/{type}?level&price_ton
 *  (a lot on the map / for sale). The conditions are always written next to the number. */
import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { getResource } from '@/lib/resourceConfig';
import { useUiText } from '@/lib/uiI18n';
import FitText from '@/components/ui/FitText';
// texts: src/i18n/payback.json; for every language but Russian the server's LibreTranslate text wins (backend/ui_i18n.py)
import L from '@/i18n/payback.json';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;

const f = (s, v) => Object.entries(v || {}).reduce((a, [k, x]) => a.split(`{${k}}`).join(String(x)), s);
const n0 = (v) => Math.round(Number(v) || 0).toLocaleString('ru-RU').replace(/ /g, ' ');
const dd = (v) => Math.ceil(Number(v) || 0);
/** the next step's line: the extra profit it adds pays it back; a level that adds no profit by itself (casino 1 → 2) —
 *  the whole business on that level; a free level-0 business — its buyout 0 → 1 (backend/payback.py, next.mode) */
const nextText = (T, nx) => (nx.days == null ? f(T.nextNever, { l: nx.level, c: n0(nx.cost_city) })
  : nx.mode === 'full' ? f(T.nextFull, { l: nx.level, c: n0(nx.cost_city), p: n0(nx.profit_city), d: dd(nx.days) })
    : f(T.next, { l: nx.level, c: n0(nx.cost_city), e: n0(nx.extra_city), d: dd(nx.days) }));

/** bizId — my business; or type + level + priceTon — a lot on the map. variant 'chip' (business screen) | 'line'. */
export default function PaybackButton({ bizId, type, level = 1, priceTon, lang = 'ru', variant = 'line', className = '' }) {
  const T = useUiText('payback', lang, L);
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let alive = true;
    const tk = localStorage.getItem('token');
    const url = bizId ? `${API}/payback/business/${bizId}`
      : type ? `${API}/payback/type/${type}?level=${level || 1}${priceTon != null ? `&price_ton=${priceTon}` : ''}` : null;
    if (!url) return undefined;
    fetch(url, { headers: tk ? { Authorization: `Bearer ${tk}` } : {} }).then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (alive) setData(d); }).catch(() => {});
    return () => { alive = false; };
  }, [bizId, type, level, priceTon]);
  if (!data || data.days === undefined) return null;
  const never = data.days === null && data.invest_city != null;
  if (data.invest_city == null && !data.day) return null;
  const label = data.invest_city == null ? `${n0(data.day.profit_city)} $CITY ${T.perDay}`
    : never ? T.never : f(data.buyout ? T.buyout : T.btn, { d: dd(data.days) });
  const d = data.day || {};
  const r = getResource(d.resource, lang) || {};
  const row = (k, v, cls = 'text-white') => (
    <div className="flex justify-between gap-3 text-sm"><span className="text-white/60">{k}</span><span className={`font-semibold tabular-nums ${cls}`}>{v}</span></div>
  );
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} data-testid="payback-btn"
        className={variant === 'chip'
          ? `rounded-2xl bg-black/40 border border-emerald-400/30 px-2 py-2 flex items-center justify-center gap-1.5 text-emerald-300 font-bold text-[13px] whitespace-nowrap active:scale-95 transition-transform ${className}`
          : `w-full rounded-lg bg-emerald-500/10 border border-emerald-400/25 px-3 py-2 flex items-center gap-2 text-emerald-300 text-xs font-semibold text-left ${className}`}>
        <TrendingUp className="w-4 h-4 shrink-0" />
        {variant === 'chip'
          ? <FitText max={13} min={8} className={never ? 'text-amber-300' : ''}>{label}</FitText>
          : <span className={never ? 'text-amber-300' : ''}>{label}</span>}
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-void border-white/10 max-w-md" data-testid="payback-dialog">
          <DialogHeader><DialogTitle className="text-white flex items-center gap-2"><TrendingUp className="w-5 h-5 text-emerald-400" />{T.title}</DialogTitle></DialogHeader>
          <div className="space-y-2">
            {row(T.out, `${r.icon || ''} ${n0(d.qty)} ${r.name || d.resource || ''}`)}
            {row(T.sale, `+${n0(d.gross_city)} $CITY`, 'text-green-400')}
            {row(f(T.tax, { p: Math.round((d.tax_rate || 0) * 100) }), `−${n0(d.tax_city)}`, 'text-red-300')}
            {(d.inputs || []).length > 0 && row(T.raw, `−${n0(d.inputs_city)}`, 'text-red-300')}
            {(d.inputs || []).map((x) => {
              const rr = getResource(x.resource, lang) || {};
              return <div key={x.resource} className="flex justify-between text-xs text-white/45 pl-3"><span>{rr.icon} {n0(x.qty)} × {x.price_city}</span><span>−{n0(x.city)}</span></div>;
            })}
            {row(f(T.rep, { p: d.repair_pct }), `−${n0(d.repair_city)}`, 'text-red-300')}
            <div className="border-t border-white/10 pt-2">{row(T.profit, `${n0(d.profit_city)} $CITY`, d.profit_city > 0 ? 'text-emerald-300' : 'text-red-400')}</div>
            {data.invest_city != null && row(data.buyout ? T.costBuy : f(T.cost, { l: data.level }), `${n0(data.invest_city)} $CITY`)}
            {data.invest_city != null && row(T.days, never ? '—' : `~${dd(data.days)} ${T.dShort}`, never ? 'text-amber-300' : 'text-emerald-300')}
            {data.next && (
              <div className="rounded-lg bg-blue-500/10 border border-blue-400/20 p-2 text-xs text-blue-200" data-testid="payback-next">
                {nextText(T, data.next)}
              </div>
            )}
            <p className="text-[11px] text-white/50 leading-snug">{T.cond}</p>
            <p className="text-[11px] text-white/40 leading-snug">{T.note}</p>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** the upgrade window: one line «the upgrade pays back in ~N d» for my business */
export function UpgradePaybackLine({ bizId, lang = 'ru' }) {
  const T = useUiText('payback', lang, L);
  const [nx, setNx] = useState(null);
  useEffect(() => {
    let alive = true;
    const tk = localStorage.getItem('token');
    if (!bizId) return undefined;
    fetch(`${API}/payback/business/${bizId}`, { headers: tk ? { Authorization: `Bearer ${tk}` } : {} })
      .then((r) => (r.ok ? r.json() : null)).then((d) => { if (alive) setNx(d ? d.next : null); }).catch(() => {});
    return () => { alive = false; };
  }, [bizId]);
  if (!nx) return null;
  return (
    <div className="rounded-lg bg-emerald-500/10 border border-emerald-400/25 p-2 text-xs text-emerald-200 flex gap-2" data-testid="upgrade-payback">
      <TrendingUp className="w-4 h-4 shrink-0 mt-0.5" />
      <span>{nextText(T, nx)}
        <span className="block text-emerald-200/60 mt-0.5">{T.title.toLowerCase()}</span></span>
    </div>
  );
}
