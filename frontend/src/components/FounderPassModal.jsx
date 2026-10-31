/**
 * FounderPassModal — the private investor pool (backend/founder_pass.py).
 * Plans with price / share of net profit / places left, the chosen plan's
 * terms (payout cap, buy-back right, disclaimer) and «Купить за …»: paid right away from the REAL balance.
 * Not enough money → the top-up modal with the missing amount (direct TON top-up, then the purchase runs).
 * The player's own shares show «received / cap» progress. Every number comes from the admin («Founder Pass» tab).
 */
import { useCallback, useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { Gem, MessageCircle } from 'lucide-react';
import SupportModal from '@/components/SupportModal';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslation } from '@/lib/translations';
import { fill } from '@/lib/translationsMore';
import LandPurchaseTopUpModal from '@/components/LandPurchaseTopUpModal';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/founder-pass`;
const tok = () => localStorage.getItem('token') || localStorage.getItem('ton_city_token');
const ERR = { fp_closed: 'fp_err_closed', fp_sold_out: 'fp_err_sold', fp_already: 'fp_err_already', fp_busy: 'fp_err_busy' };

export function fmtMoney(v, currency = 'TON') {
  const n = Number(v || 0).toLocaleString('en-US', { maximumFractionDigits: 2 });
  return currency === 'USD' ? `$${n}` : `${n} TON`;
}

/** Perk lines of a plan (or of the player's active shares) — [{icon, text}] in the player's language. */
export function perkLines(pk, t) {
  if (!pk) return [];
  const out = [];
  const n = (v) => Number(v || 0);
  if (n(pk.sale_tax_discount_pct) > 0) out.push({ icon: '🏷️', text: fill(t('fp_pk_tax'), { p: n(pk.sale_tax_discount_pct) }) });
  if (n(pk.withdraw_fee_discount_pct) > 0) out.push({ icon: '💸', text: fill(t('fp_pk_wd'), { p: n(pk.withdraw_fee_discount_pct) }) });
  if (n(pk.repair_discount_pct) > 0) out.push({ icon: '🛠️', text: fill(t('fp_pk_repair'), { p: n(pk.repair_discount_pct) }) });
  if (n(pk.welcome_bonus_city) > 0) out.push({ icon: '🎁', text: fill(t('fp_pk_bonus'), { n: n(pk.welcome_bonus_city).toLocaleString('en-US') }) });
  if (pk.withdraw_speed === 'instant') out.push({ icon: '⚡', text: t('fp_pk_wd_instant') });
  if (pk.withdraw_speed === 'h12') out.push({ icon: '⏱️', text: t('fp_pk_wd_h12') });
  if (pk.city_pass_premium) out.push({ icon: '⭐', text: t('fp_pk_pass') });
  if (n(pk.arcade_extra_attempts) > 0) out.push({ icon: '🎮', text: fill(t('fp_pk_att'), { n: n(pk.arcade_extra_attempts) }) });
  if (n(pk.arcade_xp_bonus_pct) > 0) out.push({ icon: '⚡', text: fill(t('fp_pk_xp'), { p: n(pk.arcade_xp_bonus_pct) }) });
  if (pk.badge) out.push({ icon: '💎', text: t('fp_pk_badge') });
  return out;
}

function PerkList({ lines }) {
  if (!lines.length) return null;
  return (
    <ul className="space-y-1">
      {lines.map((l, i) => (
        <li key={i} className="flex items-start gap-1.5 text-[11px] text-white/85"><span className="shrink-0">{l.icon}</span><span>{l.text}</span></li>
      ))}
    </ul>
  );
}

export function openContact(url) {
  if (!url) return;
  try {
    const tg = window.Telegram?.WebApp;
    if (tg && /^https:\/\/t\.me\//.test(url) && tg.openTelegramLink) { tg.openTelegramLink(url); return; }
  } catch (_) { /* fall through */ }
  window.open(url, '_blank', 'noopener');
}

export default function FounderPassModal({ open, onClose }) {
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const [data, setData] = useState(null);
  const [sel, setSel] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}?lang=${lang}`, { headers: { Authorization: `Bearer ${tok()}` } });
      setData(r.ok ? await r.json() : { visible: false });
    } catch (_) { setData({ visible: false }); }
  }, [lang]);

  useEffect(() => { if (open) { setSel(null); load(); } }, [open, load]);

  const cur = 'TON';
  const capPct = data?.cap_pct || 300;
  const [topUp, setTopUp] = useState(null);
  const [supportOpen, setSupportOpen] = useState(false);   // «Есть вопросы?» → the support chat       // {tier, priceTon, balanceTon} when the real balance is short

  const buy = async (tier, { fromTopUp = false } = {}) => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/buy`, {
        method: 'POST', headers: { Authorization: `Bearer ${tok()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier_id: tier.id }),
      });
      const d = await r.json().catch(() => ({}));
      if (r.status === 402 && d.detail?.code === 'fp_insufficient') {
        if (fromTopUp) { toast.error(t('topUpTitle')); return; }
        setTopUp({ tier, priceTon: Number(d.detail.price || tier.price), balanceTon: Number(d.detail.balance || 0) });
        return;
      }
      if (!r.ok) { toast.error(t(ERR[d.detail] || 'fp_err')); return; }
      toast.success(t('fp_bought'));
      if (d.balance_ton !== undefined) window.dispatchEvent(new CustomEvent('balanceUpdate', { detail: { balance: d.balance_ton, bonus_balance: d.bonus_balance } }));
      await load();
    } catch (_) { toast.error(t('fp_err')); } finally { setBusy(false); }
  };

  const tiers = data?.tiers || [];
  const holdings = data?.holdings || [];
  const selTier = tiers.find((x) => x.id === sel);
  const hasActive = (tierId) => holdings.some((h) => h.tier_id === tierId && h.status === 'active');

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#0d1526] border-amber-500/30 rounded-2xl p-5 sm:max-w-md max-h-[88vh] overflow-y-auto gap-0" data-testid="founder-pass-modal">
        <DialogTitle className="flex items-center gap-2 text-amber-400 text-lg font-bold">
          <Gem className="w-5 h-5" /> {t('fp_pool_title')}
        </DialogTitle>
        <p className="text-xs text-text-muted mt-1 mb-4">{t('fp_pool_desc')}</p>

        {data === null && <div className="text-xs text-text-muted py-6 text-center">…</div>}
        {data && !data.visible && <div className="text-xs text-text-muted py-6 text-center">{t('fp_err_closed')}</div>}

        {data?.visible && (
          <>
            {data.my_perks?.active && (
              <div className="mb-3 p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/25" data-testid="founder-pass-my-perks">
                <div className="text-[11px] uppercase tracking-wide text-emerald-300 font-bold mb-1.5">💎 {t('fp_my_perks')}</div>
                <PerkList lines={perkLines(data.my_perks, t)} />
                <div className="text-[10px] text-emerald-200/70 mt-1.5">♾️ {t('fp_forever')}</div>
              </div>
            )}
            {holdings.length > 0 && (
              <div className="mb-4 space-y-2" data-testid="founder-pass-holdings">
                <div className="text-[11px] uppercase tracking-wide text-amber-300/90 font-bold">{t('fp_my')}</div>
                {holdings.map((h) => {
                  const pct = Math.min(100, (Number(h.paid_total || 0) / Math.max(1e-9, Number(h.max_payout || 0))) * 100);
                  return (
                    <div key={h.id} className="rounded-xl bg-amber-500/5 border border-amber-500/25 p-3">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-amber-300">{h.tier_name}</span>
                        <span className="text-text-muted">{t(`fp_st_${h.status}`)}</span>
                      </div>
                      <div className="h-2 rounded-full bg-white/10 mt-2 overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-amber-400 to-emerald-400" style={{ width: `${pct}%` }} />
                      </div>
                      <div className="text-[11px] text-white/80 mt-1.5">
                        {fill(t('fp_paid'), { a: fmtMoney(h.paid_total, cur), b: fmtMoney(h.max_payout, cur) })}
                        <span className="text-text-muted"> · {fill(t('fp_profit'), { p: h.share_pct })}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="space-y-2.5 mb-4">
              {tiers.map((p) => {
                const active = sel === p.id;
                return (
                  <button
                    type="button" key={p.id} onClick={() => setSel(active ? null : p.id)} data-testid={`founder-tier-${p.id}`}
                    className={`w-full text-left p-3.5 rounded-2xl border transition-all bg-black/30 ${active ? 'border-amber-400 shadow-lg shadow-amber-500/10' : 'border-white/10 hover:border-amber-500/50'} ${p.sold_out ? 'opacity-60' : ''}`}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">{p.name}</span>
                          {p.badge === 'popular' && <span className="text-[9px] px-1.5 rounded bg-cyber-cyan/15 text-cyber-cyan border border-cyber-cyan/30">{t('fp_popular')}</span>}
                          {p.badge === 'vip' && <span className="text-[9px] px-1.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">VIP</span>}
                        </div>
                        <div className="text-lg font-black text-white">{fmtMoney(p.price, cur)}</div>
                      </div>
                      <div className="text-right">
                        <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-bold">{fill(t('fp_profit'), { p: p.share_pct })}</span>
                        <div className={`text-[10px] mt-1 ${p.sold_out ? 'text-red-400' : 'text-text-muted'}`}>
                          {p.sold_out ? t('fp_sold_out') : fill(t('fp_left'), { a: p.slots_left, b: p.slots_total })}
                        </div>
                      </div>
                    </div>
                    {perkLines(p.perks, t).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {perkLines(p.perks, t).map((l, i) => (
                          <span key={i} className="text-[10px] leading-none px-1.5 py-1 rounded-md bg-white/5 border border-white/10 text-white/75">{l.icon} {l.text}</span>
                        ))}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {selTier && (
              <div className="p-4 rounded-2xl bg-amber-950/20 border border-amber-500/30 mb-3 text-xs space-y-2" data-testid="founder-pass-terms">
                <div className="flex justify-between"><span className="text-text-muted">{t('fp_selected')}:</span><span className="font-bold text-amber-300">{selTier.name}</span></div>
                <div className="flex justify-between"><span className="text-text-muted">{t('fp_price')}:</span><span className="font-bold text-white">{fmtMoney(selTier.price, cur)}</span></div>
                <div className="flex justify-between"><span className="text-text-muted">{t('fp_share')}:</span><span className="font-bold text-white">{selTier.share_pct}%</span></div>
                <div className="flex justify-between"><span className="text-text-muted">{fill(t('fp_cap'), { p: capPct })}:</span><span className="font-bold text-emerald-400">{fmtMoney(selTier.max_payout, cur)}</span></div>
                {perkLines(selTier.perks, t).length > 0 && (
                  <div className="pt-2 border-t border-amber-500/20" data-testid="founder-pass-perks">
                    <div className="text-text-muted mb-1">{t('fp_perks')}:</div>
                    <PerkList lines={perkLines(selTier.perks, t)} />
                    <div className="text-[10px] text-amber-200/70 mt-1.5">♾️ {t('fp_forever')}</div>
                  </div>
                )}
                <p className="text-[10px] text-amber-200/80 pt-2 border-t border-amber-500/20 leading-relaxed">
                  ⚠️ {fill(t('fp_buyout'), { p: capPct, max: fmtMoney(selTier.max_payout, cur) })}
                </p>
                <div className="text-[10px] text-white/60 pt-1">{fill(t('fp_pay_real'), { b: fmtMoney(data.balance_ton, cur) })}</div>
                <button
                  type="button" disabled={busy || selTier.sold_out || !data.enabled || hasActive(selTier.id)} onClick={() => buy(selTier)} data-testid="founder-pass-buy"
                  className="w-full py-2.5 mt-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black rounded-xl transition-all disabled:opacity-40"
                >
                  {selTier.sold_out ? t('fp_sold_out') : hasActive(selTier.id) ? t('fp_err_already') : fill(t('fp_buy'), { p: fmtMoney(selTier.price, cur) })}
                </button>
              </div>
            )}

            {data.note && <p className="text-[11px] text-white/80 whitespace-pre-line mb-2">{data.note}</p>}
            <p className="text-[10px] text-text-muted leading-relaxed">{t('fp_disclaimer')}</p>
            {/* «Есть вопросы?» — opens the in-app support chat */}
            <button type="button" onClick={() => setSupportOpen(true)} data-testid="founder-pass-support"
              className="mt-2 text-[11px] text-amber-300/90 hover:text-amber-200 flex items-center gap-1">
              <MessageCircle className="w-3 h-3" />{t('fp_questions')}
            </button>
          </>
        )}
      </DialogContent>
      <SupportModal open={supportOpen} onOpenChange={setSupportOpen} language={lang} />
      <LandPurchaseTopUpModal
        isOpen={!!topUp}
        onClose={() => setTopUp(null)}
        cell={topUp ? { priceTon: topUp.priceTon } : null}
        userBalanceTon={topUp?.balanceTon || 0}
        token={tok()}
        onConfirmPurchase={async () => { const tier = topUp?.tier; if (tier) await buy(tier, { fromTopUp: true }); }}
        linkPrompt={t('fp_topup_link')}
        testid="fp-topup-modal"
      />
    </Dialog>
  );
}
