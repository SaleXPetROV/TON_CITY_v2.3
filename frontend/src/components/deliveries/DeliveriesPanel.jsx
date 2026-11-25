/** Contracts → «Грузы в пути»: the trucks of my contracts on the road, when they arrive (a live countdown), the cargo
 *  waiting at the gate, and the paid «Доставить сейчас». Shown inside «Закупки» (side="in": coming to me) and inside
 *  «Поставки» (side="out": going from me). Server: backend/deliveries.py (/api/deliveries/my). */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Truck } from 'lucide-react';
import { getResource } from '@/lib/resourceConfig';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const L = {
  ru: { card: 'Ваш грузовик', title: 'Грузы в пути', toYou: 'к вам от @{n}', fromYou: 'от вас к @{n}', eta: 'прибудет через {t}', now: 'подъезжает', dark: 'едет медленнее: тёмный район (×{k})', waiting: 'ждёт у ворот — освободите склад ({n} не помещается)', speed: 'Доставить сейчас · {p} $CITY', done: 'Груз доставлен', noMoney: 'Не хватает $CITY', cannot: 'Груз уже прибыл', h: 'ч', m: 'мин', s: 'сек', confirm: 'Доставить груз сейчас за {p} $CITY?' },
  en: { card: 'Your truck', title: 'Cargo on the road', toYou: 'to you from @{n}', fromYou: 'from you to @{n}', eta: 'arrives in {t}', now: 'arriving', dark: 'driving slower: a dark district (×{k})', waiting: 'waiting at the gate — free some room ({n} don’t fit)', speed: 'Deliver now · {p} $CITY', done: 'Cargo delivered', noMoney: 'Not enough $CITY', cannot: 'The cargo has already arrived', h: 'h', m: 'min', s: 's', confirm: 'Deliver the cargo now for {p} $CITY?' },
  es: { card: 'Tu camión', title: 'Carga en camino', toYou: 'para ti de @{n}', fromYou: 'de ti para @{n}', eta: 'llega en {t}', now: 'llegando', dark: 'va más lento: distrito a oscuras (×{k})', waiting: 'espera en la puerta — libera espacio ({n} no caben)', speed: 'Entregar ahora · {p} $CITY', done: 'Carga entregada', noMoney: 'No hay suficientes $CITY', cannot: 'La carga ya llegó', h: 'h', m: 'min', s: 's', confirm: '¿Entregar la carga ahora por {p} $CITY?' },
  zh: { card: '你的货车', title: '在途货物', toYou: '来自 @{n}', fromYou: '发往 @{n}', eta: '{t}后到达', now: '即将到达', dark: '减速行驶：停电区（×{k}）', waiting: '在门口等待——请腾出仓库（{n} 放不下）', speed: '立即送达 · {p} $CITY', done: '货物已送达', noMoney: '$CITY 不足', cannot: '货物已到达', h: '小时', m: '分钟', s: '秒', confirm: '花 {p} $CITY 立即送达？' },
  fr: { card: 'Votre camion', title: 'Cargaisons en route', toYou: 'pour vous de @{n}', fromYou: 'de vous pour @{n}', eta: 'arrive dans {t}', now: 'en approche', dark: 'roule plus lentement : quartier éteint (×{k})', waiting: 'attend au portail — libérez de la place ({n} ne rentrent pas)', speed: 'Livrer maintenant · {p} $CITY', done: 'Cargaison livrée', noMoney: 'Pas assez de $CITY', cannot: 'La cargaison est déjà arrivée', h: 'h', m: 'min', s: 's', confirm: 'Livrer la cargaison maintenant pour {p} $CITY ?' },
  de: { card: 'Dein Lkw', title: 'Ladungen unterwegs', toYou: 'an dich von @{n}', fromYou: 'von dir an @{n}', eta: 'kommt in {t}', now: 'fährt vor', dark: 'fährt langsamer: dunkler Bezirk (×{k})', waiting: 'wartet am Tor — mach Platz ({n} passen nicht)', speed: 'Jetzt liefern · {p} $CITY', done: 'Ladung geliefert', noMoney: 'Nicht genug $CITY', cannot: 'Die Ladung ist schon da', h: 'Std.', m: 'Min.', s: 'Sek.', confirm: 'Ladung jetzt für {p} $CITY liefern?' },
  ja: { card: 'あなたのトラック', title: '輸送中の荷物', toYou: '@{n} からあなたへ', fromYou: 'あなたから @{n} へ', eta: '{t}後に到着', now: 'まもなく到着', dark: '減速走行中：停電中の地区（×{k}）', waiting: '門で待機中——倉庫を空けてください（{n} が入りません）', speed: '今すぐ配達 · {p} $CITY', done: '荷物が届きました', noMoney: '$CITY が足りません', cannot: '荷物はもう届いています', h: '時間', m: '分', s: '秒', confirm: '{p} $CITY で今すぐ配達しますか？' },
  ko: { card: '내 트럭', title: '이동 중인 화물', toYou: '@{n} → 나', fromYou: '나 → @{n}', eta: '{t} 후 도착', now: '곧 도착', dark: '감속 주행: 어두운 구역 (×{k})', waiting: '문 앞 대기 — 창고를 비우세요 ({n} 들어가지 않음)', speed: '지금 배송 · {p} $CITY', done: '화물 배송 완료', noMoney: '$CITY 부족', cannot: '화물이 이미 도착함', h: '시간', m: '분', s: '초', confirm: '{p} $CITY로 지금 배송할까요?' },
  id: { card: 'Truk Anda', title: 'Muatan di jalan', toYou: 'untukmu dari @{n}', fromYou: 'darimu untuk @{n}', eta: 'tiba dalam {t}', now: 'segera tiba', dark: 'melaju lebih lambat: distrik gelap (×{k})', waiting: 'menunggu di gerbang — kosongkan gudang ({n} tidak muat)', speed: 'Kirim sekarang · {p} $CITY', done: 'Muatan terkirim', noMoney: '$CITY tidak cukup', cannot: 'Muatan sudah tiba', h: 'j', m: 'mnt', s: 'dtk', confirm: 'Kirim muatan sekarang seharga {p} $CITY?' },
};
const f = (s, v) => Object.entries(v || {}).reduce((a, [k, x]) => a.split(`{${k}}`).join(String(x)), s);

/** onlyId → the card of one truck (a tap on it on the map): a bottom sheet with a close button. */
export default function DeliveriesPanel({ lang, token, side, onlyId, onClose, onChanged }) {
  const T = L[lang] || L.en;
  const [rows, setRows] = useState([]);
  const [skew, setSkew] = useState(0);              // server clock − my clock
  const [busy, setBusy] = useState(null);
  const [k, setK] = useState(1.5);                  // a dark street takes k× as long
  const [, setTick] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const load = useCallback(() => {
    const tk = token || localStorage.getItem('token'); if (!tk) return;
    axios.get(`${API}/deliveries/my`, { headers: { Authorization: `Bearer ${tk}` } }).then((r) => {
      setRows((r.data.shipments || []).filter((x) => (x.status === 'in_transit' || x.status === 'waiting_room') && (!side || x.side === side)
        && (!onlyId || x.id === onlyId)));
      setLoaded(true);
      if (r.data.settings?.blackout_slowdown) setK(r.data.settings.blackout_slowdown);
      if (r.data.server_now) setSkew(new Date(r.data.server_now).getTime() - Date.now());
    }).catch(() => {});
  }, [token, side, onlyId]);
  useEffect(() => { load(); const id = setInterval(load, onlyId ? 15000 : 30000); return () => clearInterval(id); }, [load, onlyId]);
  // a live countdown: once a second, only while a truck of this list is on the road
  const moving = rows.some((x) => x.status === 'in_transit');
  useEffect(() => {
    if (!moving) return undefined;
    const id = setInterval(() => { if (!document.hidden) setTick((x) => x + 1); }, 1000);
    return () => clearInterval(id);
  }, [moving]);
  if (onlyId && loaded && !rows.length) {            // it has arrived meanwhile
    return (
      <div className="fixed inset-x-3 bottom-24 z-[60] mx-auto max-w-md rounded-xl border border-emerald-400/40 bg-zinc-950/95 p-3 text-sm text-emerald-200 flex items-center justify-between" data-testid="truck-card">
        <span>✅ {T.done}</span>
        <button type="button" onClick={onClose} className="min-w-[34px] min-h-[34px] text-zinc-300" aria-label="close" data-testid="truck-card-close">✕</button>
      </div>
    );
  }
  if (!rows.length) return null;
  // more than 60 min left → hours and minutes; otherwise minutes and seconds
  const left = (iso) => {
    const sec = Math.floor((new Date(iso).getTime() - (Date.now() + skew)) / 1000);
    if (sec <= 0) return null;
    if (sec > 3600) {
      const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60);
      return `${h} ${T.h} ${String(m).padStart(2, '0')} ${T.m}`;
    }
    const m = Math.floor(sec / 60), s2 = sec % 60;
    return m ? `${m} ${T.m} ${String(s2).padStart(2, '0')} ${T.s}` : `${s2} ${T.s}`;
  };
  const speed = async (x) => {
    if (!window.confirm(f(T.confirm, { p: Math.round(x.speedup_price) }))) return;
    setBusy(x.id);
    try {
      await axios.post(`${API}/deliveries/${x.id}/speedup`, {}, { headers: { Authorization: `Bearer ${token || localStorage.getItem('token')}` } });
      toast.success(T.done); load(); if (onChanged) onChanged();
    } catch (e) {
      const c = e.response?.data?.detail?.code;
      toast.error(c === 'no_money' ? T.noMoney : c === 'cannot' ? T.cannot : 'Error');
    } finally { setBusy(null); }
  };
  return (
    <div className={onlyId
      ? 'fixed inset-x-3 bottom-24 z-[60] mx-auto max-w-md rounded-xl border border-amber-400/40 bg-zinc-950/95 backdrop-blur p-3 space-y-2 shadow-2xl'
      : 'rounded-xl border border-amber-400/30 bg-amber-500/5 p-3 space-y-2'} data-testid={onlyId ? 'truck-card' : 'deliveries-panel'}>
      <div className="flex items-center gap-2 text-amber-200 text-sm font-bold"><Truck className="w-4 h-4" /> {onlyId ? T.card : `${T.title} · ${rows.length}`}
        {onlyId && <button type="button" onClick={onClose} className="ml-auto min-w-[34px] min-h-[34px] text-zinc-300" aria-label="close" data-testid="truck-card-close">✕</button>}
      </div>
      {rows.map((x) => {
        const r = getResource(x.resource, lang) || {};
        const t = left(x.arrives_at);
        return (
          <div key={x.id} className="rounded-lg bg-zinc-950/60 p-2.5 text-xs space-y-1.5" data-testid={`shipment-${x.id}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-white font-semibold">{r.icon} {Math.round(x.qty)} {r.name || x.res_name}</span>
              <span className="text-zinc-400">{x.side === 'in' ? f(T.toYou, { n: x.seller_name }) : f(T.fromYou, { n: x.buyer_name })}</span>
            </div>
            <div className={x.status === 'waiting_room' ? 'text-amber-300' : 'text-zinc-300'}>
              {x.status === 'waiting_room' ? f(T.waiting, { n: Math.round(x.qty_left) })
                : <span className="tabular-nums" data-testid={`eta-${x.id}`}>{t ? f(T.eta, { t }) : T.now}</span>}
            </div>
            {x.status === 'in_transit' && x.slow && <div className="text-amber-300">🌑 {f(T.dark, { k: String(k).replace('.', lang === 'en' || lang === 'zh' || lang === 'ja' || lang === 'ko' ? '.' : ',') })}</div>}
            {x.status === 'in_transit' && x.speedup_price != null && (
              <button type="button" disabled={busy === x.id} onClick={() => speed(x)}
                className="w-full min-h-[34px] rounded-lg bg-amber-400 text-zinc-950 font-bold disabled:opacity-50" data-testid={`speedup-${x.id}`}>
                {f(T.speed, { p: Math.round(x.speedup_price) })}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
