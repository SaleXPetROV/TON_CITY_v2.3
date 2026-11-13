/**
 * ProductionChain — «Цепочка производства» (GET /api/economy/chain, the same config the backend produces with).
 * Focused view for one resource or one business:
 *   «Из чего делается» (input resources + the buildings that make them) → the building → its resource →
 *   «Где нужен» (the buildings that consume it and what they make).
 * «Вся цепочка» opens the whole scheme: tier 1 → 2 → 3 buildings (city sprites) with their resource; tapping a
 * building highlights where its resource comes from and where it goes. Every resource chip opens `onResource`.
 * Used in the business info on the city map and in the resource window (Resources page).
 */
import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, ArrowRight, Workflow, X } from 'lucide-react';
import { getResource } from '@/lib/resourceConfig';
import { tBusiness } from '@/lib/translationsExtra';
import { fill } from '@/lib/translationsMore';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
let chainCache = null;
let chainPromise = null;
export async function loadChain() {
  if (chainCache) return chainCache;
  if (!chainPromise) {
    chainPromise = fetch(`${API}/economy/chain`).then((r) => r.json()).then((d) => { chainCache = d; return d; })
      .catch(() => { chainPromise = null; return null; });
  }
  return chainPromise;
}

const sprite = (code) => `/sprites/city/${code}/stage2.webp`;
const TIER_TEXT = { 1: 'text-green-300', 2: 'text-blue-300', 3: 'text-amber-300' };

function ResChip({ id, lang, onResource, size = 'sm' }) {
  const r = getResource(id, lang);
  const legend = r?.tier === 3;
  return (
    <button type="button" onClick={(e) => { e.stopPropagation(); onResource && onResource(id); }}
      className={`rounded-lg border leading-tight max-w-full ${size === 'xs'
        ? 'flex flex-col items-center gap-0.5 w-full px-1 py-1 text-[10px] text-center'      // full scheme: icon above the name — long words never break
        : `inline-flex items-center gap-1 px-1.5 py-0.5 text-left ${size === 'lg' ? 'text-sm' : 'text-[11px]'}`} ${legend ? 'res-legendary text-white' : 'bg-white/5 border-white/10 text-white/85'} ${onResource ? 'hover:brightness-125' : 'cursor-default'}`}
      data-testid={`chain-res-${id}`}>
      <span className="shrink-0">{r?.icon || '📦'}</span><span className="min-w-0 break-words" lang={lang}>{r?.name || id}</span>
    </button>
  );
}

function BizTile({ b, lang, onResource, dim, active, onClick, small }) {
  return (
    <div onClick={onClick} role={onClick ? 'button' : undefined}
      className={`rounded-xl border p-1.5 flex flex-col items-center gap-1 transition-all ${active ? 'border-cyber-cyan/70 bg-cyber-cyan/10 shadow-[0_0_10px_rgba(0,240,255,0.15)]' : 'border-white/10 bg-white/[0.03]'} ${dim ? 'opacity-25' : ''} ${onClick ? 'cursor-pointer hover:border-white/30' : ''}`}
      data-testid={`chain-biz-${b.code}`}>
      <img src={sprite(b.code)} alt="" className={`${small ? 'w-9 h-9' : 'w-14 h-14'} object-contain`} loading="lazy" />
      <div className={`${small ? 'text-[9px]' : 'text-[10px]'} w-full text-white/80 text-center leading-tight break-words hyphens-auto`} lang={lang}>{tBusiness(b.code, lang)}</div>
      <ResChip id={b.produces} lang={lang} onResource={onResource} size="xs" />
    </div>
  );
}

/** Focused chain for `resource` (or for the resource of `business`). */
export default function ProductionChain({ resource, business, lang, t, onResource, defaultFull = false, testid, hideTitle = false }) {
  const [chain, setChain] = useState(chainCache);
  const [full, setFull] = useState(defaultFull);
  const [pick, setPick] = useState(null);
  useEffect(() => { let a = true; loadChain().then((d) => { if (a && d) setChain(d); }); return () => { a = false; }; }, []);

  const biz = useMemo(() => chain?.businesses || [], [chain]);
  const byCode = useMemo(() => Object.fromEntries(biz.map((b) => [b.code, b])), [biz]);
  const res = resource || byCode[business]?.produces;
  const maker = business ? byCode[business] : biz.find((b) => b.produces === res);
  const users = biz.filter((b) => res && b.consumes && b.consumes[res] !== undefined);
  const tier = getResource(res, lang)?.tier || maker?.tier || 1;

  // whole scheme: what is related to the picked building (inputs up the chain, consumers down the chain)
  const focusCode = pick || maker?.code;
  const related = useMemo(() => {
    const set = new Set();
    if (!focusCode || !byCode[focusCode]) return set;
    const up = (code) => {
      if (set.has(code)) return; set.add(code);
      Object.keys(byCode[code]?.consumes || {}).forEach((r) => biz.filter((x) => x.produces === r).forEach((x) => up(x.code)));
    };
    const down = (code) => {
      const r = byCode[code]?.produces;
      biz.filter((x) => x.consumes && x.consumes[r] !== undefined).forEach((x) => { if (!set.has(x.code)) { set.add(x.code); down(x.code); } });
    };
    up(focusCode); down(focusCode);
    return set;
  }, [focusCode, byCode, biz]);

  if (!chain) return <div className="text-[11px] text-text-muted py-2">…</div>;
  if (!res) return null;

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 space-y-2.5" data-testid={testid || 'production-chain'}>
      {!hideTitle && <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide font-bold text-cyber-cyan"><Workflow className="w-3.5 h-3.5" />{t('ch_title')}</div>}

      {/* made from → building → resource */}
      <div>
        <div className="text-[10px] uppercase tracking-wide text-text-muted mb-1">{t('ch_made_from')}</div>
        {maker && Object.keys(maker.consumes || {}).length ? (
          <div className="flex flex-wrap items-center gap-1.5">
            {Object.keys(maker.consumes).map((r) => {
              const src = biz.find((x) => x.produces === r);
              return (
                <span key={r} className="inline-flex items-center gap-1">
                  {src && <img src={sprite(src.code)} alt={tBusiness(src.code, lang)} title={tBusiness(src.code, lang)} className="w-7 h-7 object-contain" loading="lazy" />}
                  <ResChip id={r} lang={lang} onResource={onResource} />
                </span>
              );
            })}
          </div>
        ) : <div className="text-[11px] text-white/60">{t('ch_no_input')}</div>}
      </div>

      {maker && (
        <div className="flex items-center gap-2 rounded-xl bg-black/30 border border-white/10 p-2">
          <img src={sprite(maker.code)} alt="" className="w-14 h-14 object-contain shrink-0" loading="lazy" />
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase tracking-wide text-text-muted">{t('ch_made_by')}</div>
            <div className="text-sm font-bold text-white leading-tight break-words" lang={lang}>{tBusiness(maker.code, lang)}</div>
            <div className={`text-[10px] ${TIER_TEXT[maker.tier]}`}>{fill(t('mf_tier_n'), { n: maker.tier })}</div>
          </div>
          <ArrowRight className="w-4 h-4 text-white/40 shrink-0" />
          <div className="shrink-0 max-w-[42%] flex justify-end"><ResChip id={res} lang={lang} onResource={onResource} size="lg" /></div>
        </div>
      )}

      <div>
        <div className="text-[10px] uppercase tracking-wide text-text-muted mb-1">{t('ch_used_in')}</div>
        {users.length ? (
          <div className="space-y-1.5">
            {users.map((u) => (
              <div key={u.code} className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-2 py-1.5" data-testid={`chain-user-${u.code}`}>
                <img src={sprite(u.code)} alt="" className="w-10 h-10 object-contain shrink-0" loading="lazy" />
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold text-white leading-tight break-words" lang={lang}>{tBusiness(u.code, lang)}</div>
                  <div className={`text-[10px] ${TIER_TEXT[u.tier]}`}>{fill(t('mf_tier_n'), { n: u.tier })}</div>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-white/35 shrink-0" />
                <div className="shrink-0 max-w-[45%] flex justify-end"><ResChip id={u.produces} lang={lang} onResource={onResource} /></div>
              </div>
            ))}
          </div>
        ) : <div className="text-[11px] text-white/60">{tier === 3 ? t('ch_final') : t('ch_not_used')}</div>}
      </div>

      <button type="button" onClick={() => setFull((v) => !v)} className="w-full h-8 rounded-lg border border-white/10 text-[11px] font-semibold text-white/80 hover:text-white flex items-center justify-center gap-1" data-testid="chain-full-toggle">
        {full ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}{full ? t('ch_hide') : t('ch_full')}
      </button>

      {full && (
        <div data-testid="chain-full">
          <div className="text-[10px] text-text-muted mb-1.5">{t('ch_hint')}</div>
          <div className="grid grid-cols-3 gap-1.5">
            {[1, 2, 3].map((tr) => (
              <div key={tr} className="space-y-1.5">
                <div className={`text-[10px] font-bold text-center ${TIER_TEXT[tr]}`}>{fill(t('mf_tier_n'), { n: tr })}</div>
                {biz.filter((b) => b.tier === tr).map((b) => (
                  <BizTile key={b.code} b={b} lang={lang} onResource={onResource} small
                    active={b.code === focusCode} dim={focusCode && !related.has(b.code)}
                    onClick={() => setPick((p) => (p === b.code ? null : b.code))} />
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


/** Small window with the production chain (city map → business info → «Цепочка производства»). */
export function ProductionChainModal({ business, resource, lang, t, onClose, onResource }) {
  if (!business && !resource) return null;
  return (
    <div className="fixed inset-0 z-[85] bg-black/60 flex items-end sm:items-center justify-center p-3" onClick={onClose} data-testid="chain-modal">
      <div className="w-full max-w-sm rounded-2xl border border-cyber-cyan/30 bg-[#0b1020] shadow-2xl mb-[var(--bottom-nav-h,0px)] sm:mb-0 flex flex-col max-h-[min(72dvh,620px)]"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between gap-2 px-3 pt-3 pb-2 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-1.5 text-sm font-bold text-cyber-cyan"><Workflow className="w-4 h-4" />{t('ch_title')}</div>
          <button type="button" onClick={onClose} className="text-white/60 hover:text-white" aria-label={t('page_close')} data-testid="chain-modal-close"><X className="w-5 h-5" /></button>
        </div>
        <div className="overflow-y-auto p-2.5">
          <ProductionChain business={business} resource={resource} lang={lang} t={t} onResource={onResource} hideTitle testid="chain-modal-body" />
        </div>
      </div>
    </div>
  );
}
