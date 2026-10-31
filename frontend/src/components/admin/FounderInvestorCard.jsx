/**
 * FounderInvestorCard — the admin's full card of a Founder Pass investor
 * (GET /api/admin/founder-pass/investors/{id}): account, balances, money summary, founder perks that apply now,
 * every share with its payouts (+ a payout form → the player's REAL balance), businesses, credits, City Pass,
 * transactions, withdrawals and the raw account document. Russian only (admin).
 */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Gem, Copy } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/admin/founder-pass`;
const HOLD_ST = { active: 'Активна', completed: 'Лимит достигнут', bought_out: 'Выкуплена', cancelled: 'Отменена' };
const WD = { standard: 'обычный (до 24 ч)', h12: 'до 12 часов', instant: 'моментальный' };
const ton = (v) => `${Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 4 })} TON`;
const dt = (s) => { if (!s) return '—'; try { return new Date(String(s).replace(' ', 'T')).toLocaleString('ru-RU'); } catch (_) { return String(s); } };

function Row({ k, v, mono }) {
  return (
    <div className="flex justify-between gap-3 py-1 border-b border-white/5 text-xs">
      <span className="text-text-muted shrink-0">{k}</span>
      <span className={`text-white text-right break-all ${mono ? 'font-mono text-[11px]' : ''}`}>{v === undefined || v === null || v === '' ? '—' : v}</span>
    </div>
  );
}

function Box({ title, children, testid }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3" data-testid={testid}>
      <div className="text-[11px] uppercase tracking-wide font-bold text-amber-300/90 mb-2">{title}</div>
      {children}
    </div>
  );
}

function PayoutForm({ h, token, onDone }) {
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const left = Math.max(0, Number(h.max_payout || 0) - Number(h.paid_total || 0));
  const send = async () => {
    const a = Number(String(amount).replace(',', '.'));
    if (!a) return;
    if (!window.confirm(a > 0 ? `Зачислить ${a} TON на реальный баланс @${h.username}?` : `Списать ${-a} TON с реального баланса @${h.username} (корректировка)?`)) return;
    setBusy(true);
    try {
      await axios.post(`${API}/holdings/${h.id}/payout`, { amount: a, note }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(a > 0 ? 'Выплата зачислена на реальный баланс' : 'Корректировка проведена');
      setAmount(''); setNote(''); onDone();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Ошибка'); } finally { setBusy(false); }
  };
  if (!(h.status === 'active' || h.status === 'completed')) return null;
  return (
    <div className="flex flex-wrap items-end gap-2 mt-2">
      <label className="text-[11px] text-text-muted">Сумма, TON (осталось {ton(left)})
        <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} className="h-8 w-32 mt-1 bg-black/40 border-white/10 text-xs" data-testid={`fp-pay-amount-${h.id}`} />
      </label>
      <label className="text-[11px] text-text-muted flex-1 min-w-[140px]">Комментарий
        <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="например: прибыль за октябрь" className="h-8 mt-1 bg-black/40 border-white/10 text-xs" />
      </label>
      <Button size="sm" disabled={busy || !amount} onClick={send} className="h-8 bg-emerald-600 hover:bg-emerald-500" data-testid={`fp-pay-send-${h.id}`}>Начислить</Button>
    </div>
  );
}

export default function FounderInvestorCard({ userId, token, onClose, onChanged }) {
  const [d, setD] = useState(null);
  const [raw, setRaw] = useState(false);
  const load = useCallback(async () => {
    if (!userId) return;
    try {
      const r = await axios.get(`${API}/investors/${encodeURIComponent(userId)}`, { headers: { Authorization: `Bearer ${token}` } });
      setD(r.data);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Не удалось загрузить игрока'); }
  }, [userId, token]);
  useEffect(() => { setD(null); setRaw(false); load(); }, [load]);

  const u = d?.user || {};
  const s = d?.summary || {};
  const pk = d?.perks || {};
  const copy = (v) => { try { navigator.clipboard.writeText(String(v)); toast.success('Скопировано'); } catch (_) { /* noop */ } };

  return (
    <Dialog open={!!userId} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#0d1526] border-amber-500/30 rounded-2xl p-4 sm:max-w-4xl max-h-[90vh] overflow-y-auto gap-3" data-testid="fp-investor-card">
        <DialogTitle className="flex items-center gap-2 text-amber-300 text-lg font-bold">
          <Gem className="w-5 h-5" /> @{u.username || '…'} {pk.active ? <span className="text-xs text-emerald-300 font-semibold">· фоундер</span> : d && <span className="text-xs text-white/40">· не фоундер</span>}
        </DialogTitle>
        {!d ? <div className="text-xs text-text-muted py-8 text-center">Загрузка…</div> : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {[['Вложено', ton(s.invested)], ['Выплачено по Founder Pass', `${ton(s.paid)} / ${ton(s.max_payout)}`], ['Реальный баланс', ton(u.balance_ton)], ['Бонусный баланс', ton(u.bonus_balance)],
                ['Пополнено', ton(s.deposits)], ['Выведено', ton(s.withdrawn)], ['Вывод в ожидании', ton(s.withdraw_pending)], ['Долг по кредитам', ton(s.active_debt)],
                ['Платформа получила от игрока', ton(s.platform_received)], ['Платформа выплатила игроку', ton(s.platform_paid)], ['Бизнесов', s.businesses], ['Рефералов', s.referrals]].map(([k, v]) => (
                <div key={k} className="rounded-xl bg-white/5 border border-white/10 p-2"><div className="text-[10px] text-text-muted">{k}</div><div className="text-sm font-bold text-white mt-0.5">{v}</div></div>
              ))}
            </div>

            <div className="grid md:grid-cols-2 gap-3">
              <Box title="Аккаунт">
                <Row k="ID" v={<span className="inline-flex items-center gap-1">{u.id}<button type="button" onClick={() => copy(u.id)}><Copy className="w-3 h-3 text-white/50" /></button></span>} mono />
                <Row k="Ник / имя" v={`@${u.username || '—'} · ${u.display_name || '—'}`} />
                <Row k="E-mail" v={u.email} />
                <Row k="Telegram" v={[u.telegram_username && `@${u.telegram_username}`, u.telegram_id && `id ${u.telegram_id}`].filter(Boolean).join(' · ')} />
                <Row k="Кошелёк" v={u.wallet_address} mono />
                <Row k="Язык / часовой пояс" v={`${u.language || '—'} · ${u.timezone || '—'}`} />
                <Row k="Регистрация" v={dt(u.created_at)} />
                <Row k="Последний вход" v={dt(u.last_login)} />
                <Row k="IP / устройство" v={`${u.last_ip || '—'} · ${u.last_device || '—'} · ${u.last_browser || ''}`} />
                <Row k="Пригласил" v={u.referrerId} mono />
                <Row k="Альянс" v={u.alliance_name ? `${u.alliance_emblem || ''} ${u.alliance_name} [${u.alliance_tag || ''}]` : ''} />
                <Row k="Блокировка" v={u.is_blocked ? `⛔ ${u.block_reason || 'да'}` : 'нет'} />
                <Row k="Вывод заблокирован" v={u.withdrawal_blocked ? 'да' : 'нет'} />
                <Row k="Админ" v={u.is_admin ? 'да' : 'нет'} />
              </Box>
              <Box title="Привилегии, которые действуют сейчас" testid="fp-investor-perks">
                {!pk.active ? <div className="text-xs text-text-muted">Игрок сейчас не фоундер — привилегии не действуют.</div> : (
                  <>
                    <Row k="Скидка на налог с продаж ресурсов" v={`${pk.sale_tax_discount_pct || 0}%`} />
                    <Row k="Скидка на комиссию вывода" v={`${pk.withdraw_fee_discount_pct || 0}%`} />
                    <Row k="Скорость вывода" v={WD[pk.withdraw_speed] || pk.withdraw_speed} />
                    <Row k="Скидка на ремонт" v={`${pk.repair_discount_pct || 0}%`} />
                    <Row k="City Pass Premium бесплатно" v={pk.city_pass_premium ? 'да' : 'нет'} />
                    <Row k="Аркада: + попыток / + XP" v={`+${pk.arcade_extra_attempts || 0} / +${pk.arcade_xp_bonus_pct || 0}%`} />
                    <Row k="Значок «Инвестор»" v={pk.badge ? 'да' : 'нет'} />
                  </>
                )}
                <div className="mt-2 text-[11px] text-text-muted">Инвестор с {dt(u.investor?.since)} · City Pass: {d.city_pass ? `${d.city_pass.xp || 0} XP${d.city_pass.premium ? ', премиум' : ''}${d.city_pass.premium_source === 'founder_pass' ? ' (по Founder Pass)' : ''}` : '—'}</div>
              </Box>
            </div>

            <Box title="Доли и выплаты" testid="fp-investor-holdings">
              {(d.holdings || []).map((h) => (
                <div key={h.id} className="rounded-lg border border-amber-500/20 bg-amber-500/[0.03] p-2 mb-2">
                  <div className="flex flex-wrap justify-between gap-2 text-xs">
                    <span className="font-bold text-amber-200">{h.tier_name} · {ton(h.price)} · {h.share_pct}% прибыли</span>
                    <span className="text-white/70">{HOLD_ST[h.status] || h.status} · с {dt(h.created_at)} · {h.paid_in_app ? 'куплено с баланса' : 'добавлено админом'}</span>
                  </div>
                  <div className="text-xs text-white/80 mt-1">Выплачено {ton(h.paid_total)} из {ton(h.max_payout)} (лимит {h.cap_pct}%)</div>
                  {(h.payouts || []).length > 0 && (
                    <table className="w-full text-[11px] mt-1.5">
                      <thead className="text-text-muted"><tr className="text-left"><th className="p-0.5">Дата</th><th className="p-0.5">Сумма</th><th className="p-0.5">Комментарий</th><th className="p-0.5">Кто</th></tr></thead>
                      <tbody>{[...h.payouts].reverse().map((p, i) => (
                        <tr key={i} className="border-t border-white/5"><td className="p-0.5 whitespace-nowrap">{dt(p.at)}</td><td className={`p-0.5 ${p.amount < 0 ? 'text-red-300' : 'text-emerald-300'}`}>{p.amount > 0 ? '+' : ''}{ton(p.amount)}</td><td className="p-0.5">{p.note || '—'}</td><td className="p-0.5">{p.by}</td></tr>
                      ))}</tbody>
                    </table>
                  )}
                  <PayoutForm h={{ ...h, username: u.username }} token={token} onDone={() => { load(); onChanged?.(); }} />
                </div>
              ))}
            </Box>

            <div className="grid md:grid-cols-2 gap-3">
              <Box title={`Бизнесы (${(d.businesses || []).length})`}>
                {(d.businesses || []).length === 0 ? <div className="text-xs text-text-muted">Нет</div> : (d.businesses || []).map((b) => (
                  <Row key={b.id} k={`${b.business_type} · ур. ${b.level ?? '—'}`} v={`прочность ${Math.round(Number(b.durability ?? 100))}% · (${b.x ?? '—'}, ${b.y ?? '—'})`} />
                ))}
              </Box>
              <Box title={`Кредиты (${(d.credits || []).length})`}>
                {(d.credits || []).length === 0 ? <div className="text-xs text-text-muted">Нет</div> : (d.credits || []).map((c) => (
                  <Row key={c.id} k={`${c.lender_name || c.lender_type} · ${c.status}`} v={`${ton(c.amount)} · осталось ${ton(c.remaining)}`} />
                ))}
              </Box>
            </div>

            <Box title={`Операции (последние ${(d.transactions || []).length})`}>
              <div className="max-h-72 overflow-auto">
                <table className="w-full text-[11px] min-w-[640px]">
                  <thead className="text-text-muted sticky top-0 bg-[#0d1526]"><tr className="text-left"><th className="p-1">Дата</th><th className="p-1">Тип</th><th className="p-1">Сумма</th><th className="p-1">Статус</th><th className="p-1">Описание</th></tr></thead>
                  <tbody>{(d.transactions || []).map((t) => (
                    <tr key={t.id || t.created_at} className="border-t border-white/5">
                      <td className="p-1 whitespace-nowrap">{dt(t.created_at)}</td>
                      <td className="p-1">{t.tx_type || t.type}{t.priority && t.priority !== 'standard' ? <span className="ml-1 text-amber-300">⚡{t.priority}</span> : null}</td>
                      <td className="p-1 whitespace-nowrap">{ton(t.amount_ton ?? t.amount)}</td>
                      <td className="p-1">{t.status || '—'}</td>
                      <td className="p-1 max-w-[320px] truncate" title={t.description}>{t.description || '—'}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </Box>

            <div>
              <button type="button" className="text-[11px] text-white/60 hover:text-white underline" onClick={() => setRaw((v) => !v)}>{raw ? 'Скрыть' : 'Показать'} все поля аккаунта (как в базе)</button>
              {raw && <pre className="mt-2 max-h-80 overflow-auto rounded-lg bg-black/50 border border-white/10 p-2 text-[10px] text-white/80 whitespace-pre-wrap break-all" data-testid="fp-investor-raw">{JSON.stringify(u, null, 2)}</pre>}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
