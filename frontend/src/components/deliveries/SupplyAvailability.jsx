/** Before buying a business: can its raw materials be had on the island? (players who make them — for a contract —
 *  and lots on the market). Server: GET /api/deliveries/availability/{type}. */
import { useEffect, useState } from 'react';
import { getResource } from '@/lib/resourceConfig';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const L = {
  ru: { h: 'Сырьё для этого бизнеса', day: '{n}/сут', pl: 'игроки: {n}', lots: 'лотов на рынке: {n}', none: 'сейчас взять негде' },
  en: { h: 'Raw materials for this business', day: '{n}/day', pl: 'players: {n}', lots: 'market lots: {n}', none: 'nowhere to get it now' },
  es: { h: 'Materias primas de este negocio', day: '{n}/día', pl: 'jugadores: {n}', lots: 'lotes en el mercado: {n}', none: 'ahora no se consigue' },
  zh: { h: '这家企业的原料', day: '每天 {n}', pl: '玩家：{n}', lots: '市场挂单：{n}', none: '目前无处可得' },
  fr: { h: 'Matières premières de cette entreprise', day: '{n}/jour', pl: 'joueurs : {n}', lots: 'lots au marché : {n}', none: 'introuvable pour l’instant' },
  de: { h: 'Rohstoffe für dieses Unternehmen', day: '{n}/Tag', pl: 'Spieler: {n}', lots: 'Marktlose: {n}', none: 'gerade nirgends zu bekommen' },
  ja: { h: 'このビジネスの原料', day: '1日 {n}', pl: 'プレイヤー：{n}', lots: '市場の出品：{n}', none: '今は入手先がありません' },
  ko: { h: '이 비즈니스의 원료', day: '하루 {n}', pl: '플레이어: {n}', lots: '시장 매물: {n}', none: '지금은 구할 곳이 없음' },
  id: { h: 'Bahan baku bisnis ini', day: '{n}/hari', pl: 'pemain: {n}', lots: 'lot di pasar: {n}', none: 'saat ini tidak ada sumbernya' },
};
const f = (s, v) => Object.entries(v).reduce((a, [k, x]) => a.split(`{${k}}`).join(String(x)), s);

export default function SupplyAvailability({ type, level = 1, lang }) {
  const [rows, setRows] = useState(null);
  useEffect(() => {
    if (!type) return undefined;
    let alive = true;
    fetch(`${API}/deliveries/availability/${encodeURIComponent(type)}?level=${Math.max(1, level || 1)}&lang=${lang}`)
      .then((r) => (r.ok ? r.json() : null)).then((d) => { if (alive && d) setRows(d.inputs || []); }).catch(() => {});
    return () => { alive = false; };
  }, [type, level, lang]);
  if (!rows || !rows.length) return null;
  const T = L[lang] || L.en;
  return (
    <div className="mt-3 rounded-xl border border-amber-400/30 bg-amber-500/5 p-3 space-y-1.5" data-testid="supply-availability">
      <div className="text-xs font-bold text-amber-200">🚚 {T.h}</div>
      {rows.map((x) => {
        const r = getResource(x.resource, lang) || {};
        const bits = [x.players ? f(T.pl, { n: x.players }) : null,
          x.market_lots ? f(T.lots, { n: x.market_lots }) : null].filter(Boolean);
        return (
          <div key={x.resource} className="text-xs leading-snug">
            <span className="text-white font-semibold">{r.icon} {r.name || x.res_name}</span>
            <span className="text-white/50"> · {f(T.day, { n: Math.round(x.per_day) })}</span>
            <div className={x.ok ? 'text-white/70' : 'text-red-300'}>{x.ok ? bits.join(' · ') : T.none}</div>
          </div>
        );
      })}
    </div>
  );
}
