/**
 * FounderPassPanel — admin for the Founder Pass (backend/founder_pass.py).
 * Sections: «Инвесторы» (every player with a share: list + full card with all the information about him),
 * «Тарифы и привилегии» (plan editor + each plan's founder perks), «Доступ и условия», «Доли и выплаты»
 * (payouts go to the player's REAL balance with a history entry «Выплата Founder Pass от администрации»).
 * Players buy a share themselves from the real balance — there are no applications any more (old ones stay
 * visible in «Доли и выплаты» if there are any).
 */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Gem, Plus, RefreshCw, Trash2, ArrowUp, ArrowDown, Users, Search } from 'lucide-react';
import FounderInvestorCard from './FounderInvestorCard';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/admin/founder-pass`;
const APP_ST = { new: 'Новая', contacted: 'Связались', approved: 'Одобрена', rejected: 'Отклонена', cancelled: 'Отменена игроком' };
const HOLD_ST = { active: 'Активна', completed: 'Лимит достигнут', bought_out: 'Выкуплена', cancelled: 'Отменена' };
const BADGE = { '': 'нет', popular: 'Популярный', vip: 'VIP' };
// Founder perks of a plan — applied automatically, with no time limit, while the player is a founder
// (a share «Активна» or «Лимит достигнут»; several shares → the best value of each perk).
const PERKS = [
  { k: 'sale_tax_discount_pct', label: 'Скидка на налог с продаж ресурсов, %', hint: 'налог с каждой продажи на рынке ниже на этот %', max: 90 },
  { k: 'withdraw_fee_discount_pct', label: 'Скидка на комиссию вывода, %', hint: 'комиссия вывода TON ниже на этот %', max: 90 },
  { k: 'repair_discount_pct', label: 'Скидка на ремонт бизнесов, %', hint: 'стоимость ремонта ниже на этот %', max: 90 },
  { k: 'welcome_bonus_city', label: 'Приветственный бонус, $CITY', hint: 'один раз при покупке доли, на бонусный баланс', max: 10000000 },
  { k: 'arcade_extra_attempts', label: 'Аркада: + платных попыток', hint: 'в каждой игре', max: 20 },
  { k: 'arcade_xp_bonus_pct', label: 'Аркада: + XP, %', hint: 'к награде за каждую игру', max: 500 },
];
const EMPTY_PERKS = { sale_tax_discount_pct: 0, withdraw_fee_discount_pct: 0, repair_discount_pct: 0, welcome_bonus_city: 0, city_pass_premium: false, arcade_extra_attempts: 0, arcade_xp_bonus_pct: 0, badge: true, withdraw_speed: 'standard' };
export const WD_SPEED = { standard: 'Обычный (до 24 ч, после проверки админом)', h12: 'До 12 часов (автоматически)', instant: 'Моментально (автоматически сразу)' };
const cleanPerks = (p) => {
  const o = { ...EMPTY_PERKS, ...(p || {}) };
  PERKS.forEach(({ k }) => { o[k] = Number(String(o[k] ?? 0).replace(',', '.')) || 0; });
  o.city_pass_premium = !!o.city_pass_premium; o.badge = !!o.badge;
  o.withdraw_speed = WD_SPEED[o.withdraw_speed] ? o.withdraw_speed : 'standard';
  return o;
};

function Kpi({ label, value }) {
  return (
    <div className="rounded-xl bg-white/5 border border-white/10 p-3">
      <div className="text-[11px] uppercase tracking-wide text-text-muted">{label}</div>
      <div className="text-xl font-bold mt-1 text-white">{value}</div>
    </div>
  );
}

const fmtDate = (s) => { try { return new Date(s).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (_) { return s || ''; } };

export default function FounderPassPanel({ token }) {
  const [cfg, setCfg] = useState(null);
  const [f, setF] = useState(null);
  const [apps, setApps] = useState([]);
  const [appFilter, setAppFilter] = useState('open');
  const [holds, setHolds] = useState([]);
  const [busy, setBusy] = useState(false);
  const [manual, setManual] = useState({ user: '', tier_id: '', price: '' });
  const [section, setSection] = useState('investors');
  const [inv, setInv] = useState({ items: [], totals: {} });
  const [invQ, setInvQ] = useState({ q: '', tier: '', status: '' });
  const [openUser, setOpenUser] = useState(null);
  const headers = { headers: { Authorization: `Bearer ${token}` } };
  const err = (e, msg) => toast.error(e?.response?.data?.detail || msg);

  const load = useCallback(async () => {
    try {
      const [s, a, h, iv] = await Promise.all([
        axios.get(`${API}/settings`, headers),
        axios.get(`${API}/applications`, { ...headers, params: { status: appFilter } }),
        axios.get(`${API}/holdings`, headers),
        axios.get(`${API}/investors`, { ...headers, params: invQ }),
      ]);
      setInv(iv.data);
      setCfg(s.data);
      setF((x) => x || { ...s.data, allowedText: (s.data.allowed || []).join('\n'), tiers: s.data.tiers.map((t) => ({ ...t })) });
      setApps(a.data.items || []);
      setHolds(h.data.items || []);
    } catch (e) { err(e, 'Не удалось загрузить Founder Pass'); }
  }, [token, appFilter, invQ]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true);
    try {
      const patch = {
        enabled: !!f.enabled, visibility: f.visibility, allowed: f.allowedText, contact: f.contact,
        cap_pct: Number(f.cap_pct), note: f.note,
        tiers: f.tiers.map((t) => ({ ...t, price: Number(t.price), share_pct: Number(t.share_pct), slots_total: Number(t.slots_total), slots_taken_manual: Number(t.slots_taken_manual), perks: cleanPerks(t.perks) })),
      };
      const r = await axios.put(`${API}/settings`, patch, headers);
      setCfg(r.data);
      setF({ ...r.data, allowedText: (r.data.allowed || []).join('\n'), tiers: r.data.tiers.map((t) => ({ ...t })) });
      toast.success('Founder Pass сохранён');
    } catch (e) { err(e, 'Ошибка сохранения'); } finally { setBusy(false); }
  };

  const setPerk = (i, k, v) => setF((s) => ({ ...s, tiers: s.tiers.map((t, j) => (j === i ? { ...t, perks: { ...EMPTY_PERKS, ...(t.perks || {}), [k]: v } } : t)) }));
  const setTier = (i, patch) => setF((s) => ({ ...s, tiers: s.tiers.map((t, j) => (j === i ? { ...t, ...patch } : t)) }));
  const moveTier = (i, d) => setF((s) => {
    const t = [...s.tiers]; const j = i + d; if (j < 0 || j >= t.length) return s;
    [t[i], t[j]] = [t[j], t[i]]; return { ...s, tiers: t };
  });
  const addTier = () => setF((s) => ({ ...s, tiers: [...s.tiers, { id: `tier${s.tiers.length + 1}`, name: 'NEW PASS', price: 100, share_pct: 0.1, slots_total: 10, slots_taken_manual: 0, badge: '', active: true, perks: { ...EMPTY_PERKS } }] }));

  const appStatus = async (a, status) => {
    if (status === 'approved' && !window.confirm(`Одобрить заявку @${a.username || a.user_id} на ${a.tier_name}? Будет создана доля игрока.`)) return;
    try { await axios.post(`${API}/applications/${a.id}/status`, { status }, headers); toast.success('Готово'); load(); }
    catch (e) { err(e, 'Ошибка'); }
  };
  const payout = async (h) => {
    const left = Math.max(0, Number(h.max_payout || 0) - Number(h.paid_total || 0));
    const v = window.prompt(`Выплата по доле @${h.username} (${h.tier_name}), TON — зачисляется на РЕАЛЬНЫЙ баланс игрока и появится в его истории как «Выплата Founder Pass от администрации». Осталось до лимита: ${left} TON. Отрицательное число — корректировка (списание с реального баланса):`, '');
    if (v === null || v === '') return;
    const note = window.prompt('Комментарий к выплате (необязательно):', '') || '';
    try { await axios.post(`${API}/holdings/${h.id}/payout`, { amount: Number(String(v).replace(',', '.')), note }, headers); toast.success('Выплата зачислена на реальный баланс игрока'); load(); }
    catch (e) { err(e, 'Ошибка'); }
  };
  const holdStatus = async (h, status) => {
    if ((status === 'bought_out' || status === 'cancelled') && !window.confirm(`Перевести долю @${h.username} в «${HOLD_ST[status]}»? Если других долей нет — игрок перестанет быть фоундером и потеряет все привилегии.`)) return;
    try { await axios.post(`${API}/holdings/${h.id}/status`, { status }, headers); load(); }
    catch (e) { err(e, 'Ошибка'); }
  };
  const addManual = async () => {
    try {
      await axios.post(`${API}/holdings`, { user: manual.user, tier_id: manual.tier_id || f.tiers[0]?.id, price: manual.price }, headers);
      toast.success('Доля добавлена'); setManual({ user: '', tier_id: '', price: '' }); load();
    } catch (e) { err(e, 'Ошибка'); }
  };

  if (!cfg || !f) return <div className="text-sm text-text-muted">Загрузка…</div>;
  const money = (v, c = 'TON') => (c === 'USD' ? `$${Number(v || 0).toLocaleString('ru-RU')}` : `${Number(v || 0).toLocaleString('ru-RU')} TON`);
  const tierStats = Object.fromEntries((cfg.tiers || []).map((t) => [t.id, t]));
  const sel = 'h-8 rounded bg-black/40 border border-white/10 text-xs text-white px-1';

  return (
    <div className="space-y-4" data-testid="founder-pass-panel">
      <div className="flex flex-wrap items-center gap-3">
        <Gem className="w-5 h-5 text-amber-300" />
        <span className="font-bold text-white">Founder Pass — закрытый инвесторский пул</span>
        <label className="flex items-center gap-2 text-sm"><Switch checked={!!f.enabled} onCheckedChange={(v) => setF((s) => ({ ...s, enabled: v }))} />{f.enabled ? 'Включён' : 'Выключен'}</label>
        <div className="flex gap-1 ml-auto">
          <Button size="sm" variant="outline" onClick={load}><RefreshCw className="w-4 h-4" /></Button>
          <Button size="sm" onClick={save} disabled={busy} className="bg-amber-500 text-black hover:bg-amber-400">Сохранить</Button>
        </div>
      </div>
      {(() => {
        // what players get RIGHT NOW (the saved settings), and whether the form has unsaved changes
        const unsaved = !!f.enabled !== !!cfg.enabled || f.visibility !== cfg.visibility
          || (f.allowedText || '').trim() !== (cfg.allowed || []).join('\n').trim();
        const n = (cfg.allowed || []).length;
        const st = !cfg.enabled
          ? ['border-rose-400/40 bg-rose-500/10 text-rose-200', 'Сейчас игроки НЕ видят Founder Pass: он выключен. Видят только админы и те, у кого уже есть доля. Включите переключатель «Включён» и нажмите «Сохранить».']
          : cfg.visibility === 'all'
            ? ['border-emerald-400/40 bg-emerald-500/10 text-emerald-200', 'Сейчас Founder Pass видят все игроки: «Бизнесы» → нажать на свой профиль → «Founder Pass».']
            : ['border-amber-400/40 bg-amber-500/10 text-amber-200', `Сейчас Founder Pass видят только игроки из списка доступа (${n}), админы и держатели долей. Чтобы видели все — выберите «Все игроки» и нажмите «Сохранить».`];
        return (
          <div className={`rounded-lg border px-3 py-2 text-xs space-y-1 ${st[0]}`} data-testid="fp-visibility-status">
            <div>{st[1]}</div>
            {unsaved && <div className="font-bold text-amber-300" data-testid="fp-unsaved">Есть несохранённые изменения — игроки их не увидят, пока вы не нажмёте «Сохранить».</div>}
            <div className="text-white/50">Админ видит Founder Pass всегда, поэтому проверяйте на аккаунте обычного игрока. Игроку достаточно закрыть и снова открыть окно профиля.</div>
          </div>
        );
      })()}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Kpi label="Фоундеров сейчас" value={cfg.stats.founders ?? 0} />
        <Kpi label="Активных долей" value={cfg.stats.active_holdings} />
        <Kpi label="Привлечено" value={money(cfg.stats.raised)} />
        <Kpi label="Выплачено" value={money(cfg.stats.paid)} />
      </div>

      <div className="flex flex-wrap gap-1.5" data-testid="fp-sections">
        {[['investors', `Инвесторы (${inv.totals?.founders ?? 0})`], ['tiers', 'Тарифы и привилегии'], ['access', 'Доступ и условия'], ['holdings', 'Доли и выплаты']].map(([k, l]) => (
          <button key={k} type="button" onClick={() => setSection(k)} data-testid={`fp-sec-${k}`}
            className={`px-3 h-8 rounded-lg text-xs font-semibold border ${section === k ? 'bg-amber-500 text-black border-amber-400' : 'bg-white/5 text-white/80 border-white/10 hover:border-white/25'}`}>{l}</button>
        ))}
      </div>

      {section === 'investors' && (
        <Card className="bg-white/[0.03] border-white/10" data-testid="fp-investors">
          <CardHeader className="pb-2 flex-row flex-wrap items-center gap-2 justify-between">
            <CardTitle className="text-sm text-white flex items-center gap-2"><Users className="w-4 h-4 text-amber-300" />Инвесторы</CardTitle>
            <div className="flex flex-wrap gap-2 items-center text-xs">
              <div className="relative"><Search className="w-3.5 h-3.5 absolute left-2 top-2 text-white/40" />
                <Input value={invQ.q} onChange={(e) => setInvQ((q) => ({ ...q, q: e.target.value }))} placeholder="ник, e-mail, Telegram, id" className="h-8 w-56 pl-7 bg-black/40 border-white/10 text-xs" data-testid="fp-inv-search" />
              </div>
              <select value={invQ.tier} onChange={(e) => setInvQ((q) => ({ ...q, tier: e.target.value }))} className={sel}>
                <option value="">Все тарифы</option>
                {(cfg.tiers || []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
              <select value={invQ.status} onChange={(e) => setInvQ((q) => ({ ...q, status: e.target.value }))} className={sel}>
                <option value="">Все</option><option value="founder">Фоундеры сейчас</option><option value="former">Бывшие (выкуплены / отменены)</option>
              </select>
            </div>
          </CardHeader>
          <CardContent className="overflow-auto">
            <div className="text-[11px] text-text-muted mb-2">Всего: {inv.count ?? 0} · вложено {money(inv.totals?.invested)} · выплачено {money(inv.totals?.paid)}. Нажмите на игрока — откроется полная информация о нём.</div>
            {(inv.items || []).length === 0 ? <div className="text-xs text-text-muted">Инвесторов пока нет</div> : (
              <table className="w-full text-xs min-w-[900px]">
                <thead className="text-text-muted"><tr className="text-left">
                  <th className="p-1.5">Игрок</th><th className="p-1.5">Тарифы</th><th className="p-1.5">Вложено</th><th className="p-1.5">Выплачено / лимит</th>
                  <th className="p-1.5">Реальный баланс</th><th className="p-1.5">Инвестор с</th><th className="p-1.5">Последний вход</th><th className="p-1.5">Статус</th>
                </tr></thead>
                <tbody>
                  {inv.items.map((r) => {
                    const cap = (r.holdings || []).filter((h) => h.status === 'active' || h.status === 'completed').reduce((a, h) => a + Number(h.max_payout || 0), 0);
                    return (
                      <tr key={r.user_id} onClick={() => setOpenUser(r.user_id)} className="border-t border-white/5 cursor-pointer hover:bg-white/[0.04]" data-testid={`fp-inv-${r.user_id}`}>
                        <td className="p-1.5"><div className="font-semibold text-white">@{r.username || '—'}{r.is_blocked && <span className="ml-1 text-red-400">⛔</span>}</div>
                          <div className="text-[10px] text-text-muted">{r.email}{r.telegram_username ? ` · @${r.telegram_username}` : ''}{r.telegram_id ? ` · TG ${r.telegram_id}` : ''}</div></td>
                        <td className="p-1.5">{(r.holdings || []).map((h) => (
                          <span key={h.id} className={`inline-block mr-1 mb-0.5 px-1.5 py-0.5 rounded border text-[10px] ${h.status === 'active' || h.status === 'completed' ? 'border-amber-500/40 text-amber-200 bg-amber-500/10' : 'border-white/10 text-white/40 line-through'}`}>{h.tier_name}</span>
                        ))}</td>
                        <td className="p-1.5 text-white">{money(r.invested)}</td>
                        <td className="p-1.5">{money(r.paid)} / {money(cap)}</td>
                        <td className="p-1.5">{money(r.balance_ton)}<div className="text-[10px] text-text-muted">бонус {money(r.bonus_balance)}</div></td>
                        <td className="p-1.5 whitespace-nowrap">{fmtDate(r.since)}</td>
                        <td className="p-1.5 whitespace-nowrap">{fmtDate(r.last_login)}</td>
                        <td className="p-1.5">{r.founder ? <span className="text-emerald-300 font-semibold">Фоундер</span> : <span className="text-white/40">Бывший</span>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      {section === 'access' && <Card className="bg-white/[0.03] border-white/10">
        <CardHeader className="pb-2"><CardTitle className="text-sm text-white">Доступ и условия</CardTitle></CardHeader>
        <CardContent className="grid md:grid-cols-2 gap-3 text-xs">
          <div className="space-y-2">
            <label className="block">Кто видит Founder Pass в профиле
              <select value={f.visibility} onChange={(e) => setF((s) => ({ ...s, visibility: e.target.value }))} className={`${sel} w-full mt-1`}>
                <option value="whitelist">Только игроки из списка доступа</option>
                <option value="all">Все игроки</option>
              </select>
            </label>
            <label className="block">Список доступа (по одному в строке: id, @username, e-mail или Telegram id)
              <textarea value={f.allowedText} onChange={(e) => setF((s) => ({ ...s, allowedText: e.target.value }))} rows={5}
                className="w-full mt-1 rounded bg-black/40 border border-white/10 text-xs text-white p-2" placeholder={'@salex\n123456789'} />
            </label>
            <div className="text-[11px] text-text-muted">Админы видят пул всегда. Игрок, у которого уже есть доля, тоже видит его всегда.</div>
          </div>
          <div className="space-y-2">
            <div className="text-[11px] text-text-muted rounded-lg border border-white/10 bg-white/[0.03] p-2">Кнопка «Есть вопросы?» под тарифами открывает у игрока чат с поддержкой (вкладка «Поддержка» в админке).</div>
            <div className="grid grid-cols-2 gap-2">
              <div className="block">Валюта тарифов
                <div className="h-8 mt-1 rounded bg-black/40 border border-white/10 text-xs text-white px-2 flex items-center">TON</div>
              </div>
              <label className="block">Лимит выплат, % от цены
                <Input type="number" min="100" value={f.cap_pct} onChange={(e) => setF((s) => ({ ...s, cap_pct: e.target.value }))} className="h-8 mt-1 bg-black/40 border-white/10 text-xs" />
              </label>
            </div>
            <label className="block">Текст для игроков под тарифами (на русском, переводится автоматически)
              <textarea value={f.note || ''} onChange={(e) => setF((s) => ({ ...s, note: e.target.value }))} rows={3}
                className="w-full mt-1 rounded bg-black/40 border border-white/10 text-xs text-white p-2" />
            </label>
            <div className="text-[11px] text-text-muted">Игроки всегда видят примечание: «Это не публичная оферта. Выплаты зависят от фактической прибыли проекта и не гарантированы».</div>
          </div>
        </CardContent>
      </Card>}

      {section === 'tiers' && <>
      <Card className="bg-white/[0.03] border-white/10">
        <CardHeader className="pb-2 flex-row items-center justify-between">
          <CardTitle className="text-sm text-white">Тарифы</CardTitle>
          <Button size="sm" variant="outline" onClick={addTier}><Plus className="w-4 h-4 mr-1" />Тариф</Button>
        </CardHeader>
        <CardContent className="overflow-auto">
          <table className="w-full text-xs min-w-[900px]">
            <thead className="text-text-muted">
              <tr className="text-left">
                <th className="p-1">Вкл.</th><th className="p-1">Код</th><th className="p-1">Название</th><th className="p-1">Цена, TON</th>
                <th className="p-1">Доля прибыли, %</th><th className="p-1">Мест всего</th><th className="p-1">Занято вручную</th>
                <th className="p-1">Метка</th><th className="p-1">Продано / осталось</th><th className="p-1">Макс. выплата</th><th className="p-1" />
              </tr>
            </thead>
            <tbody>
              {f.tiers.map((t, i) => {
                const st = tierStats[t.id];
                return (
                  <tr key={i} className="border-t border-white/5">
                    <td className="p-1"><Switch checked={!!t.active} onCheckedChange={(v) => setTier(i, { active: v })} /></td>
                    <td className="p-1"><Input value={t.id} onChange={(e) => setTier(i, { id: e.target.value })} className="h-8 w-24 bg-black/40 border-white/10 text-xs" /></td>
                    <td className="p-1"><Input value={t.name} onChange={(e) => setTier(i, { name: e.target.value })} className="h-8 w-36 bg-black/40 border-white/10 text-xs" /></td>
                    <td className="p-1"><Input type="number" min="0" value={t.price} onChange={(e) => setTier(i, { price: e.target.value })} className="h-8 w-24 bg-black/40 border-white/10 text-xs" /></td>
                    <td className="p-1"><Input type="number" min="0" step="0.01" value={t.share_pct} onChange={(e) => setTier(i, { share_pct: e.target.value })} className="h-8 w-20 bg-black/40 border-white/10 text-xs" /></td>
                    <td className="p-1"><Input type="number" min="0" value={t.slots_total} onChange={(e) => setTier(i, { slots_total: e.target.value })} className="h-8 w-20 bg-black/40 border-white/10 text-xs" /></td>
                    <td className="p-1"><Input type="number" min="0" value={t.slots_taken_manual} onChange={(e) => setTier(i, { slots_taken_manual: e.target.value })} className="h-8 w-20 bg-black/40 border-white/10 text-xs" title="места, проданные вне приложения" /></td>
                    <td className="p-1">
                      <select value={t.badge || ''} onChange={(e) => setTier(i, { badge: e.target.value })} className={sel}>
                        {Object.entries(BADGE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </td>
                    <td className="p-1 text-white/80">{st ? `${st.holdings} / ${st.slots_left}` : '—'}</td>
                    <td className="p-1 text-emerald-300">{money((Number(t.price) || 0) * (Number(f.cap_pct) || 0) / 100)}</td>
                    <td className="p-1 whitespace-nowrap">
                      <button type="button" onClick={() => moveTier(i, -1)} className="text-white/50 hover:text-white p-0.5"><ArrowUp className="w-3.5 h-3.5" /></button>
                      <button type="button" onClick={() => moveTier(i, 1)} className="text-white/50 hover:text-white p-0.5"><ArrowDown className="w-3.5 h-3.5" /></button>
                      <button type="button" onClick={() => { if (window.confirm(`Удалить тариф ${t.name}? Уже созданные доли останутся.`)) setF((s) => ({ ...s, tiers: s.tiers.filter((_, j) => j !== i) })); }} className="text-white/50 hover:text-red-400 p-0.5"><Trash2 className="w-3.5 h-3.5" /></button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="text-[11px] text-text-muted mt-2">Изменения применяются после «Сохранить». Цена, доля прибыли и лимит уже купленных долей не меняются — они фиксируются в момент покупки. Привилегии (ниже) берутся из тарифа текущие: изменили — инвесторы получат новые значения в течение минуты.</div>
        </CardContent>
      </Card>

      <Card className="bg-white/[0.03] border-white/10">
        <CardHeader className="pb-2"><CardTitle className="text-sm text-white">Привилегии фоундера</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="text-[11px] text-text-muted">Все привилегии действуют без ограничения по времени, пока игрок является фоундером: у него есть доля со статусом «Активна» или «Лимит достигнут». После «Выкуплена» / «Отменена» (если других долей нет) привилегии прекращаются, бесплатный City Pass Premium снимается. Если долей несколько — по каждому пункту берётся лучшее значение. Скидки на налог, вывод и ремонт умножаются с баффами ресурсов. Скорость вывода: «Моментально» — заявка отправляется автоматически сразу, «До 12 часов» — автоматически через 12 часов (вы можете одобрить раньше).</div>
          <div className="grid md:grid-cols-3 gap-3">
            {f.tiers.map((t, i) => {
              const pk = { ...EMPTY_PERKS, ...(t.perks || {}) };
              return (
                <div key={i} className="rounded-xl border border-amber-500/25 bg-amber-500/[0.04] p-3 space-y-2 text-xs" data-testid={`fp-perks-${t.id}`}>
                  <div className="font-bold text-amber-300">{t.name || t.id} · {money(t.price)}</div>
                  {PERKS.map(({ k, label, hint, max }) => (
                    <label key={k} className="flex items-center justify-between gap-2" title={hint}>
                      <span className="text-white/80">{label}</span>
                      <Input type="number" min="0" max={max} value={pk[k]} onChange={(e) => setPerk(i, k, e.target.value)} className="h-7 w-24 bg-black/40 border-white/10 text-xs" />
                    </label>
                  ))}
                  <label className="flex items-center justify-between gap-2"><span className="text-white/80">Скорость вывода</span>
                    <select value={pk.withdraw_speed || 'standard'} onChange={(e) => setPerk(i, 'withdraw_speed', e.target.value)} className={`${sel} w-44`} data-testid={`fp-wd-speed-${t.id}`}>
                      {Object.entries(WD_SPEED).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </label>
                  <label className="flex items-center justify-between gap-2"><span className="text-white/80">City Pass Premium бесплатно</span><Switch checked={!!pk.city_pass_premium} onCheckedChange={(v) => setPerk(i, 'city_pass_premium', v)} /></label>
                  <label className="flex items-center justify-between gap-2"><span className="text-white/80">Значок «💎 Инвестор» в профиле</span><Switch checked={!!pk.badge} onCheckedChange={(v) => setPerk(i, 'badge', v)} /></label>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
      </>}

      {section === 'holdings' && apps.length > 0 && <Card className="bg-white/[0.03] border-white/10">
        <CardHeader className="pb-2 flex-row items-center justify-between">
          <CardTitle className="text-sm text-white">Старые заявки (до прямой покупки)</CardTitle>
          <select value={appFilter} onChange={(e) => setAppFilter(e.target.value)} className={sel}>
            <option value="open">Открытые</option>
            <option value="">Все</option>
            {Object.entries(APP_ST).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </CardHeader>
        <CardContent className="overflow-auto">
          {apps.length === 0 ? <div className="text-xs text-text-muted">Заявок нет</div> : (
            <table className="w-full text-xs min-w-[760px]">
              <thead className="text-text-muted"><tr className="text-left"><th className="p-1">Дата</th><th className="p-1">Игрок</th><th className="p-1">Тариф</th><th className="p-1">Цена</th><th className="p-1">Комментарий</th><th className="p-1">Статус</th><th className="p-1" /></tr></thead>
              <tbody>
                {apps.map((a) => (
                  <tr key={a.id} className="border-t border-white/5">
                    <td className="p-1 whitespace-nowrap">{fmtDate(a.created_at)}</td>
                    <td className="p-1">@{a.username || '—'}<div className="text-[10px] text-text-muted">{a.email || ''}{a.telegram_id ? ` · TG ${a.telegram_id}` : ''}</div></td>
                    <td className="p-1">{a.tier_name}<div className="text-[10px] text-text-muted">{a.share_pct}% · лимит {money(a.max_payout, a.currency)}</div></td>
                    <td className="p-1">{money(a.price, a.currency)}</td>
                    <td className="p-1 max-w-[200px] truncate" title={a.comment}>{a.comment || '—'}</td>
                    <td className="p-1">{APP_ST[a.status] || a.status}</td>
                    <td className="p-1 whitespace-nowrap">
                      {(a.status === 'new' || a.status === 'contacted') && (
                        <div className="flex gap-1">
                          {a.status === 'new' && <Button size="sm" variant="outline" className="h-7 text-[11px]" onClick={() => appStatus(a, 'contacted')}>Связались</Button>}
                          <Button size="sm" className="h-7 text-[11px] bg-emerald-600 hover:bg-emerald-500" onClick={() => appStatus(a, 'approved')}>Одобрить</Button>
                          <Button size="sm" variant="outline" className="h-7 text-[11px] text-red-300" onClick={() => appStatus(a, 'rejected')}>Отклонить</Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>}

      {section === 'holdings' && <Card className="bg-white/[0.03] border-white/10">
        <CardHeader className="pb-2"><CardTitle className="text-sm text-white">Доли игроков</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-end gap-2 text-xs">
            <label>Игрок (id, @username, e-mail, Telegram id)
              <Input value={manual.user} onChange={(e) => setManual((m) => ({ ...m, user: e.target.value }))} className="h-8 w-56 mt-1 bg-black/40 border-white/10 text-xs" />
            </label>
            <label>Тариф
              <select value={manual.tier_id || f.tiers[0]?.id || ''} onChange={(e) => setManual((m) => ({ ...m, tier_id: e.target.value }))} className={`${sel} block mt-1`}>
                {f.tiers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </label>
            <label>Цена (пусто — по тарифу)
              <Input type="number" min="0" value={manual.price} onChange={(e) => setManual((m) => ({ ...m, price: e.target.value }))} className="h-8 w-28 mt-1 bg-black/40 border-white/10 text-xs" />
            </label>
            <Button size="sm" variant="outline" onClick={addManual} disabled={!manual.user}>Добавить долю вручную (сделка вне игры)</Button>
          </div>
          <div className="overflow-auto">
            {holds.length === 0 ? <div className="text-xs text-text-muted">Долей пока нет</div> : (
              <table className="w-full text-xs min-w-[760px]">
                <thead className="text-text-muted"><tr className="text-left"><th className="p-1">С</th><th className="p-1">Игрок</th><th className="p-1">Тариф</th><th className="p-1">Цена</th><th className="p-1">Выплачено / лимит</th><th className="p-1">Статус</th><th className="p-1" /></tr></thead>
                <tbody>
                  {holds.map((h) => {
                    const pct = Math.min(100, (Number(h.paid_total || 0) / Math.max(1e-9, Number(h.max_payout || 0))) * 100);
                    return (
                      <tr key={h.id} className="border-t border-white/5">
                        <td className="p-1 whitespace-nowrap">{fmtDate(h.created_at)}</td>
                        <td className="p-1"><button type="button" className="text-amber-200 hover:underline" onClick={() => setOpenUser(h.user_id)}>@{h.username || h.user_id}</button>
                          <div className="text-[10px] text-text-muted">{h.paid_in_app ? 'куплено с баланса' : 'добавлено админом'}</div></td>
                        <td className="p-1">{h.tier_name}<div className="text-[10px] text-text-muted">{h.share_pct}% прибыли · лимит {h.cap_pct}%</div></td>
                        <td className="p-1">{money(h.price, h.currency)}</td>
                        <td className="p-1 w-48">
                          <div>{money(h.paid_total, h.currency)} / {money(h.max_payout, h.currency)}</div>
                          <div className="h-1.5 rounded bg-white/10 mt-1 overflow-hidden"><div className="h-full bg-amber-400" style={{ width: `${pct}%` }} /></div>
                        </td>
                        <td className="p-1">
                          <select value={h.status} onChange={(e) => holdStatus(h, e.target.value)} className={sel}>
                            {Object.entries(HOLD_ST).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                          </select>
                        </td>
                        <td className="p-1"><Button size="sm" variant="outline" className="h-7 text-[11px]" onClick={() => payout(h)}>+ выплата</Button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          <div className="text-[11px] text-text-muted">«+ выплата» зачисляет сумму на РЕАЛЬНЫЙ баланс игрока (её можно вывести), в его истории появляется операция «Выплата Founder Pass от администрации», игрок получает уведомление, а во вкладке «Доходы» сумма учитывается как расход «Выплаты по Founder Pass». Больше остатка до лимита начислить нельзя. Когда выплаты доходят до лимита, доля получает статус «Лимит достигнут» — игрок остаётся фоундером со всеми привилегиями.</div>
        </CardContent>
      </Card>}

      <FounderInvestorCard userId={openUser} token={token} onClose={() => setOpenUser(null)} onChanged={load} />
    </div>
  );
}
