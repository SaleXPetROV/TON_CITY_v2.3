/**
 * Админка → Объявления → «Скорость рассылки»: сколько сообщений в секунду шлёт бот, порядок получателей
 * (заблокировавшие бота — последними) и анализ последней рассылки.
 */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Gauge, Star } from 'lucide-react';
import { BroadcastAnalysis } from '@/components/admin/BroadcastProgressDialog';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const inp = 'bg-black/40 border border-white/15 rounded-lg px-2.5 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400/60';

export default function BroadcastSpeedPanel({ token }) {
  const h = { headers: { Authorization: `Bearer ${token}` } };
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/broadcast-speed`, { headers: { Authorization: `Bearer ${token}` } }); setS(r.data); }
    catch (e) { toast.error('Не удалось загрузить настройки рассылки'); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true);
    try {
      await axios.put(`${API}/admin/broadcast-speed`, { tg_per_sec: Number(s.tg_per_sec), paid: !!s.paid, paid_per_sec: Number(s.paid_per_sec), dead_last: !!s.dead_last }, h);
      toast.success('Сохранено');
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
    setBusy(false);
  };

  if (!s) return <div className="glass-panel rounded-2xl p-6 text-text-muted text-sm">Загрузка…</div>;
  const k = s.known || {};
  const known = (k.ok || 0) + (k.blocked || 0) + (k.not_found || 0) + (k.error || 0);
  return (
    <div className="space-y-4" data-testid="broadcast-speed">
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div>
          <h2 className="font-unbounded text-lg font-bold text-text-main flex items-center gap-2"><Gauge className="w-5 h-5 text-cyber-cyan" />Скорость рассылки в Telegram</h2>
          <p className="text-xs text-text-muted mt-1 max-w-3xl">
            Telegram бесплатно пропускает от бота около 30 сообщений в секунду, и это всё вместе: отправка тому, кто
            заблокировал бота, тоже занимает место. Поэтому бот помнит, кто получил прошлую рассылку, и в следующий раз
            сначала пишет новым и тем, кто получил, а заблокировавшим — в конце. Если Telegram просит подождать, рассылка
            ждёт и замедляется сама, никто не теряется.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <label className="text-xs text-white/60 flex flex-col gap-1">Сообщений в секунду (бесплатно, до 30)
            <input type="number" min={1} max={30} className={`${inp} w-28`} value={s.tg_per_sec} disabled={s.paid}
              onChange={(e) => setS({ ...s, tg_per_sec: e.target.value })} data-testid="bs-rate" />
          </label>
          <label className="flex items-center gap-2 text-sm text-white/85">
            <input type="checkbox" checked={s.dead_last !== false} onChange={(e) => setS({ ...s, dead_last: e.target.checked })} data-testid="bs-dead-last" />
            Заблокировавших бота — в конец очереди
          </label>
        </div>

        <div className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-3 space-y-2">
          <label className="flex items-center gap-2 text-sm text-white/90">
            <input type="checkbox" checked={!!s.paid} onChange={(e) => setS({ ...s, paid: e.target.checked })} data-testid="bs-paid" />
            <Star className="w-4 h-4 text-amber-300" />Платная рассылка Telegram — до 1000 в секунду
          </label>
          <p className="text-xs text-text-muted">
            Включается сначала в @BotFather. Telegram берёт 0,1 Star за каждое сообщение сверх бесплатных 30 в секунду
            (только за доставленные). Условия Telegram: на балансе бота не меньше 100 000 Stars и не меньше 100 000
            пользователей в месяц. Без этого Telegram ответит ошибкой — не включайте.
          </p>
          {s.paid && (
            <label className="text-xs text-white/60 flex flex-col gap-1 w-56">Сообщений в секунду (30–1000)
              <input type="number" min={30} max={1000} className={inp} value={s.paid_per_sec} onChange={(e) => setS({ ...s, paid_per_sec: e.target.value })} data-testid="bs-paid-rate" />
            </label>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-white text-sm font-semibold disabled:opacity-40" onClick={save} disabled={busy} data-testid="bs-save">Сохранить</button>
          <span className="text-xs text-text-muted">Сейчас: {s.rate} в секунду{s.paid_on ? ' · платная' : ''}</span>
        </div>
      </div>

      <div className="glass-panel rounded-2xl p-6 space-y-3">
        <h3 className="font-unbounded text-base font-bold text-text-main">Что бот знает о подписчиках</h3>
        {known ? (
          <div className="flex flex-wrap gap-2 text-xs" data-testid="bs-known">
            <span className="px-2 py-1 rounded bg-emerald-500/15 text-emerald-200">получили прошлую рассылку: {(k.ok || 0).toLocaleString('ru-RU')}</span>
            <span className="px-2 py-1 rounded bg-red-500/15 text-red-200">заблокировали бота: {(k.blocked || 0).toLocaleString('ru-RU')}</span>
            <span className="px-2 py-1 rounded bg-white/10 text-white/70">чат удалён: {(k.not_found || 0).toLocaleString('ru-RU')}</span>
            {k.error ? <span className="px-2 py-1 rounded bg-amber-500/15 text-amber-200">ошибка в прошлый раз: {k.error.toLocaleString('ru-RU')}</span> : null}
          </div>
        ) : <div className="text-xs text-text-muted">Пока нет данных — они появятся после первой рассылки.</div>}
        {s.last && (
          <>
            <div className="text-xs text-text-muted">Последняя рассылка: «{s.last.title}»{s.last.finished_at ? ` · ${new Date(s.last.finished_at).toLocaleString('ru-RU')}` : ''} · доставлено {s.last.sent ?? 0} из {s.last.total ?? 0}</div>
            <BroadcastAnalysis an={s.last.analysis} />
          </>
        )}
      </div>
    </div>
  );
}
