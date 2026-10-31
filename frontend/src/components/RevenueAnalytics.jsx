/**
 * RevenueAnalytics — admin «Доходы», built from the platform ledger (backend/ledger.py):
 * every amount the platform received or paid out, per kind, per period, with the real-money part.
 * Russian only (admin).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { RefreshCw, TrendingUp, TrendingDown, Wallet, Gift, Scale } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/admin/ledger`;
const PERIODS = [['today', 'Сегодня'], ['7d', '7 дней'], ['30d', '30 дней'], ['90d', '90 дней'], ['all', 'Всё время']];
const ton = (v) => `${Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 4 })} TON`;
const city = (v) => `${Math.round(Number(v || 0) * 1000).toLocaleString('ru-RU')} $CITY`;
const dt = (s) => { try { return new Date(s).toLocaleString('ru-RU'); } catch (_) { return s || ''; } };

function Kpi({ icon: Icon, label, value, sub, tone }) {
  return (
    <div className={`rounded-xl border p-3 ${tone}`}>
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-text-muted"><Icon className="w-3.5 h-3.5" />{label}</div>
      <div className="text-xl font-bold text-white mt-1">{ton(value)}</div>
      <div className="text-[11px] text-text-muted">{sub || city(value)}</div>
    </div>
  );
}

function KindTable({ rows, total, dir, onPick }) {
  const groups = useMemo(() => {
    const g = {};
    rows.forEach((r) => { (g[r.group] = g[r.group] || []).push(r); });
    return Object.entries(g).sort((a, b) => b[1].reduce((x, r) => x + r.ton, 0) - a[1].reduce((x, r) => x + r.ton, 0));
  }, [rows]);
  if (!rows.length) return <div className="text-xs text-text-muted py-3">За период {dir === 'in' ? 'поступлений' : 'выплат'} нет</div>;
  return (
    <table className="w-full text-xs">
      <thead className="text-text-muted"><tr className="text-left">
        <th className="p-1.5">За что</th><th className="p-1.5 text-right">Операций</th><th className="p-1.5 text-right">Сумма</th>
        {dir === 'in' && <th className="p-1.5 text-right">из них реальными</th>}<th className="p-1.5 w-32">Доля</th>
      </tr></thead>
      <tbody>
        {groups.map(([g, list]) => (
          <FragmentRows key={g} g={g} list={list} total={total} dir={dir} onPick={onPick} />
        ))}
      </tbody>
    </table>
  );
}

function FragmentRows({ g, list, total, dir, onPick }) {
  const sum = list.reduce((x, r) => x + r.ton, 0);
  return (
    <>
      <tr className="border-t border-white/10 bg-white/[0.03]"><td className="p-1.5 font-bold text-white/90" colSpan={dir === 'in' ? 3 : 2}>{g}</td><td className="p-1.5 text-right font-bold text-white/90" colSpan={2}>{ton(sum)}</td></tr>
      {list.map((r) => {
        const pct = total > 0 ? (r.ton / total) * 100 : 0;
        return (
          <tr key={r.kind} className="border-t border-white/5 cursor-pointer hover:bg-white/[0.04]" onClick={() => onPick(r.kind)} title="Показать операции">
            <td className="p-1.5 pl-4 text-white/85">{r.label}</td>
            <td className="p-1.5 text-right text-white/70">{r.count}</td>
            <td className="p-1.5 text-right text-white whitespace-nowrap">{ton(r.ton)}<div className="text-[10px] text-text-muted">{city(r.ton)}</div></td>
            {dir === 'in' && <td className="p-1.5 text-right text-emerald-300 whitespace-nowrap">{ton(r.real_ton)}</td>}
            <td className="p-1.5"><div className="h-1.5 rounded bg-white/10 overflow-hidden"><div className={`h-full ${dir === 'in' ? 'bg-emerald-400' : 'bg-rose-400'}`} style={{ width: `${pct}%` }} /></div><div className="text-[10px] text-text-muted">{pct.toFixed(1)}%</div></td>
          </tr>
        );
      })}
    </>
  );
}

export default function RevenueAnalytics({ token }) {
  const [period, setPeriod] = useState('30d');
  const [range, setRange] = useState({ from: '', to: '' });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [kind, setKind] = useState('');
  const [entries, setEntries] = useState([]);
  const [more, setMore] = useState(true);
  const headers = { headers: { Authorization: `Bearer ${token}` } };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = range.from || range.to ? { date_from: range.from, date_to: range.to } : { period };
      const r = await axios.get(`${API}/summary`, { ...headers, params });
      setData(r.data);
    } catch (e) { setData({ error: e?.response?.data?.detail || 'Не удалось загрузить доходы' }); } finally { setLoading(false); }
  }, [period, range, token]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadEntries = useCallback(async (append = false) => {
    try {
      const before = append && entries.length ? entries[entries.length - 1].created_at : '';
      const r = await axios.get(`${API}/entries`, { ...headers, params: { kind, limit: 100, before } });
      const items = r.data.items || [];
      setEntries((x) => (append ? [...x, ...items] : items));
      setMore(items.length === 100);
    } catch (_) { /* noop */ }
  }, [kind, entries, token]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadEntries(false); }, [kind]); // eslint-disable-line react-hooks/exhaustive-deps

  const t = data?.totals || {};
  const maxDay = Math.max(1e-9, ...((data?.daily || []).map((d) => Math.max(d.in, d.out))));

  return (
    <div className="space-y-4" data-testid="revenue-ledger">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-unbounded text-lg font-bold text-text-main mr-2">Доходы платформы</h2>
        {PERIODS.map(([k, l]) => (
          <button key={k} type="button" onClick={() => { setRange({ from: '', to: '' }); setPeriod(k); }} data-testid={`rev-period-${k}`}
            className={`px-3 h-8 rounded-lg text-xs font-semibold border ${period === k && !range.from && !range.to ? 'bg-cyber-cyan/20 border-cyber-cyan/60 text-white' : 'bg-white/5 border-white/10 text-white/70'}`}>{l}</button>
        ))}
        <div className="flex items-center gap-1 text-xs text-text-muted">
          с <Input type="date" value={range.from} onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))} className="h-8 w-36 bg-black/40 border-white/10 text-xs" />
          по <Input type="date" value={range.to} onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))} className="h-8 w-36 bg-black/40 border-white/10 text-xs" />
        </div>
        <Button size="sm" variant="outline" onClick={() => { load(); loadEntries(false); }} disabled={loading} className="ml-auto"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></Button>
      </div>

      {data?.error && <div className="text-sm text-red-400">{data.error}</div>}
      {!data ? <div className="text-sm text-text-muted py-8 text-center">Загрузка…</div> : !data.error && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
            <Kpi icon={TrendingUp} label="Получено всего" value={t.income_ton} tone="bg-emerald-500/5 border-emerald-500/25" />
            <Kpi icon={Wallet} label="из них реальными деньгами" value={t.income_real_ton} tone="bg-emerald-500/5 border-emerald-500/25" />
            <Kpi icon={Gift} label="из них бонусами игроков" value={t.income_bonus_ton} sub="бонусы — не деньги: в чистый доход не входят" tone="bg-white/5 border-white/10" />
            <Kpi icon={TrendingDown} label="Выплачено игрокам" value={t.expense_ton} tone="bg-rose-500/5 border-rose-500/25" />
            <Kpi icon={Scale} label="Чистый доход (реальные деньги)" value={t.net_real_ton} sub={`= ${ton(t.income_real_ton)} − ${ton(t.expense_ton)}`} tone="bg-cyber-cyan/5 border-cyber-cyan/30" />
          </div>

          <div className="grid xl:grid-cols-2 gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-3" data-testid="rev-income">
              <div className="text-sm font-bold text-emerald-300 mb-2">Поступления — сколько и за что</div>
              <KindTable rows={data.income || []} total={t.income_ton || 0} dir="in" onPick={setKind} />
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-3" data-testid="rev-expense">
              <div className="text-sm font-bold text-rose-300 mb-2">Выплаты игрокам реальными деньгами</div>
              <KindTable rows={data.expense || []} total={t.expense_ton || 0} dir="out" onPick={setKind} />
            </div>
          </div>

          {(data.daily || []).length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-3">
              <div className="text-sm font-bold text-white mb-2">По дням (МСК)</div>
              <div className="space-y-1 max-h-72 overflow-auto">
                {[...data.daily].reverse().map((d) => (
                  <div key={d.day} className="grid grid-cols-[90px_1fr_150px] items-center gap-2 text-[11px]">
                    <span className="text-white/70">{d.day}</span>
                    <div className="space-y-0.5">
                      <div className="h-2 rounded bg-emerald-400/80" style={{ width: `${(d.in / maxDay) * 100}%` }} />
                      {d.out > 0 && <div className="h-2 rounded bg-rose-400/80" style={{ width: `${(d.out / maxDay) * 100}%` }} />}
                    </div>
                    <span className="text-right"><span className="text-emerald-300">+{ton(d.in)}</span>{d.out > 0 && <span className="text-rose-300"> −{ton(d.out)}</span>}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-3" data-testid="rev-entries">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <div className="text-sm font-bold text-white">Журнал операций</div>
              <select value={kind} onChange={(e) => setKind(e.target.value)} className="h-8 rounded bg-black/40 border border-white/10 text-xs text-white px-1" data-testid="rev-kind">
                <option value="">Все виды</option>
                {Object.entries(data.kinds || {}).map(([k, v]) => <option key={k} value={k}>{v.dir === 'in' ? '＋ ' : '－ '}{v.label}</option>)}
              </select>
            </div>
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-[11px] min-w-[720px]">
                <thead className="text-text-muted sticky top-0 bg-[#0b1220]"><tr className="text-left"><th className="p-1">Когда</th><th className="p-1">За что</th><th className="p-1 text-right">Сумма</th><th className="p-1 text-right">Реальными</th><th className="p-1">Игрок</th><th className="p-1">Примечание</th></tr></thead>
                <tbody>
                  {entries.map((e) => (
                    <tr key={e.id} className="border-t border-white/5">
                      <td className="p-1 whitespace-nowrap">{dt(e.created_at)}</td>
                      <td className="p-1">{e.label}</td>
                      <td className={`p-1 text-right whitespace-nowrap ${e.dir === 'in' ? 'text-emerald-300' : 'text-rose-300'}`}>{e.dir === 'in' ? '+' : '−'}{ton(e.ton)}</td>
                      <td className="p-1 text-right whitespace-nowrap">{e.dir === 'in' ? ton(e.real_ton) : '—'}</td>
                      <td className="p-1">{e.username ? `@${e.username}` : (e.user_id || '—')}</td>
                      <td className="p-1 max-w-[260px] truncate" title={e.note}>{e.note || ''}{e.external ? ' · вне игры' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {entries.length === 0 && <div className="text-xs text-text-muted py-3">Операций нет</div>}
            </div>
            {more && entries.length > 0 && <Button size="sm" variant="outline" className="mt-2" onClick={() => loadEntries(true)}>Показать ещё</Button>}
          </div>

          <div className="text-[11px] text-text-muted leading-relaxed">
            Журнал ведётся с {data.since ? dt(data.since) : 'момента обновления'}: каждая сумма, которую платформа получила или выплатила, записывается в момент операции.
            Учитываются: продажа участков и постройка бизнесов, улучшения, ремонт, снос, выкуп бизнесов уровня 0, доля государства с изъятых бизнесов, налоги с продажи ресурсов и бизнесов, налог с оборота, комиссии перепродажи, аренды бизнесов и складов, тендеров и штрафы, комиссия за вывод, City Pass Premium, создание альянсов, возврат кредитов, продажа Founder Pass.
            Расходы: выплаты Founder Pass, бонусы за рефералов и комиссии B2B-партнёрам, покупка ресурсов государством, выдача кредитов, промокоды на реальный баланс.
            «Реальными» — часть, оплаченная реальным балансом; остальное игрок заплатил бонусами (это не деньги, поэтому чистый доход считается только по реальной части).
            Условные налоги экономических тиков и сбора дохода не учитываются — с игроков при этом деньги не списываются. Старые счётчики до журнала не переносились: они смешивали $CITY и TON и учитывали условные налоги.
          </div>
        </>
      )}
    </div>
  );
}
