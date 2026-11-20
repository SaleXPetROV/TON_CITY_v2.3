/** Админка → «Доставка»: грузовики по контрактам — время в пути, платное ускорение (доход проекта), блэкаут, автосмена. */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const H = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
const inp = 'bg-black/40 border border-white/15 rounded-lg px-2.5 py-1.5 text-sm text-white w-28 focus:outline-none focus:border-amber-400/60';
const ST = { in_transit: 'в пути', waiting_room: 'ждёт у ворот (склад полон)', delivered: 'доставлен', lost: 'покупатель удалён' };
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—');
const FIELDS = [
  ['min_per_tile', 'Минут на клетку дороги'], ['min_minutes', 'Доставка не быстрее, мин'], ['max_minutes', 'Доставка не дольше, мин'],
  ['speedup_city_per_min', 'Ускорение: $CITY за минуту'], ['speedup_min_fee', 'Ускорение: минимум, $CITY'],
  ['others_on_map', 'Чужих грузовиков на карте, до'], ['blackout_slowdown', 'Блэкаут: во сколько раз медленнее тёмная улица'],
];

export default function AdminDeliveries() {
  const [data, setData] = useState(null);
  const [s, setS] = useState(null);
  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/deliveries`, H()); setData(r.data); setS((x) => x || r.data.settings); }
    catch (e) { toast.error('Не удалось загрузить доставку'); }
  }, []);
  useEffect(() => { load(); const id = setInterval(load, 20000); return () => clearInterval(id); }, [load]);
  const save = async (patch) => {
    try { const r = await axios.put(`${API}/admin/deliveries/settings`, { ...s, ...(patch || {}) }, H()); setS(r.data); toast.success('Сохранено'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const st = data?.stats || {};
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4" data-testid="admin-deliveries">
      <h2 className="font-unbounded text-lg font-bold text-white">Доставка по контрактам</h2>
      <p className="text-xs text-text-muted max-w-3xl">
        В час поставки по контракту деньги переходят как раньше, а товар уходит со склада поставщика и едет грузовиком по дорогам
        острова к бизнесу покупателя: время = клетки дороги × минуты на клетку (в пределах минимума и максимума). Покупатель или
        поставщик может «Доставить сейчас» за $CITY — эти деньги идут в казну проекта. В блэкаут грузовик стоит, пока его дорога идёт
        через тёмный район. На карте путь видят только покупатель и поставщик, остальные — только грузовик.
      </p>
      {s && (
        <label className="flex items-center gap-3 text-sm text-white font-semibold">
          <input type="checkbox" className="w-4 h-4" checked={!!s.enabled} onChange={(e) => save({ enabled: e.target.checked })} data-testid="admin-deliveries-enabled" />
          Доставка включена
          <span className="text-xs font-normal text-text-muted">{s.enabled ? 'товар по контрактам едет грузовиком' : 'выключено: товар приходит мгновенно, как раньше'}</span>
        </label>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
        {[['В пути', st.in_transit], ['Ждут у ворот', st.waiting], ['Доставлено за сутки', st.delivered_24h], ['Среднее время, мин', st.avg_minutes],
          ['Ускорения за сутки, $CITY', Math.round(st.speedup_24h_city || 0).toLocaleString('ru-RU')],
          ['Ускорения всего, $CITY', Math.round(st.speedup_total_city || 0).toLocaleString('ru-RU')]]
          .map(([k, v]) => <div key={k} className="rounded-xl border border-white/10 p-3"><div className="text-xs text-text-muted">{k}</div><div className="text-white font-bold">{v ?? 0}</div></div>)}
      </div>
      {s && (
        <div className="rounded-xl border border-white/10 p-4">
          <h3 className="font-unbounded text-base font-bold text-white mb-3">Правила</h3>
          <div className="flex flex-wrap gap-4 mb-3 text-sm text-white/85">
            <label className="flex items-center gap-2"><input type="checkbox" checked={!!s.speedup_enabled} onChange={(e) => setS({ ...s, speedup_enabled: e.target.checked })} />Платное ускорение</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={!!s.blackout_delays} onChange={(e) => setS({ ...s, blackout_delays: e.target.checked })} />В блэкаут грузовики едут медленнее по тёмным районам (блэкаут включает только админ)</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={!!s.auto_shift} onChange={(e) => setS({ ...s, auto_shift: e.target.checked })} />Автосмена, если всё сырьё бизнеса покрыто контрактами</label>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {FIELDS.map(([k, label]) => (
              <label key={k} className="text-xs text-white/60 flex flex-col gap-1">{label}
                <input className={inp} type="number" step="any" value={s[k] ?? ''} onChange={(e) => setS({ ...s, [k]: e.target.value })} />
              </label>
            ))}
          </div>
          <button type="button" className="mt-4 px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-white text-sm font-semibold" onClick={() => save()}>Сохранить</button>
        </div>
      )}
      <div className="rounded-xl border border-white/10 p-4 overflow-x-auto">
        <h3 className="font-unbounded text-base font-bold text-white mb-2">Последние доставки</h3>
        {(data?.shipments || []).length ? (
          <table className="w-full text-xs text-white/80">
            <thead><tr className="text-left text-white/50"><th className="py-1 pr-2">Отправлен</th><th className="pr-2">Поставщик → покупатель</th><th className="pr-2">Груз</th><th className="pr-2">В пути, мин</th><th className="pr-2">Прибытие</th><th className="pr-2">Статус</th></tr></thead>
            <tbody>
              {data.shipments.map((x) => (
                <tr key={x.id} className="border-t border-white/5">
                  <td className="py-1 pr-2 whitespace-nowrap">{fmt(x.departed_at)}</td>
                  <td className="pr-2">@{x.seller_name} → @{x.buyer_name}</td>
                  <td className="pr-2">{Math.round(x.qty)} {x.res_name}</td>
                  <td className="pr-2">{x.minutes}{x.delayed_min ? ` (+${Math.round(x.delayed_min)} блэкаут)` : ''}</td>
                  <td className="pr-2 whitespace-nowrap">{fmt(x.delivered_at || x.arrives_at)}</td>
                  <td className="pr-2">{ST[x.status] || x.status}{x.slow || x.dark ? ' · медленнее: тёмный район' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <div className="text-sm text-text-muted">Доставок пока нет.</div>}
      </div>
    </div>
  );
}
