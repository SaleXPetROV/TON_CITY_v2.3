/**
 * «XP игроков» — how much XP the players collect per day / week / month and the most (backend/xp_stats.py).
 * All XP of City Pass or only the XP of the games.
 */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { RefreshCw, Trophy } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/admin`;
const PERIODS = [['day', 'Сегодня'], ['yesterday', 'Вчера'], ['week', '7 дней'], ['month', '30 дней']];
const nf = (v) => Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 1 });
const dm = (d) => `${d.slice(8, 10)}.${d.slice(5, 7)}`;

function Kpi({ label, value, sub, accent }) {
  return (
    <div className={`rounded-xl border p-3 ${accent ? 'border-amber-400/40 bg-amber-500/10' : 'border-white/10 bg-white/5'}`}>
      <div className="text-[11px] uppercase tracking-wide text-text-muted">{label}</div>
      <div className={`text-xl font-bold mt-1 ${accent ? 'text-amber-200' : 'text-white'}`}>{value}</div>
      {sub && <div className="text-[11px] text-text-muted mt-0.5 truncate">{sub}</div>}
    </div>
  );
}

export default function XpStatsPanel({ token }) {
  const [period, setPeriod] = useState('day');
  const [source, setSource] = useState('all');
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true);
    try {
      const r = await axios.get(`${API}/xp-stats?period=${period}&source=${source}`, { headers: { Authorization: `Bearer ${token}` } });
      setD(r.data);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Не удалось загрузить статистику XP'); } finally { setBusy(false); }
  }, [period, source, token]);
  useEffect(() => { load(); }, [load]);

  const peak = Math.max(1, ...((d?.series || []).map((s) => s.total)));
  return (
    <div className="space-y-4" data-testid="xp-stats">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-xl border border-white/10 bg-white/5 p-1">
          {PERIODS.map(([id, label]) => (
            <button key={id} type="button" onClick={() => setPeriod(id)} data-testid={`xp-period-${id}`}
              className={`px-3 py-1.5 rounded-lg text-sm ${period === id ? 'bg-fuchsia-500/25 text-white' : 'text-white/60 hover:text-white'}`}>{label}</button>
          ))}
        </div>
        <div className="flex rounded-xl border border-white/10 bg-white/5 p-1">
          {[['all', 'Всё XP (City Pass)'], ['games', 'Только игры']].map(([id, label]) => (
            <button key={id} type="button" onClick={() => setSource(id)} data-testid={`xp-source-${id}`}
              className={`px-3 py-1.5 rounded-lg text-sm ${source === id ? 'bg-cyan-500/25 text-white' : 'text-white/60 hover:text-white'}`}>{label}</button>
          ))}
        </div>
        <button type="button" onClick={load} className="ml-auto text-white/60 hover:text-white p-2" title="Обновить"><RefreshCw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} /></button>
      </div>
      {!d ? <div className="text-sm text-text-muted">Загрузка…</div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
            <Kpi label="Игроков с XP" value={nf(d.players)} />
            <Kpi label="Всего XP" value={nf(d.total)} />
            <Kpi label="В среднем на игрока" value={nf(d.avg)} sub={`медиана ${nf(d.median)}`} />
            <Kpi label="Максимум за период" value={d.max ? nf(d.max.xp) : '—'} sub={d.max?.username} accent />
            <Kpi label="Средний игрок за 1 день" value={nf(d.per_player_day?.avg)} />
            <Kpi label="Рекорд за 1 день" value={nf(d.per_player_day?.max)} />
          </div>
          {d.series.length > 1 && (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3" data-testid="xp-series">
              <div className="text-xs text-text-muted mb-2">XP по дням (столбец — всего за день, подпись — игроков и максимум одного игрока)</div>
              <div className="flex items-end gap-1 h-40">
                {d.series.map((s) => (
                  <div key={s.day} className="flex-1 min-w-0 flex flex-col items-center justify-end h-full group" title={`${dm(s.day)}: ${nf(s.total)} XP · игроков ${s.players} · максимум ${nf(s.max)}`}>
                    <div className="text-[9px] text-white/60 mb-0.5 opacity-0 group-hover:opacity-100">{nf(s.total)}</div>
                    <div className="w-full rounded-t bg-gradient-to-t from-fuchsia-600/70 to-amber-300/90" style={{ height: `${Math.max(2, (s.total / peak) * 100)}%` }} />
                    <div className="text-[9px] text-text-muted mt-1">{dm(s.day)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 overflow-x-auto">
            <div className="text-sm font-bold text-white mb-2 flex items-center gap-2"><Trophy className="w-4 h-4 text-amber-300" />Больше всех XP за период</div>
            <table className="w-full text-xs" data-testid="xp-top">
              <thead><tr className="text-text-muted text-left"><th className="py-1 pr-3">#</th><th className="py-1 pr-3">Игрок</th><th className="py-1 pr-3">XP</th><th className="py-1 pr-3">Доля от всех</th></tr></thead>
              <tbody>
                {d.top.map((t, i) => (
                  <tr key={t.user_id} className="border-t border-white/5">
                    <td className="py-1 pr-3 text-white/60">{i + 1}</td>
                    <td className="py-1 pr-3 text-white">{t.username}</td>
                    <td className="py-1 pr-3 font-mono text-amber-200">{nf(t.xp)}</td>
                    <td className="py-1 pr-3 text-white/60">{d.total ? `${((t.xp / d.total) * 100).toFixed(1)}%` : '—'}</td>
                  </tr>
                ))}
                {!d.top.length && <tr><td colSpan={4} className="py-2 text-text-muted">За этот период XP никто не получал.</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
