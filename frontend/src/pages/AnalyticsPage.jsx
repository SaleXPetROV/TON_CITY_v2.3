/**
 * AnalyticsPage — «Аналитика» of the resource market (backend/market_analytics.py).
 *   /analytics             — trends (rising / falling / high demand / traded the most), market map (bubbles:
 *                            price change × volume × deals, colour = tier), the table of every resource.
 *   /analytics/:resourceId — one resource: key numbers, price & volume over time, what is on sale now,
 *                            deal history with nicknames, the production chain, «Купить» / «Продать».
 * Period: 24 h / 7 days / 30 days. Deals between linked accounts are listed but not counted.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, CartesianGrid, ReferenceLine,
  LineChart, Line, BarChart, Bar, Cell,
} from 'recharts';
import { BarChart3, RefreshCw, ArrowLeft, TrendingUp, TrendingDown, Flame, Activity, ShoppingCart, Tag } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import PageHeader from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslation } from '@/lib/translations';
import { fill } from '@/lib/translationsMore';
import { getResource } from '@/lib/resourceConfig';
import ProductionChain from '@/components/ProductionChain';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const tok = () => localStorage.getItem('token') || localStorage.getItem('ton_city_token');
// tier colours of the charts (validated: CVD-safe on the dark surface)
const TIER_COLOR = { 1: '#199e70', 2: '#3987e5', 3: '#d95926' };
const TIER_TEXT = { 1: 'text-green-300', 2: 'text-blue-300', 3: 'text-amber-300' };
const GRID = 'rgba(255,255,255,0.07)';
const AXIS = { fill: 'rgba(255,255,255,0.55)', fontSize: 10 };
// numbers and dates in the player's language
const LOCALES = { en: 'en-US', ru: 'ru-RU', es: 'es-ES', zh: 'zh-CN', fr: 'fr-FR', de: 'de-DE', ja: 'ja-JP', ko: 'ko-KR', id: 'id-ID' };
let LOC = 'ru-RU';
const num = (v, d = 2) => (v === null || v === undefined ? '—' : Number(v).toLocaleString(LOC, { maximumFractionDigits: d }));
const city = (v, d = 2) => (v === null || v === undefined ? '—' : `${num(v, d)} $CITY`);
const short = (v) => {
  const n = Number(v || 0);
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return `${Math.round(n)}`;
};
const pct = (v) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${num(v, 1)}%`);
const pctClass = (v) => (v > 0 ? 'text-emerald-300' : v < 0 ? 'text-rose-300' : 'text-white/60');

function Periods({ value, onChange, t }) {
  return (
    <div className="flex gap-1.5" data-testid="an-periods">
      {['24h', '7d', '30d'].map((p) => (
        <button key={p} type="button" onClick={() => onChange(p)} data-testid={`an-period-${p}`}
          className={`px-3 h-8 rounded-lg text-xs font-bold border transition-colors ${value === p ? 'bg-cyber-cyan/20 border-cyber-cyan/60 text-white' : 'bg-white/5 border-white/10 text-white/60'}`}>
          {t(`an_${p}`)}
        </button>
      ))}
    </div>
  );
}

function Tile({ label, value, sub, cls = '' }) {
  return (
    <div className="rounded-xl bg-white/[0.04] border border-white/10 p-2.5 min-w-0">
      <div className="text-[10px] uppercase tracking-wide text-text-muted truncate">{label}</div>
      <div className={`text-base sm:text-lg font-bold text-white mt-0.5 truncate ${cls}`}>{value}</div>
      {sub && <div className="text-[10px] text-text-muted truncate">{sub}</div>}
    </div>
  );
}

function ChipRes({ id, lang, onClick, extra }) {
  const r = getResource(id, lang);
  return (
    <button type="button" onClick={() => onClick(id)}
      className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs border ${r.tier === 3 ? 'res-legendary text-white' : 'bg-white/5 border-white/10 text-white/85'} hover:brightness-125`}>
      <span>{r.icon}</span><span>{r.name}</span>{extra && <span className="text-[10px] opacity-80">{extra}</span>}
    </button>
  );
}

function ChartTip({ active, payload, render }) {
  if (!active || !payload || !payload.length) return null;
  return <div className="rounded-lg bg-[#0b1020]/95 border border-white/15 px-2.5 py-1.5 text-[11px] text-white shadow-xl">{render(payload[0].payload)}</div>;
}

// ───────────────────────────── overview ─────────────────────────────
function Overview({ data, lang, t, open }) {
  const [tier, setTier] = useState(0);
  const [sort, setSort] = useState({ k: 'volume_city', d: -1 });
  const rows = useMemo(() => {
    const list = (data?.resources || []).filter((r) => !tier || r.tier === tier);
    return [...list].sort((a, b) => {
      const va = a[sort.k] ?? -Infinity; const vb = b[sort.k] ?? -Infinity;
      if (sort.k === 'resource') return sort.d * getResource(a.resource, lang).name.localeCompare(getResource(b.resource, lang).name);
      return sort.d * (va - vb);
    });
  }, [data, tier, sort, lang]);
  const bubbles = (data?.resources || []).filter((r) => r.deals > 0 && (!tier || r.tier === tier))
    .map((r) => ({ ...r, x: r.price_change_pct ?? 0, y: Math.max(1, r.volume_city), z: r.deals }));
  const tot = data?.totals || {};
  const volChange = tot.prev_volume_city ? ((tot.volume_city - tot.prev_volume_city) / tot.prev_volume_city) * 100 : null;
  const tr = data?.trends || {};
  const head = (k, label, right) => (
    <th className={`p-1.5 cursor-pointer select-none whitespace-nowrap ${right ? 'text-right' : 'text-left'}`} onClick={() => setSort((s) => ({ k, d: s.k === k ? -s.d : -1 }))}>
      {label}{sort.k === k ? (sort.d < 0 ? ' ↓' : ' ↑') : ''}
    </th>
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <Tile label={t('an_volume')} value={short(tot.volume_city)} sub={volChange === null ? '$CITY' : fill(t('an_vs_prev'), { p: pct(volChange) })} />
        <Tile label={t('an_deals')} value={num(tot.deals, 0)} />
        <Tile label={t('an_lots')} value={num(tot.listed_lots, 0)} />
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3" data-testid="an-trends">
        <div className="text-sm font-bold text-white mb-2">{t('an_trends')}</div>
        <div className="grid sm:grid-cols-2 gap-2.5">
          {[['rising', TrendingUp, 'text-emerald-300', 'price_change_pct'], ['falling', TrendingDown, 'text-rose-300', 'price_change_pct'],
            ['demand', Flame, 'text-amber-300', 'demand_pct'], ['volume', Activity, 'text-cyber-cyan', 'volume_city']].map(([k, Icon, c, field]) => {
            const ids = tr[k] || [];
            const key = k === 'volume' ? 'an_top_volume' : `an_${k}`;
            return (
              <div key={k} className="rounded-xl bg-black/25 border border-white/5 p-2">
                <div className={`flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide ${c}`}><Icon className="w-3.5 h-3.5" />{t(key)}</div>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {ids.length ? ids.map((id) => {
                    const r = (data.resources || []).find((x) => x.resource === id) || {};
                    const extra = field === 'volume_city' ? short(r.volume_city) : field === 'demand_pct' ? `${num(r.demand_pct, 0)}%` : pct(r[field]);
                    return <ChipRes key={id} id={id} lang={lang} onClick={open} extra={extra} />;
                  }) : <span className="text-xs text-text-muted">{t('an_none')}</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5" data-testid="an-tier-filter">
        {[0, 1, 2, 3].map((n) => (
          <button key={n} type="button" onClick={() => setTier(n)}
            className={`px-3 h-8 rounded-lg text-xs font-bold border ${tier === n ? 'bg-white/15 border-white/40 text-white' : 'bg-white/5 border-white/10 text-white/60'}`}>
            {n ? <span className="inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full" style={{ background: TIER_COLOR[n] }} />{fill(t('mf_tier_n'), { n })}</span> : t('an_all')}
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3" data-testid="an-bubbles">
        <div className="text-sm font-bold text-white">{t('an_bubbles')}</div>
        <div className="text-[11px] text-text-muted mb-2">{t('an_bubbles_hint')} {t('an_tier_legend')}.</div>
        {bubbles.length === 0 ? <div className="text-xs text-text-muted py-10 text-center">{t('an_no_data')}</div> : (
          <div className="h-[280px] sm:h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 16, right: 16, bottom: 18, left: 0 }}>
                <CartesianGrid stroke={GRID} />
                <XAxis type="number" dataKey="x" name={t('an_change')} tick={AXIS} stroke={GRID} tickFormatter={(v) => `${v}%`}
                  label={{ value: t('an_price_change'), position: 'insideBottom', offset: -10, fill: 'rgba(255,255,255,0.45)', fontSize: 10 }} />
                <YAxis type="number" dataKey="y" scale="log" domain={['auto', 'auto']} tick={AXIS} stroke={GRID} tickFormatter={short} width={44} />
                <ZAxis type="number" dataKey="z" range={[220, 1600]} />
                <ReferenceLine x={0} stroke="rgba(255,255,255,0.25)" />
                <Tooltip cursor={false} content={<ChartTip render={(p) => (
                  <div className="space-y-0.5">
                    <div className="font-bold">{getResource(p.resource, lang).icon} {getResource(p.resource, lang).name}</div>
                    <div>{t('an_volume')}: {city(p.volume_city, 0)}</div>
                    <div>{t('an_change')}: {pct(p.price_change_pct)}</div>
                    <div>{t('an_deals')}: {p.deals}</div>
                  </div>
                )} />} />
                <Scatter data={bubbles} onClick={(p) => open(p.resource)} cursor="pointer"
                  shape={(props) => {
                    const { cx, cy, payload } = props;
                    const r = Math.sqrt(props.size || 300) / 2;
                    return (
                      <g data-testid={`an-bubble-${payload.resource}`}>
                        <circle cx={cx} cy={cy} r={r} fill={TIER_COLOR[payload.tier]} fillOpacity={0.35} stroke={TIER_COLOR[payload.tier]} strokeWidth={2} />
                        <text x={cx} y={cy + 5} textAnchor="middle" fontSize={Math.max(12, Math.min(20, r))}>{getResource(payload.resource, lang).icon}</text>
                      </g>
                    );
                  }} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3" data-testid="an-table">
        <div className="text-sm font-bold text-white mb-2">{t('an_table')}</div>
        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-xs min-w-[560px]">
            <thead className="text-text-muted"><tr>
              {head('resource', t('an_res'))}{head('avg_city', t('an_price'), true)}{head('price_change_pct', t('an_change'), true)}
              {head('volume_city', t('an_volume'), true)}{head('demand_pct', t('an_demand_col'), true)}{head('listed_units', t('an_supply'), true)}
            </tr></thead>
            <tbody>
              {rows.map((r) => {
                const res = getResource(r.resource, lang);
                return (
                  <tr key={r.resource} onClick={() => open(r.resource)} className="border-t border-white/5 cursor-pointer hover:bg-white/[0.04]" data-testid={`an-row-${r.resource}`}>
                    <td className="p-1.5"><span className="inline-flex items-center gap-1.5">
                      <span className={`w-7 h-7 rounded-lg flex items-center justify-center ${res.tier === 3 ? 'res-legendary' : 'bg-white/5'}`}>{res.icon}</span>
                      <span className={`font-semibold ${TIER_TEXT[res.tier]}`}>{res.name}</span></span></td>
                    <td className="p-1.5 text-right text-white whitespace-nowrap">{r.avg_city ? num(r.avg_city) : <span className="text-white/40">{num(r.min_listed_city)}</span>}</td>
                    <td className={`p-1.5 text-right whitespace-nowrap ${pctClass(r.price_change_pct)}`}>{pct(r.price_change_pct)}</td>
                    <td className="p-1.5 text-right whitespace-nowrap">{r.volume_city ? short(r.volume_city) : '—'}<div className="text-[10px] text-text-muted">{r.deals ? `${r.deals} · ${num(r.units, 0)} ${t('an_units')}` : ''}</div></td>
                    <td className="p-1.5 text-right whitespace-nowrap">{r.demand_pct === null || r.demand_pct === undefined ? '—' : `${num(r.demand_pct, 0)}%`}</td>
                    <td className="p-1.5 text-right whitespace-nowrap">{r.listed_units ? num(r.listed_units, 0) : '—'}<div className="text-[10px] text-text-muted">{r.listed_lots ? fill(t('an_lots_n'), { n: r.listed_lots }) : ''}</div></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="text-[10px] text-text-muted mt-2">{t('an_demand_hint')}</div>
      </div>
    </div>
  );
}

// ───────────────────────────── one resource ─────────────────────────────
function ResourceView({ data, lang, t, period, navigate, onResource }) {
  const res = getResource(data.resource, lang);
  const color = TIER_COLOR[data.tier] || TIER_COLOR[1];
  const s = data.summary || {};
  const fmtT = (iso) => {
    const d = new Date(iso);
    return period === '24h' ? d.toLocaleTimeString(LOC, { hour: '2-digit', minute: '2-digit' })
      : d.toLocaleDateString(LOC, { day: '2-digit', month: '2-digit' }) + (period === '7d' ? ` ${d.getHours()}:00` : '');
  };
  const series = data.series || [];
  const hasDeals = series.some((x) => x.deals);
  const stateBuy = data.state && data.state.buys ? data.state.buy_city : null;
  const maxBook = Math.max(1, ...(data.book || []).map((b) => b.units));
  const minListed = (data.book || [])[0]?.price_city;
  const srcLabel = (d, side) => {
    const n = side === 'b' ? d.buyer_name : d.seller_name;
    if ((side === 'b' && d.source === 'city_buy') || (side === 's' && d.source === 'city_sell')) return `🏙 ${t('an_src_city')}`;
    return n ? `@${n}` : '—';
  };

  return (
    <div className="space-y-4" data-testid="an-resource">
      <div className="flex items-center gap-3">
        <div className={`w-14 h-14 rounded-xl flex items-center justify-center text-3xl shrink-0 ${data.tier === 3 ? 'res-legendary' : 'bg-white/5 border border-white/10'}`}>{res.icon}</div>
        <div className="min-w-0 flex-1">
          <div className="text-lg font-black text-white truncate">{res.name}</div>
          <div className={`text-xs ${TIER_TEXT[data.tier]}`}>{fill(t('mf_tier_n'), { n: data.tier })}</div>
        </div>
        <div className="flex gap-1.5 shrink-0">
          <Button size="sm" className="bg-cyber-cyan text-black hover:bg-cyber-cyan/80 h-9" onClick={() => navigate(`/trading?resource=${data.resource}`)} data-testid="an-buy"><ShoppingCart className="w-4 h-4 mr-1" />{t('an_buy')}</Button>
          <Button size="sm" variant="outline" className="border-white/15 h-9" onClick={() => navigate(`/trading?tab=my&sell=${data.resource}`)} data-testid="an-sell"><Tag className="w-4 h-4 mr-1" />{t('an_sell')}</Button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Tile label={t('an_avg_price')} value={city(s.avg_city)} sub={t('an_per_unit')} />
        <Tile label={t('an_last_price')} value={city(s.last_city)} sub={t('an_per_unit')} />
        <Tile label={t('an_min_listed')} value={city(minListed)} sub={t('an_per_unit')} />
        <Tile label={t('an_state')} value={stateBuy ? city(stateBuy) : '—'} sub={stateBuy ? t('an_per_unit') : t('an_state_no')} />
        <Tile label={t('an_volume')} value={short(s.volume_city)} sub="$CITY" />
        <Tile label={t('an_deals')} value={num(s.deals, 0)} sub={`${num(s.units, 0)} ${t('an_units')}`} />
        <Tile label={t('an_supply')} value={num((data.book || []).reduce((a, b) => a + b.units, 0), 0)} sub={fill(t('an_lots_n'), { n: (data.book || []).reduce((a, b) => a + b.lots, 0) })} />
        <Tile label={t('an_producers')} value={num(data.producers, 0)} />
      </div>

      <div className="grid lg:grid-cols-2 gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3" data-testid="an-price-chart">
          <div className="text-sm font-bold text-white mb-2">{t('an_price_chart')}</div>
          {!hasDeals ? <div className="text-xs text-text-muted py-10 text-center">{t('an_no_data')}</div> : (
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={GRID} vertical={false} />
                  <XAxis dataKey="t" tickFormatter={fmtT} tick={AXIS} stroke={GRID} minTickGap={24} />
                  <YAxis tick={AXIS} stroke={GRID} width={48} tickFormatter={(v) => num(v, v < 10 ? 2 : 0)} domain={['auto', 'auto']} />
                  {stateBuy && <ReferenceLine y={stateBuy} stroke="rgba(255,255,255,0.45)" strokeDasharray="4 4"
                    label={{ value: t('an_state_line'), position: 'insideTopRight', fill: 'rgba(255,255,255,0.6)', fontSize: 10 }} />}
                  <Tooltip cursor={{ stroke: 'rgba(255,255,255,0.3)' }} content={<ChartTip render={(p) => (
                    <div><div className="text-white/60">{new Date(p.t).toLocaleString(LOC)}</div>
                      <div>{t('an_avg_price')}: <b>{city(p.avg_city)}</b></div>
                      {p.deals > 0 && <div className="text-white/70">{num(p.min_city)} – {num(p.max_city)} · {p.deals} {t('an_deals').toLowerCase()}</div>}</div>
                  )} />} />
                  <Line type="monotone" dataKey="avg_city" stroke={color} strokeWidth={2} dot={{ r: 3, fill: color, stroke: '#0b1020', strokeWidth: 2 }} connectNulls isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3" data-testid="an-volume-chart">
          <div className="text-sm font-bold text-white mb-2">{t('an_volume_chart')}</div>
          {!hasDeals ? <div className="text-xs text-text-muted py-10 text-center">{t('an_no_data')}</div> : (
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={series} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={GRID} vertical={false} />
                  <XAxis dataKey="t" tickFormatter={fmtT} tick={AXIS} stroke={GRID} minTickGap={24} />
                  <YAxis tick={AXIS} stroke={GRID} width={48} tickFormatter={short} />
                  <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} content={<ChartTip render={(p) => (
                    <div><div className="text-white/60">{new Date(p.t).toLocaleString(LOC)}</div>
                      <div>{t('an_volume')}: <b>{city(p.volume_city, 0)}</b></div>
                      <div className="text-white/70">{num(p.units, 0)} {t('an_units')} · {p.deals} {t('an_deals').toLowerCase()}</div></div>
                  )} />} />
                  <Bar dataKey="volume_city" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                    {series.map((x, i) => <Cell key={i} fill={color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3" data-testid="an-book">
          <div className="text-sm font-bold text-white mb-2">{t('an_book')}</div>
          {(data.book || []).length === 0 ? <div className="text-xs text-text-muted py-4">—</div> : (
            <div className="space-y-1">
              {data.book.map((b) => (
                <div key={b.price_city} className="relative rounded-md overflow-hidden text-xs">
                  <div className="absolute inset-y-0 left-0 rounded-md opacity-25" style={{ width: `${(b.units / maxBook) * 100}%`, background: color }} />
                  <div className="relative flex justify-between px-2 py-1">
                    <span className="text-white font-semibold">{city(b.price_city)}</span>
                    <span className="text-white/75">{num(b.units, 0)} {t('an_units')} · {fill(t('an_lots_n'), { n: b.lots })}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <ProductionChain resource={data.resource} lang={lang} t={t} onResource={onResource} testid="an-chain" />
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3" data-testid="an-history">
        <div className="text-sm font-bold text-white mb-2">{t('an_history')}</div>
        {(data.deals || []).length === 0 ? <div className="text-xs text-text-muted py-4">{t('an_no_data')}</div> : (
          <div className="overflow-x-auto -mx-1 max-h-96 overflow-y-auto">
            <table className="w-full text-xs min-w-[560px]">
              <thead className="text-text-muted sticky top-0 bg-[#0b1020]"><tr className="text-left">
                <th className="p-1.5">{t('an_when')}</th><th className="p-1.5">{t('an_seller')}</th><th className="p-1.5">{t('an_buyer')}</th>
                <th className="p-1.5 text-right">{t('an_qty')}</th><th className="p-1.5 text-right">{t('an_price')}</th><th className="p-1.5 text-right">{t('an_sum')}</th>
              </tr></thead>
              <tbody>
                {data.deals.map((d, i) => (
                  <tr key={i} className={`border-t border-white/5 ${d.linked ? 'opacity-50' : ''}`} title={d.linked ? t('an_linked') : undefined}>
                    <td className="p-1.5 whitespace-nowrap text-white/70">{new Date(d.ts).toLocaleString(LOC, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                      {(d.source === 'tender' || d.source === 'supply') && <span className="ml-1 text-[10px] text-purple-300">{t(d.source === 'tender' ? 'an_src_tender' : 'an_src_supply')}</span>}</td>
                    <td className="p-1.5 truncate max-w-[130px]">{srcLabel(d, 's')}</td>
                    <td className="p-1.5 truncate max-w-[130px]">{srcLabel(d, 'b')}</td>
                    <td className="p-1.5 text-right">{num(d.units, 2)}</td>
                    <td className="p-1.5 text-right whitespace-nowrap">{num(d.price_city)}</td>
                    <td className="p-1.5 text-right whitespace-nowrap text-white">{num(d.total_city, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AnalyticsPage({ user }) {
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  LOC = LOCALES[lang] || 'en-US';
  const navigate = useNavigate();
  const { resourceId } = useParams();
  const [period, setPeriod] = useState(resourceId ? '7d' : '24h');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = resourceId ? `${API}/analytics/resource/${encodeURIComponent(resourceId)}?period=${period}` : `${API}/analytics/overview?period=${period}`;
      const r = await fetch(url, { headers: { Authorization: `Bearer ${tok()}` } });
      setData(r.ok ? await r.json() : { error: true });
    } catch (_) { setData({ error: true }); } finally { setLoading(false); }
  }, [resourceId, period]);
  useEffect(() => { setData(null); load(); }, [load]);
  const open = (id) => navigate(`/analytics/${id}`);

  return (
    <div className="flex h-screen bg-void">
      <Sidebar user={user} />
      <div className="flex-1 overflow-hidden lg:ml-16">
        {/* plain scroller: Radix ScrollArea lets wide tables/charts stretch the page past the phone width */}
        <div className="h-full overflow-y-auto overflow-x-hidden">
          <div className="p-4 lg:px-6 lg:pt-2 pt-0 pb-28 lg:pb-6 space-y-4 max-w-6xl w-full min-w-0" data-testid="analytics-page">
            <PageHeader
              icon={<BarChart3 className="w-6 h-6 lg:w-8 lg:h-8 text-emerald-300" />}
              title={t('an_title')}
              actionButtons={
                <Button onClick={load} variant="outline" size="icon" className="border-white/10 h-8 w-8 sm:h-10 sm:w-10" disabled={loading}>
                  <RefreshCw className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${loading ? 'animate-spin' : ''}`} />
                </Button>
              }
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              {resourceId ? (
                <button type="button" onClick={() => navigate('/analytics')} className="inline-flex items-center gap-1 text-sm text-cyber-cyan hover:underline" data-testid="an-back">
                  <ArrowLeft className="w-4 h-4" />{t('an_back')}
                </button>
              ) : <div className="text-xs text-text-muted">{t('an_sub')}</div>}
              <Periods value={period} onChange={setPeriod} t={t} />
            </div>
            {!data ? <div className="text-sm text-text-muted py-16 text-center">…</div>
              : data.error ? <div className="text-sm text-rose-300 py-16 text-center">{t('fp_err')}</div>
                : resourceId ? <ResourceView data={data} lang={lang} t={t} period={period} navigate={navigate} onResource={open} />
                  : <Overview data={data} lang={lang} t={t} open={open} />}
          </div>
        </div>
      </div>
    </div>
  );
}
