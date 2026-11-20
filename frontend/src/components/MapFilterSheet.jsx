/**
 * MapFilterSheet — «Фильтр» on the city map: business types (by tier, with how many are on sale now),
 * where it is sold (city / players / rent), price range, business level, lot size, district.
 * «Применить» hands the filter to the page, which outlines the matching buildings on sale in red
 * (CityMapEngine.setHighlight) until the filter is reset or the player leaves the map.
 */
import { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { SlidersHorizontal, Check } from 'lucide-react';
import { fill } from '@/lib/translationsMore';
import { tBusiness } from '@/lib/translationsExtra';

export const EMPTY_FILTER = { types: [], sources: ['city', 'market', 'rent'], tiers: [], priceMin: '', priceMax: '', levelMin: '', sizes: [], districts: [] };
const SIZES = ['1x1', '1x2', '2x2', '3x3'];
const sizeOf = (c) => { const w = c.w || 1, h = c.h || 1; return w === h ? `${w}x${h}` : '1x2'; };

/** The predicate the map engine uses: (cell, sale) → matches the filter. */
export function filterPredicate(f) {
  const num = (v) => (v === '' || v == null || Number.isNaN(Number(v)) ? null : Number(v));
  const pMin = num(f.priceMin), pMax = num(f.priceMax), lMin = num(f.levelMin);
  return (c, sale) => {
    const b = c.building; if (!b || !sale) return false;
    if (f.sources.length && !f.sources.includes(sale.kind)) return false;
    if (f.types.length && !f.types.includes(b.type)) return false;
    if (f.tiers.length && !f.tiers.includes(Number(b.tier || 1))) return false;
    if (pMin != null && (sale.price || 0) < pMin) return false;
    if (pMax != null && (sale.price || 0) > pMax) return false;
    if (lMin != null && Number(b.level || 0) < lMin) return false;
    if (f.sizes.length && !f.sizes.includes(sizeOf(c))) return false;
    if (f.districts.length && !f.districts.includes(String(c.district))) return false;
    return true;
  };
}

export const filterActive = (f) => !!f;

function Chip({ on, onClick, children, testid }) {
  return (
    <button type="button" onClick={onClick} data-testid={testid}
      className={`px-2.5 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-colors ${on ? 'bg-rose-500/20 border-rose-400/70 text-white' : 'bg-white/[0.04] border-white/10 text-white/70 hover:border-white/25'}`}>
      {on && <Check className="w-3 h-3 text-rose-300" />}{children}
    </button>
  );
}

export default function MapFilterSheet({ open, onClose, value, onApply, onReset, businessTypes, cells, saleOf, t, lang }) {
  const [f, setF] = useState(value || EMPTY_FILTER);
  useEffect(() => { if (open) setF(value || EMPTY_FILTER); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  // what is on sale right now, per business type (shown next to every type)
  const onSale = useMemo(() => {
    const m = {};
    (cells || []).forEach((c) => { if (c.building && saleOf(c)) m[c.building.type] = (m[c.building.type] || 0) + 1; });
    return m;
  }, [cells, saleOf, open]); // eslint-disable-line react-hooks/exhaustive-deps
  const districts = useMemo(() => [...new Set((cells || []).map((c) => c.district).filter((d) => d != null).map(String))].sort(), [cells]);
  const types = useMemo(() => {
    const fromCfg = Object.entries(businessTypes || {}).map(([k, v]) => ({ k, tier: Number(v?.tier || 1), icon: v?.icon || '🏢' }));
    const known = new Set(fromCfg.map((x) => x.k));
    (cells || []).forEach((c) => { const b = c.building; if (b && !known.has(b.type)) { known.add(b.type); fromCfg.push({ k: b.type, tier: Number(b.tier || 1), icon: b.icon || '🏢' }); } });
    return fromCfg.sort((a, b) => a.tier - b.tier || tBusiness(a.k, lang).localeCompare(tBusiness(b.k, lang)));
  }, [businessTypes, cells, lang]);

  const toggle = (key, v) => setF((s) => ({ ...s, [key]: s[key].includes(v) ? s[key].filter((x) => x !== v) : [...s[key], v] }));
  const matches = useMemo(() => {
    const p = filterPredicate(f);
    return (cells || []).filter((c) => { const s = c.building && saleOf(c); return s && p(c, s); }).length;
  }, [f, cells, saleOf, open]); // eslint-disable-line react-hooks/exhaustive-deps
  const inp = 'w-full h-9 rounded-xl bg-black/40 border border-white/10 text-sm text-white px-3 outline-none focus:border-rose-400/60';
  const head = 'text-[11px] font-black tracking-[0.16em] uppercase text-white/50 mb-2';

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#0d1526] border-rose-500/30 rounded-2xl p-0 sm:max-w-lg max-h-[88vh] overflow-hidden flex flex-col gap-0" data-testid="map-filter-sheet">
        <div className="p-4 pb-3 border-b border-white/10">
          <DialogTitle className="flex items-center gap-2 text-white text-lg font-black"><SlidersHorizontal className="w-5 h-5 text-rose-400" />{t('mf_title')}</DialogTitle>
          <p className="text-[11px] text-white/55 mt-1">{t('mf_hint')}</p>
        </div>
        <div className="p-4 space-y-5 overflow-y-auto">
          <div>
            <div className={head}>{t('mf_source')}</div>
            <div className="flex flex-wrap gap-2">
              {['city', 'market', 'rent'].map((k) => <Chip key={k} on={f.sources.includes(k)} onClick={() => toggle('sources', k)} testid={`mf-src-${k}`}>{t(`mf_src_${k}`)}</Chip>)}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <div className={head.replace(' mb-2', '')}>{t('mf_types')}</div>
              <div className="flex gap-2 text-[11px]">
                <button type="button" className="text-rose-300 font-bold" onClick={() => setF((s) => ({ ...s, types: types.filter((x) => onSale[x.k]).map((x) => x.k) }))}>{t('mf_all')}</button>
                <button type="button" className="text-white/50 font-bold" onClick={() => setF((s) => ({ ...s, types: [] }))}>{t('mf_clear')}</button>
              </div>
            </div>
            {[1, 2, 3].map((tier) => {
              const list = types.filter((x) => x.tier === tier);
              if (!list.length) return null;
              const allOn = list.every((x) => f.types.includes(x.k));
              return (
                <div key={tier} className="mb-3">
                  <button type="button" onClick={() => setF((s) => ({ ...s, types: allOn ? s.types.filter((x) => !list.some((y) => y.k === x)) : [...new Set([...s.types, ...list.map((y) => y.k)])] }))}
                    className={`text-[11px] font-bold mb-1.5 px-2 py-0.5 rounded-md ${tier === 3 ? 'bg-purple-500/20 text-purple-300' : tier === 2 ? 'bg-blue-500/20 text-blue-300' : 'bg-green-500/20 text-green-300'}`} data-testid={`mf-tier-${tier}`}>
                    {fill(t('mf_tier_n'), { n: tier })}
                  </button>
                  <div className="grid grid-cols-2 gap-1.5">
                    {list.map((x) => {
                      const on = f.types.includes(x.k), n = onSale[x.k] || 0;
                      return (
                        <button type="button" key={x.k} onClick={() => toggle('types', x.k)} data-testid={`mf-type-${x.k}`}
                          className={`flex items-center gap-2 rounded-xl border px-2 py-1.5 text-left transition-colors ${on ? 'bg-rose-500/15 border-rose-400/70' : 'bg-white/[0.03] border-white/10'} ${n ? '' : 'opacity-50'}`}>
                          <span className="text-lg leading-none">{x.icon}</span>
                          <span className="flex-1 min-w-0">
                            <span className="block text-xs font-semibold text-white truncate">{tBusiness(x.k, lang)}</span>
                            <span className="block text-[10px] text-white/50">{fill(t('mf_on_sale'), { n })}</span>
                          </span>
                          {on && <Check className="w-3.5 h-3.5 text-rose-300 shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className={head}>{t('mf_price')}</div>
              <div className="flex gap-2">
                <input type="number" min="0" inputMode="numeric" placeholder={t('mf_from')} value={f.priceMin} onChange={(e) => setF((s) => ({ ...s, priceMin: e.target.value }))} className={inp} data-testid="mf-price-min" />
                <input type="number" min="0" inputMode="numeric" placeholder={t('mf_to')} value={f.priceMax} onChange={(e) => setF((s) => ({ ...s, priceMax: e.target.value }))} className={inp} data-testid="mf-price-max" />
              </div>
            </div>
            <div>
              <div className={head}>{t('mf_level')}</div>
              <select value={f.levelMin} onChange={(e) => setF((s) => ({ ...s, levelMin: e.target.value }))} className={inp} data-testid="mf-level">
                <option value="">{t('mf_any')}</option>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((l) => <option key={l} value={l}>{l}+</option>)}
              </select>
            </div>
          </div>

          <div>
            <div className={head}>{t('mf_size')}</div>
            <div className="flex flex-wrap gap-2">{SIZES.map((sz) => <Chip key={sz} on={f.sizes.includes(sz)} onClick={() => toggle('sizes', sz)}>{sz.replace('x', '×')}</Chip>)}</div>
          </div>

          {districts.length > 1 && (
            <div>
              <div className={head}>{t('mf_district')}</div>
              <div className="flex flex-wrap gap-2">{districts.map((d) => <Chip key={d} on={f.districts.includes(d)} onClick={() => toggle('districts', d)}>{fill(t('mf_district_n'), { n: d })}</Chip>)}</div>
            </div>
          )}
        </div>
        <div className="p-4 pt-3 border-t border-white/10 bg-[#0b1220]">
          <div className="text-center text-xs text-white/60 mb-2" data-testid="mf-count">{matches ? fill(t('mf_found'), { n: matches }) : t('mf_none')}</div>
          <div className="grid grid-cols-2 gap-2">
            <button type="button" onClick={() => { setF(EMPTY_FILTER); onReset(); }} className="h-11 rounded-xl border border-white/15 text-white/85 font-bold" data-testid="mf-reset">{t('mf_reset')}</button>
            <button type="button" onClick={() => onApply(f)} className="h-11 rounded-xl bg-gradient-to-r from-rose-500 to-red-600 text-white font-black shadow-lg shadow-rose-500/25" data-testid="mf-apply">{t('mf_apply')}</button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
