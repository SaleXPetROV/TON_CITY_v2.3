/**
 * Админка → Мульти-аккаунты → «Общий IP»: аккаунты, которые заходили с одного IP за выбранный период.
 * IP записывается при каждом действии игрока (не чаще раза в 15 минут на пару «игрок + IP»).
 * Здесь же: блокировка выбранных, «Не мульти» (IP офиса, семьи, мобильного оператора), выгрузка CSV и
 * ежедневный отчёт файлом в Telegram в заданное время.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Network, Download, Send, Ban, ShieldCheck, Search, RefreshCw, EyeOff, Eye, Clock, Copy } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const TZS = ['Europe/Moscow', 'Europe/Minsk', 'Europe/Kyiv', 'Europe/Berlin', 'Europe/London', 'Asia/Almaty', 'Asia/Tashkent', 'Asia/Dubai', 'Asia/Jakarta', 'UTC'];
const inp = 'bg-black/40 border border-white/15 rounded-lg px-2.5 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400/60';
const btn = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition disabled:opacity-40';
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—');

export default function MultiIpPanel() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const h = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);
  const [days, setDays] = useState(30);
  const [minUsers, setMinUsers] = useState(2);
  const [q, setQ] = useState('');
  const [showIgnored, setShowIgnored] = useState(false);
  const [data, setData] = useState(null);
  const [sel, setSel] = useState({});
  const [busy, setBusy] = useState(false);
  const [cfg, setCfg] = useState(null);
  const [reason, setReason] = useState('Мульти-аккаунт: несколько аккаунтов с одного IP');

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/admin/multi-ip`, { ...h, params: { days, min_users: minUsers, include_ignored: showIgnored, q } });
      setData(r.data);
      setCfg((c) => c || { ...r.data.settings, chat_ids_text: (r.data.settings.chat_ids || []).join(', ') });
    } catch (e) { toast.error(e.response?.data?.detail || 'Не удалось загрузить'); }
  }, [h, days, minUsers, showIgnored, q]);
  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [load]);

  const selected = Object.keys(sel).filter((k) => sel[k]);
  const toggle = (id) => setSel((s) => ({ ...s, [id]: !s[id] }));
  const selectGroup = (g, keepOne) => setSel((s) => {
    const n = { ...s };
    // «все, кроме самого старого»: keep the first-registered account of the group
    const users = [...g.users].filter((u) => !u.admin);
    const keep = keepOne ? [...users].sort((a, b) => String(a.created_at || '').localeCompare(String(b.created_at || '')))[0]?.id : null;
    users.forEach((u) => { n[u.id] = u.id !== keep; });
    return n;
  });

  const block = async (ids, unblock = false) => {
    if (!ids.length) return;
    if (!window.confirm(unblock ? `Разблокировать ${ids.length} акк.?` : `Заблокировать ${ids.length} акк.?\nПричина: ${reason}`)) return;
    setBusy(true);
    try {
      const r = await axios.post(`${API}/admin/multi-ip/block`, { user_ids: ids, unblock, reason }, h);
      toast.success(unblock ? `Разблокировано: ${r.data.changed}` : `Заблокировано: ${r.data.changed}`);
      setSel({}); await load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
    setBusy(false);
  };
  const ignore = async (g, undo = false) => {
    const note = undo ? '' : window.prompt('Почему это не мульти? (офис, семья, мобильный оператор…)', '') ?? null;
    if (note === null) return;
    try { await axios.post(`${API}/admin/multi-ip/ignore`, { ip_bidx: g.ip_bidx, note, undo }, h); toast.success(undo ? 'IP снова в списке' : 'IP скрыт из списка и отчёта'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const exportCsv = async () => {
    try {
      const r = await axios.get(`${API}/admin/multi-ip/export.csv`, { ...h, params: { days, min_users: minUsers }, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a'); a.href = url; a.download = `multi_accounts_${new Date().toISOString().slice(0, 10)}.csv`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error('Не удалось выгрузить'); }
  };
  const saveCfg = async () => {
    try {
      const body = { enabled: cfg.enabled, time: cfg.time, tz: cfg.tz, days: Number(cfg.days), min_users: Number(cfg.min_users),
        only_new: cfg.only_new, chat_ids: cfg.chat_ids_text };
      const r = await axios.put(`${API}/admin/multi-ip/settings`, body, h);
      setCfg({ ...r.data, chat_ids_text: (r.data.chat_ids || []).join(', ') });
      toast.success(r.data.enabled ? `Отчёт будет приходить каждый день в ${r.data.time}` : 'Сохранено');
    } catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const sendNow = async () => {
    setBusy(true);
    try { const r = await axios.post(`${API}/admin/multi-ip/send-now`, {}, h); toast.success(`Файл отправлен: ${r.data.sent} получ., ${r.data.groups} IP, ${r.data.accounts} акк.`); }
    catch (e) { toast.error(e.response?.data?.detail || 'Не удалось отправить'); }
    setBusy(false);
  };

  const t = data?.totals || {};
  return (
    <div className="space-y-4 mb-6" data-testid="multi-ip-panel">
      <div className="bg-void border border-orange-500/30 rounded-xl p-5">
        <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
          <div>
            <h3 className="text-xl font-bold text-white flex items-center gap-2"><Network className="w-5 h-5 text-orange-400" /> Общий IP</h3>
            <p className="text-xs text-text-muted mt-1 max-w-3xl">
              Аккаунты, которые заходили в игру с одного IP. IP записывается при каждом действии игрока (не чаще раза в 15 минут).
              Один IP бывает у семьи, офиса или мобильного оператора — такие IP можно скрыть кнопкой «Не мульти».
              Заблокированный игрок видит причину и может написать в поддержку, остальное ему недоступно.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="px-2 py-1 rounded bg-orange-500/20 text-orange-200" data-testid="mip-groups">IP: {t.groups ?? '…'}</span>
            <span className="px-2 py-1 rounded bg-cyan-500/20 text-cyan-200">Аккаунтов: {t.accounts ?? '…'}</span>
            <span className="px-2 py-1 rounded bg-red-500/20 text-red-200">Заблокировано: {t.blocked ?? '…'}</span>
            <span className="px-2 py-1 rounded bg-white/10 text-white/60">Скрыто IP: {t.ignored ?? 0}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-3">
          <label className="text-xs text-white/60">Период
            <select className={`${inp} ml-1`} value={days} onChange={(e) => setDays(Number(e.target.value))}>
              {[1, 3, 7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>{d} дн.</option>)}
            </select>
          </label>
          <label className="text-xs text-white/60">Аккаунтов на IP от
            <select className={`${inp} ml-1`} value={minUsers} onChange={(e) => setMinUsers(Number(e.target.value))}>
              {[2, 3, 4, 5, 10].map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2 top-2.5 text-white/40" />
            <input className={`${inp} pl-7 w-56`} placeholder="IP, ник или ID" value={q} onChange={(e) => setQ(e.target.value)} data-testid="mip-search" />
          </div>
          <label className="text-xs text-white/60 flex items-center gap-1"><input type="checkbox" checked={showIgnored} onChange={(e) => setShowIgnored(e.target.checked)} /> показать скрытые</label>
          <button className={`${btn} bg-white/10 text-white/80`} onClick={load}><RefreshCw className="w-3.5 h-3.5" /> Обновить</button>
          <button className={`${btn} bg-cyan-500/20 text-cyan-100`} onClick={exportCsv} data-testid="mip-export"><Download className="w-3.5 h-3.5" /> CSV</button>
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-3 p-2 rounded-lg bg-red-500/5 border border-red-500/20">
          <span className="text-xs text-white/70">Выбрано: <b className="text-white">{selected.length}</b></span>
          <input className={`${inp} flex-1 min-w-[220px] text-xs`} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Причина блокировки (игрок её увидит)" />
          <button className={`${btn} bg-red-500/80 hover:bg-red-500 text-white`} disabled={!selected.length || busy} onClick={() => block(selected)} data-testid="mip-block-selected"><Ban className="w-3.5 h-3.5" /> Заблокировать</button>
          <button className={`${btn} bg-emerald-500/20 text-emerald-100`} disabled={!selected.length || busy} onClick={() => block(selected, true)}><ShieldCheck className="w-3.5 h-3.5" /> Разблокировать</button>
          {!!selected.length && <button className={`${btn} text-white/50`} onClick={() => setSel({})}>Снять выбор</button>}
        </div>

        <div className="space-y-2 max-h-[640px] overflow-y-auto pr-1">
          {(data?.groups || []).map((g) => (
            <div key={g.ip_bidx} className={`rounded-xl border p-3 ${g.ignored ? 'border-white/10 opacity-60' : 'border-orange-500/25 bg-orange-500/[0.03]'}`} data-testid={`mip-group-${g.ip_bidx.slice(0, 8)}`}>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-mono text-orange-200">{g.ip}</span>
                  <button title="Скопировать IP" onClick={() => { navigator.clipboard.writeText(g.ip); toast.success('IP скопирован'); }}><Copy className="w-3 h-3 text-white/40" /></button>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-100">{g.count} акк.</span>
                  {g.blocked > 0 && <span className="text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-200">заблок. {g.blocked}</span>}
                  <span className="text-[11px] text-white/40">последний вход {fmt(g.last_seen)}</span>
                  {g.ignored && <span className="text-[11px] text-white/50">не мульти{g.note ? `: ${g.note}` : ''}</span>}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <button className={`${btn} bg-white/10 text-white/80`} onClick={() => selectGroup(g, true)} title="Выбрать всех, кроме самого старого аккаунта">Все, кроме первого</button>
                  <button className={`${btn} bg-white/10 text-white/80`} onClick={() => selectGroup(g, false)}>Выбрать всех</button>
                  {g.ignored
                    ? <button className={`${btn} bg-white/10 text-white/70`} onClick={() => ignore(g, true)}><Eye className="w-3.5 h-3.5" /> Вернуть</button>
                    : <button className={`${btn} bg-white/10 text-white/70`} onClick={() => ignore(g)}><EyeOff className="w-3.5 h-3.5" /> Не мульти</button>}
                </div>
              </div>
              <table className="w-full text-xs">
                <thead className="text-white/40 text-left">
                  <tr><th className="w-6"></th><th className="py-1">Ник</th><th>ID</th><th>Создан</th><th>Последний вход</th><th>Действий</th><th>Других общих IP</th><th>Баланс</th><th></th></tr>
                </thead>
                <tbody>
                  {g.users.map((u) => (
                    <tr key={u.id} className={`border-t border-white/5 ${u.blocked ? 'text-red-300/80' : 'text-white/85'}`}>
                      <td><input type="checkbox" disabled={u.admin} checked={!!sel[u.id]} onChange={() => toggle(u.id)} data-testid={`mip-sel-${u.id}`} /></td>
                      <td className="py-1.5 font-semibold">{u.username}{u.admin && <span className="ml-1 text-[10px] text-cyan-300">админ</span>}{u.blocked && <span className="ml-1 text-[10px] text-red-300">заблокирован</span>}</td>
                      <td className="font-mono text-white/50">
                        {u.id.slice(0, 8)}… <button title="Скопировать ID" onClick={() => { navigator.clipboard.writeText(u.id); toast.success('ID скопирован'); }}><Copy className="w-3 h-3 inline" /></button>
                      </td>
                      <td>{fmt(u.created_at)}</td>
                      <td>{fmt(u.last_seen)}</td>
                      <td>{u.hits}</td>
                      <td>{u.shared_ips > 1 ? <span className="text-amber-300">{u.shared_ips - 1}</span> : '—'}</td>
                      <td>{(u.balance_city || 0).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="text-right">
                        {!u.admin && (u.blocked
                          ? <button className="text-emerald-300 hover:underline" onClick={() => block([u.id], true)}>разблокировать</button>
                          : <button className="text-red-300 hover:underline" onClick={() => block([u.id])} data-testid={`mip-block-${u.id}`}>заблокировать</button>)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          {data && !data.groups.length && <div className="text-center text-white/40 text-sm py-8">Общих IP за этот период нет</div>}
        </div>
      </div>

      {cfg && (
        <div className="bg-void border border-cyan-500/25 rounded-xl p-5" data-testid="mip-report-settings">
          <h4 className="text-base font-bold text-white flex items-center gap-2 mb-1"><Clock className="w-4 h-4 text-cyan-300" /> Отчёт файлом в Telegram</h4>
          <p className="text-xs text-text-muted mb-3">Каждый день в указанное время бот присылает файл CSV: группа, IP, ID игрока, ник, сколько аккаунтов на IP, заблокирован ли. Открывается в Excel и Google Таблицах.</p>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex items-center gap-2 text-sm text-white/85"><input type="checkbox" checked={!!cfg.enabled} onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })} data-testid="mip-enabled" /> Присылать каждый день</label>
            <label className="text-xs text-white/60 flex flex-col gap-1">Время
              <input type="time" className={inp} value={cfg.time} onChange={(e) => setCfg({ ...cfg, time: e.target.value })} data-testid="mip-time" />
            </label>
            <label className="text-xs text-white/60 flex flex-col gap-1">Часовой пояс
              <select className={inp} value={cfg.tz} onChange={(e) => setCfg({ ...cfg, tz: e.target.value })}>{TZS.map((z) => <option key={z} value={z}>{z}</option>)}</select>
            </label>
            <label className="text-xs text-white/60 flex flex-col gap-1">Период
              <select className={inp} value={cfg.days} onChange={(e) => setCfg({ ...cfg, days: e.target.value })}>{[1, 3, 7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>{d} дн.</option>)}</select>
            </label>
            <label className="text-xs text-white/60 flex flex-col gap-1">Аккаунтов на IP от
              <select className={inp} value={cfg.min_users} onChange={(e) => setCfg({ ...cfg, min_users: e.target.value })}>{[2, 3, 4, 5, 10].map((d) => <option key={d} value={d}>{d}</option>)}</select>
            </label>
            <label className="flex items-center gap-2 text-xs text-white/70"><input type="checkbox" checked={!!cfg.only_new} onChange={(e) => setCfg({ ...cfg, only_new: e.target.checked })} /> Только новые IP (которых не было в прошлых отчётах)</label>
          </div>
          <label className="text-xs text-white/60 flex flex-col gap-1 mt-3 max-w-xl">Кому (Telegram ID через запятую; пусто — всем админам с привязанным Telegram)
            <input className={inp} value={cfg.chat_ids_text || ''} onChange={(e) => setCfg({ ...cfg, chat_ids_text: e.target.value })} placeholder="123456789, 987654321" data-testid="mip-chats" />
          </label>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <button className={`${btn} bg-cyan-500 hover:bg-cyan-400 text-white`} onClick={saveCfg} data-testid="mip-save">Сохранить</button>
            <button className={`${btn} bg-white/10 text-white/85`} onClick={sendNow} disabled={busy} data-testid="mip-send-now"><Send className="w-3.5 h-3.5" /> Отправить сейчас</button>
            {cfg.last_sent_date && <span className="text-[11px] text-white/45">последний отчёт: {cfg.last_sent_date}{cfg.last_result ? ` · ${cfg.last_result.ok ? `отправлен (${cfg.last_result.groups} IP)` : `не отправлен: ${cfg.last_result.reason || ''}`}` : ''}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
