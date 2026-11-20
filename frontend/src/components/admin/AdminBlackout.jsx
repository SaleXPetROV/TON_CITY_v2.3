/** Админка → «События» → «Блэкаут острова»: включение, запуск со своими количествами, ход, правка количеств, настройки, история. */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Play, Square, Flag, Plus, X, Save } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const inp = 'bg-black/40 border border-white/15 rounded-lg px-2.5 py-1.5 text-sm text-white w-28 focus:outline-none focus:border-amber-400/60';
const D = { 1: 'Центральное ядро', 2: 'Северный хаб', 3: 'Западный район', 4: 'Восточный район' };
export const BLACKOUT_RES = { energy: 'Энергия', scrap: 'Металл', quartz: 'Кварц', cu: 'Вычисления', traffic: 'Трафик', cooling: 'Холод', biomass: 'Биомасса',
  chips: 'Чип (эш. 2)', neurocode: 'ИИ-Модель (эш. 2)', nft: 'NFT-Арт (эш. 2)', vr_experience: 'VR-Контент (эш. 2)', logistics: 'Топливо (эш. 2)',
  profit_ton: 'Кибер-фуд (эш. 2)', repair_kits: 'Ремкомплект (эш. 2)' };
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—');
const STATUS = { active: 'идёт', won: 'остров зажжён', ended: 'время вышло', cancelled: 'отменён' };

const FIELDS = [
  ['duration_hours', 'Длится, часов'], ['interval_days', 'Автозапуск раз в, дней'],
  ['per_player_units', 'Ед. каждого ресурса на 1 игрока'], ['min_units', 'Но не меньше, ед.'],
  ['reward_pct', 'Награда, % стоимости сданного'], ['refund_pct', 'Возврат, если не успели, %'], ['xp_per_100', 'XP за 100 $CITY'], ['xp_max', 'XP максимум'],
  ['lit_bonus_pct', 'Зажжённый район: +% производства'], ['lit_bonus_days', '…на дней'], ['fail_penalty_pct', 'Тёмный район: −% производства'], ['fail_days', '…на дней'],
  ['top_n', 'Имён на башне'],
];

/** Editable needs: {"1": {"energy": 120, ...}, ...}. `lockedDistricts` — lit districts (not editable). */
function NeedsEditor({ needs, setNeeds, got, locked = {} }) {
  const setQty = (d, r, v) => setNeeds({ ...needs, [d]: { ...needs[d], [r]: v } });
  const remove = (d, r) => { const x = { ...needs[d] }; delete x[r]; setNeeds({ ...needs, [d]: x }); };
  const add = (d, r) => { if (r) setNeeds({ ...needs, [d]: { ...needs[d], [r]: needs[d]?.[r] || 100 } }); };
  const swap = (d, from, to) => {
    if (!to || to === from) return;
    const x = {}; Object.entries(needs[d]).forEach(([k, v]) => { x[k === from ? to : k] = v; });
    setNeeds({ ...needs, [d]: x });
  };
  return (
    <div className="grid sm:grid-cols-2 gap-3" data-testid="bo-needs-editor">
      {[1, 2, 3, 4].map((d) => {
        const dn = needs[String(d)] || {};
        const isLocked = !!locked[String(d)];
        return (
          <div key={d} className={`rounded-xl border p-3 ${isLocked ? 'border-amber-400/30 opacity-70' : 'border-white/10'}`}>
            <div className="flex justify-between text-sm font-semibold text-white mb-2">
              <span>{D[d]}</span>{isLocked && <span className="text-amber-300 text-xs">светится — не меняется</span>}
            </div>
            {Object.entries(dn).map(([r, q]) => (
              <div key={r} className="flex items-center gap-2 mb-1.5">
                <select className={`${inp} w-44`} value={r} disabled={isLocked} onChange={(e) => swap(String(d), r, e.target.value)}>
                  {Object.entries(BLACKOUT_RES).filter(([k]) => k === r || !(k in dn)).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                <input className={inp} type="number" min={1} value={q} disabled={isLocked} onChange={(e) => setQty(String(d), r, e.target.value)} data-testid={`bo-need-${d}-${r}`} />
                {got && <span className="text-[11px] text-white/45 w-20">сдано {got[String(d)]?.[r] ?? 0}</span>}
                {!isLocked && Object.keys(dn).length > 1 && <button className="text-white/40 hover:text-red-300" onClick={() => remove(String(d), r)} title="Убрать"><X className="w-4 h-4" /></button>}
              </div>
            ))}
            {!isLocked && Object.keys(dn).length < 5 && (
              <select className={`${inp} w-44 mt-1 text-white/60`} value="" onChange={(e) => add(String(d), e.target.value)}>
                <option value="">+ ресурс…</option>
                {Object.entries(BLACKOUT_RES).filter(([k]) => !(k in dn)).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function AdminBlackout({ onChange }) {
  const h = { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } };
  const [data, setData] = useState(null);
  const [s, setS] = useState(null);
  const [hours, setHours] = useState('');
  const [plan, setPlan] = useState(null);          // needs being prepared for the start
  const [edit, setEdit] = useState(null);          // needs of the running blackout being edited
  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/admin/blackout`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
      setData(r.data); setS((x) => x || r.data.settings);
      if (onChange) onChange(r.data);
    } catch (e) { toast.error('Не удалось загрузить'); }
  }, [onChange]);
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, [load]);

  const save = async (patch) => {
    const body = { ...s, ...(patch || {}) };
    if (patch && 'enabled' in patch && !patch.enabled && data?.active
      && !window.confirm('Выключить событие? Идущий блэкаут закончится без штрафа, всем вернут 100% сданного.')) return;
    try { const r = await axios.put(`${API}/admin/blackout/settings`, body, h); setS(r.data); toast.success('Сохранено'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const prepare = async () => {
    try { const r = await axios.get(`${API}/admin/blackout/plan`, h); setPlan(r.data); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const startNow = async () => {
    if (!window.confirm('Погасить остров сейчас? Все игроки получат уведомление.')) return;
    try {
      await axios.post(`${API}/admin/blackout/start`, { hours: hours ? Number(hours) : undefined, needs: plan?.needs }, h);
      toast.success('Остров погас'); setPlan(null); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const stop = async (mode) => {
    const q = mode === 'cancel' ? 'Отменить блэкаут? Тёмным районам штрафа не будет, всем вернут 100% сданного.' : 'Завершить сейчас, как будто время вышло? Тёмные районы получат штраф.';
    if (!window.confirm(q)) return;
    try { await axios.post(`${API}/admin/blackout/stop`, { mode }, h); toast.success('Готово'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const saveNeeds = async () => {
    try { await axios.put(`${API}/admin/blackout/needs`, { needs: edit }, h); toast.success('Количества изменены'); setEdit(null); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };

  const a = data?.active;
  const on = !!s?.enabled;
  const per = Number(s?.per_player_units || 0), mn = Number(s?.min_units || 0), pl = data?.players_now || 0;
  return (
    <div className="space-y-4" data-testid="admin-blackout">
      <div className="rounded-xl border border-amber-500/20 p-4 space-y-3">
        <p className="text-xs text-text-muted max-w-3xl">
          Остров гаснет, игроки сдают ресурсы со склада в «городскую сеть», и районы загораются один за другим. Процент у события —
          насколько остров уже зажжён (сколько нужного сдано), а не производство. Производство меняется только после блэкаута:
          зажжённый район +{s?.lit_bonus_pct ?? 5}%, тёмный −{s?.fail_penalty_pct ?? 10}%.
        </p>
        <label className="flex items-center gap-3 text-sm text-white font-semibold">
          <input type="checkbox" className="w-4 h-4" checked={on} onChange={(e) => save({ enabled: e.target.checked })} data-testid="admin-blackout-enabled" />
          Событие включено
          <span className="text-xs font-normal text-text-muted">{on ? 'игроки видят страницу «Блэкаут», можно запускать' : 'выключено: игроки ничего не видят, запустить нельзя, бонусов и штрафов нет'}</span>
        </label>

        {on && !a && !plan && (
          <button className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-sm font-bold flex items-center gap-2" onClick={prepare} data-testid="admin-blackout-prepare">
            <Play className="w-4 h-4" />Подготовить запуск
          </button>
        )}
        {on && !a && plan && (
          <div className="space-y-3" data-testid="admin-blackout-plan">
            <div className="text-xs text-text-muted">
              Количества — <b className="text-white">на весь район, все игроки вместе</b>. Предложено по настройкам: {plan.per_player_units} ед. × {plan.players} игроков
              с бизнесом (но не меньше {plan.min_units}); Ядру — ресурс эшелона 2 поменьше. Поменяйте ресурсы и числа как нужно.
            </div>
            <NeedsEditor needs={plan.needs} setNeeds={(n) => setPlan({ ...plan, needs: n })} />
            <div className="flex flex-wrap items-end gap-3">
              <label className="text-xs text-white/60 flex flex-col gap-1">Часов (пусто — {s?.duration_hours ?? 24})
                <input className={inp} value={hours} onChange={(e) => setHours(e.target.value)} />
              </label>
              <button className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-sm font-bold flex items-center gap-2" onClick={startNow} data-testid="admin-blackout-start">
                <Play className="w-4 h-4" />Погасить остров
              </button>
              <button className="px-3 py-2 rounded-lg bg-white/10 text-white/80 text-sm" onClick={prepare}>Другие ресурсы</button>
              <button className="px-3 py-2 rounded-lg text-white/50 text-sm" onClick={() => setPlan(null)}>Отмена</button>
            </div>
          </div>
        )}
      </div>

      {a && (
        <div className="rounded-xl border border-white/10 p-4" data-testid="admin-blackout-active">
          <div className="flex flex-wrap items-baseline gap-3 mb-3">
            <h3 className="font-unbounded text-base font-bold text-white">Идёт: остров зажжён на {Math.floor(a.pct)}%</h3>
            <span className="text-xs text-text-muted">до {fmt(a.ends_at)} · участников {a.participants} · игроков с бизнесом на старте {a.players}</span>
          </div>
          {edit ? (
            <>
              <div className="text-xs text-text-muted mb-2">Количества на весь район. Если поставить меньше уже сданного — район загорится сразу.</div>
              <NeedsEditor needs={edit} setNeeds={setEdit}
                got={Object.fromEntries(Object.entries(a.districts).map(([d, x]) => [d, x.got]))}
                locked={Object.fromEntries(Object.entries(a.districts).map(([d, x]) => [d, !!x.lit_at]))} />
              <div className="flex gap-2 mt-3">
                <button className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-white text-sm font-semibold flex items-center gap-2" onClick={saveNeeds} data-testid="admin-blackout-save-needs"><Save className="w-4 h-4" />Сохранить количества</button>
                <button className="px-3 py-2 rounded-lg text-white/50 text-sm" onClick={() => setEdit(null)}>Отмена</button>
              </div>
            </>
          ) : (
            <>
              <div className="grid sm:grid-cols-2 gap-3">
                {Object.values(a.districts).map((d) => (
                  <div key={d.id} className="rounded-xl border border-white/10 p-3">
                    <div className="flex justify-between text-sm font-semibold text-white"><span>{D[d.id]}</span><span className={d.lit_at ? 'text-amber-300' : 'text-white/60'}>{d.lit_at ? 'светится' : `${Math.floor(d.pct)}%`}</span></div>
                    {Object.keys(d.need).map((r) => (
                      <div key={r} className="text-xs text-white/70 mt-1">{BLACKOUT_RES[r] || r}: сдано {d.got[r]} из {d.need[r]}</div>
                    ))}
                    {d.heroes?.length > 0 && <div className="text-xs text-amber-300 mt-1">На башне: {d.heroes.map((x) => '@' + x.username).join(', ')}</div>}
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                <button className="px-4 py-2 rounded-lg bg-white/10 text-white text-sm font-semibold" onClick={() => setEdit(Object.fromEntries(Object.entries(a.districts).map(([k, x]) => [k, { ...x.need }])))} data-testid="admin-blackout-edit-needs">Изменить количества</button>
                <button className="px-4 py-2 rounded-lg bg-white/10 text-white text-sm font-semibold flex items-center gap-2" onClick={() => stop('finish')}><Flag className="w-4 h-4" />Завершить сейчас</button>
                <button className="px-4 py-2 rounded-lg bg-red-500/20 text-red-200 text-sm font-semibold flex items-center gap-2" onClick={() => stop('cancel')}><Square className="w-4 h-4" />Отменить без штрафа</button>
              </div>
            </>
          )}
        </div>
      )}

      {s && (
        <div className="rounded-xl border border-white/10 p-4">
          <h3 className="font-unbounded text-base font-bold text-white mb-1">Настройки</h3>
          <p className="text-xs text-text-muted mb-3">
            «Ед. на 1 игрока» — сколько каждого ресурса района приходится на одного игрока с бизнесом; району нужно столько,
            умноженное на число таких игроков: сейчас {per} × {pl} = {(per * pl).toLocaleString('ru-RU')}{per * pl < mn ? `, но не меньше ${mn}` : ''} ед. на ресурс.
            Это количество на всех вместе, а не на каждого. При запуске его можно поправить вручную.
          </p>
          <label className="flex items-center gap-2 text-sm text-white/85 mb-1">
            <input type="checkbox" checked={!!s.auto} disabled={!on} onChange={(e) => setS({ ...s, auto: e.target.checked })} data-testid="admin-blackout-auto" />
            Запускать сам раз в «Автозапуск раз в, дней» (в случайный час, ±10 ч; количества — по настройкам)
          </label>
          {s.auto && s.next_at && <div className="text-xs text-text-muted mb-2">Следующий: примерно {fmt(s.next_at)}</div>}
          <label className="flex items-center gap-2 text-sm text-white/85 mb-3">
            <input type="checkbox" checked={s.telegram !== false} onChange={(e) => setS({ ...s, telegram: e.target.checked })} />
            Сообщать о начале в Telegram игрокам с бизнесом
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {FIELDS.map(([k, label]) => (
              <label key={k} className="text-xs text-white/60 flex flex-col gap-1">{label}
                <input className={inp} type="number" value={s[k] ?? ''} onChange={(e) => setS({ ...s, [k]: e.target.value })} data-testid={`bo-set-${k}`} />
              </label>
            ))}
          </div>
          <button className="mt-4 px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-white text-sm font-semibold" onClick={() => save()}>Сохранить</button>
        </div>
      )}

      <div className="rounded-xl border border-white/10 p-4">
        <h3 className="font-unbounded text-base font-bold text-white mb-3">История</h3>
        {(data?.history || []).length ? (
          <table className="w-full text-xs">
            <thead className="text-white/40 text-left"><tr><th className="py-1">Начало</th><th>Итог</th><th>Зажжено</th><th>Участников</th><th>Сдано ед.</th><th>Стоимость</th><th>Выплачено</th></tr></thead>
            <tbody>
              {data.history.map((e) => (
                <tr key={e.id} className="border-t border-white/5 text-white/85">
                  <td className="py-1.5">{fmt(e.started_at)}</td><td>{STATUS[e.status] || e.status}</td><td>{Math.floor(e.pct)}%</td>
                  <td>{e.participants}</td><td>{e.units}</td><td>{(e.value || 0).toLocaleString('ru-RU')}</td><td>{(e.paid || 0).toLocaleString('ru-RU')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <div className="text-sm text-text-muted">Блэкаутов ещё не было.</div>}
      </div>
    </div>
  );
}
