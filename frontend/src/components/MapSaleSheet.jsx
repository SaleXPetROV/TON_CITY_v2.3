/**
 * MapSaleSheet — «В продаже: N» on the city map: every business that can be bought right now (the city's presale
 * lots, players' lots, rent offers), cheapest first. A tap flies the map to the lot and opens it — the player does
 * not have to zoom into the whole map to find a free business.
 */
import { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Store, ChevronRight } from 'lucide-react';
import { fill } from '@/lib/translationsMore';
import { tBusiness } from '@/lib/translationsExtra';

const SPR = '/sprites/city';
const TO_SPRITE = { chip_factory: 'chips_factory', logistics: 'logistics_hub', repair_zone: 'repair_shop', cold_storage: 'hydro_cooling' };
const fmt = (v) => Math.round(v || 0).toLocaleString('ru-RU');
const KIND_STYLE = {
  city: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/40',
  market: 'bg-amber-500/15 text-amber-200 border-amber-400/40',
  rent: 'bg-cyan-500/15 text-cyan-200 border-cyan-400/40',
};

export default function MapSaleSheet({ open, onClose, items, onPick, t, lang, viewer, spriteOf }) {
  const [kind, setKind] = useState('all');
  const kinds = useMemo(() => ['city', 'market', 'rent'].filter((k) => items.some((x) => x.sale.kind === k)), [items]);
  const list = useMemo(() => items.filter((x) => kind === 'all' || x.sale.kind === kind)
    .sort((a, b) => (a.sale.kind === 'city' ? 0 : 1) - (b.sale.kind === 'city' ? 0 : 1) || (a.sale.price || 0) - (b.sale.price || 0)), [items, kind]);
  const free = viewer === 'newbie';

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#0d1526] border-emerald-500/30 rounded-2xl p-0 sm:max-w-lg max-h-[86vh] overflow-hidden flex flex-col gap-0" data-testid="map-sale-sheet">
        <div className="p-4 pb-3 border-b border-white/10">
          <DialogTitle className="flex items-center gap-2 text-white text-lg font-black"><Store className="w-5 h-5 text-emerald-400" />{t('ms_title')}</DialogTitle>
          <p className="text-[11px] text-white/55 mt-1">{t('ms_hint')}</p>
          {kinds.length > 1 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {['all', ...kinds].map((k) => (
                <button key={k} type="button" onClick={() => setKind(k)}
                  className={`px-2.5 py-1 rounded-lg border text-[11px] font-bold ${kind === k ? 'bg-emerald-500/20 border-emerald-400/70 text-white' : 'bg-white/[0.04] border-white/10 text-white/60'}`}>
                  {k === 'all' ? `${t('mf_all')} · ${items.length}` : `${t(`mf_src_${k}`)} · ${items.filter((x) => x.sale.kind === k).length}`}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="p-3 space-y-2 overflow-y-auto">
          {!list.length && <div className="py-10 text-center text-sm text-white/50">{t('ms_empty')}</div>}
          {list.map(({ c, sale }) => {
            const b = c.building || {};
            const type = b.type;
            const lvl = b.level || 0;
            const stage = lvl <= 3 ? 1 : lvl <= 6 ? 2 : 3;
            const cityFree = free && sale.kind === 'city';
            return (
              <button key={`${c.q},${c.r}`} type="button" onClick={() => onPick(c)} data-testid={`ms-item-${c.q}-${c.r}`}
                className="w-full flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] active:scale-[0.99] p-2 text-left">
                <div className="w-14 h-14 shrink-0 rounded-lg bg-black/40 flex items-center justify-center overflow-hidden">
                  <img src={(spriteOf && spriteOf(c)) || `${SPR}/${TO_SPRITE[type] || type}/stage${stage}.webp`} alt="" className="max-w-full max-h-full object-contain" loading="lazy"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-white truncate">{tBusiness(type, lang) || type}</div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[10px]">
                    <span className={`px-1.5 py-0.5 rounded-md border font-bold ${KIND_STYLE[sale.kind] || KIND_STYLE.city}`}>{t(`mf_src_${sale.kind}`)}</span>
                    {c.district != null && <span className="text-white/50">{fill(t('mf_district_n'), { n: c.district })}</span>}
                    <span className="text-white/40">T{b.tier || 1} · {(c.w || 1)}×{(c.h || 1)}</span>
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  {cityFree ? (
                    <>
                      <div className="text-[11px] text-white/40 line-through">{fmt(sale.price)}</div>
                      <div className="text-sm font-black text-emerald-300">0 $CITY</div>
                      <div className="text-[10px] text-emerald-200/70">{t('ms_lvl0')}</div>
                    </>
                  ) : (
                    <div className="text-sm font-black text-emerald-300 whitespace-nowrap">{fmt(sale.price)} <span className="text-[10px] text-white/50">$CITY</span></div>
                  )}
                </div>
                <ChevronRight className="w-4 h-4 text-white/30 shrink-0" />
              </button>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
