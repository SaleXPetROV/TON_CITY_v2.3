import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Send, Users, CheckCircle2, Loader2, AlertTriangle, Square } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtLeft = (sec) => {
  if (!Number.isFinite(sec) || sec <= 0) return '';
  const m = Math.floor(sec / 60), s = Math.round(sec % 60);
  return m ? `≈ ${m} мин ${s} с` : `≈ ${s} с`;
};

function Row({ icon: Icon, title, done, total, status, rate, testid, extra }) {
  const pct = total ? Math.min(100, (done / total) * 100) : (status === 'done' ? 100 : 0);
  const running = status === 'running' || status === 'starting';
  return (
    <div className="rounded-lg border border-white/10 bg-black/30 p-3 space-y-2" data-testid={testid}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm text-white font-bold"><Icon className="w-4 h-4 text-cyber-cyan" />{title}</div>
        {status === 'done' && <span className="text-xs text-emerald-400 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" />готово</span>}
        {running && <span className="text-xs text-cyan-300 flex items-center gap-1"><Loader2 className="w-3.5 h-3.5 animate-spin" />идёт</span>}
        {status === 'off' && <span className="text-xs text-text-muted">бот не подключён</span>}
        {status === 'failed' && <span className="text-xs text-red-400">ошибка</span>}
        {status === 'stopped' && <span className="text-xs text-amber-300">остановлено</span>}
      </div>
      <div className="text-2xl font-unbounded text-white" data-testid={`${testid}-count`}>
        {done.toLocaleString('ru-RU')} <span className="text-base text-text-muted">из {total.toLocaleString('ru-RU')}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-emerald-400 transition-all duration-700" style={{ width: `${pct}%` }} />
      </div>
      <div className="flex flex-wrap justify-between gap-x-3 text-xs text-text-muted">
        <span>{Math.round(pct)}%{rate ? ` · ${rate} в секунду` : ''}</span>
        {running && rate && total > done && <span>осталось {fmtLeft((total - done) / rate)}</span>}
      </div>
      {extra}
    </div>
  );
}

/** Live delivery of one announcement: bot subscribers and project accounts. Polls once a second while it runs. */
export default function BroadcastProgressDialog({ annId, token, onClose }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!annId) return undefined;
    let stop = false, timer = null;
    const tick = async () => {
      try {
        const r = await axios.get(`${API}/admin/announcement/${annId}/delivery`, { headers: { Authorization: `Bearer ${token}` } });
        if (stop) return;
        setData(r.data);
        const st = r.data?.delivery?.status;
        if (st === 'done' || st === 'interrupted' || st === 'failed' || st === 'stopped') return;
      } catch (e) { /* keep polling */ }
      if (!stop) timer = setTimeout(tick, 1000);
    };
    setData(null);
    tick();
    return () => { stop = true; if (timer) clearTimeout(timer); };
  }, [annId, token]);

  const d = data?.delivery || {};
  const st = d.status || 'starting';
  const tgStatus = d.telegram_status || (st === 'done' ? 'done' : st);
  const appStatus = d.in_app_status || (st === 'done' ? 'done' : st);
  const lost = (d.blocked || 0) + (d.not_found || 0) + (d.failed || 0);
  const running = st === 'running' || st === 'starting';
  const [stopping, setStopping] = useState(false);
  const stopIt = async () => {
    setStopping(true);
    try {
      await axios.post(`${API}/admin/announcement/${annId}/stop`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Рассылка останавливается…');
    } catch (e) { toast.error(e?.response?.data?.detail || 'Не удалось остановить'); } finally { setStopping(false); }
  };

  return (
    <Dialog open={!!annId} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="glass-panel border-white/10 max-w-md" data-testid="broadcast-progress">
        <DialogHeader>
          <DialogTitle className="font-unbounded text-white">Рассылка объявления</DialogTitle>
          <DialogDescription className="text-text-muted truncate">{data?.title || '…'}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Row
            icon={Send} title="Пользователи бота (Telegram)" testid="broadcast-tg"
            done={d.sent || 0} total={d.telegram_total || 0} status={tgStatus} rate={d.rate_tg ? Math.round(d.rate_tg) : null}
            extra={(
              <div className="text-xs text-text-muted space-y-0.5">
                {lost ? (
                  <div data-testid="broadcast-tg-lost">не доставлено: {lost} (заблокировали бота: {d.blocked || 0} · чат не найден: {d.not_found || 0} · ошибки: {d.failed || 0})</div>
                ) : null}
                {running && d.telegram_stage === 'channel' && <div className="text-cyan-300">публикация в канал…</div>}
                {d.channel && <div>канал: {d.channel === 'sent' ? 'опубликовано' : 'не удалось опубликовать'}</div>}
                {d.tg_error && (lost > 0 || d.channel === 'failed' || tgStatus === 'failed') && (
                  <div className="text-red-300 break-words" data-testid="broadcast-tg-error">ответ Telegram: {d.tg_error}</div>
                )}
              </div>
            )}
          />
          <Row
            icon={Users} title="Пользователи проекта (в игре)" testid="broadcast-app"
            done={d.in_app || 0} total={d.in_app_total || 0} status={appStatus} rate={d.rate_in_app ? Math.round(d.rate_in_app) : null}
          />
          {st === 'stopped' && (
            <div className="flex items-start gap-2 text-xs text-amber-300 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0" />Рассылка остановлена. Получили те, кто посчитан выше.
            </div>
          )}
          {st === 'interrupted' && (
            <div className="flex items-start gap-2 text-xs text-amber-300 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0" />Рассылка прервалась (сервер перезапускался). Получили те, кто посчитан выше.
            </div>
          )}
          <div className="text-[11px] text-text-muted">
            Окно можно закрыть — рассылка продолжится на сервере. Счётчики также видны в карточке объявления.
          </div>
          <div className="flex gap-2">
            {running && (
              <Button variant="outline" className="flex-1 border-red-500/40 text-red-300 hover:bg-red-500/10" disabled={stopping || !!d.stop_requested} onClick={stopIt} data-testid="broadcast-stop">
                <Square className="w-3.5 h-3.5 mr-1.5" />Остановить
              </Button>
            )}
            <Button className="flex-1" variant="outline" onClick={onClose} data-testid="broadcast-progress-close">Закрыть</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
