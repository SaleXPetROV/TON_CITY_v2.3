/**
 * PlayerProfileModal — opens from the profile block (avatar / name / alliance)
 * on the «Бизнесы» page: avatar, @username, alliance (with a link to it), a few
 * stats, and — only for players the admin let in (backend/founder_pass.py) —
 * the «💎 Founder Pass» entry that opens the investor pool.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Shield, Gem, ChevronRight, BarChart3 } from 'lucide-react';
import SmartAvatar from '@/components/SmartAvatar';
import FounderPassModal from '@/components/FounderPassModal';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslation } from '@/lib/translations';
import { tonToCity, formatCity } from '@/lib/currency';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const tok = () => localStorage.getItem('token') || localStorage.getItem('ton_city_token');

function Stat({ label, value, accent }) {
  return (
    <div>
      <span className="text-text-muted block text-[11px]">{label}</span>
      <span className={`font-bold text-sm ${accent || 'text-white'}`}>{value}</span>
    </div>
  );
}

export default function PlayerProfileModal({ open, onClose, user, passLevel }) {
  const navigate = useNavigate();
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const [card, setCard] = useState(null);
  const [showFounder, setShowFounder] = useState(false);

  useEffect(() => {
    if (!open) { setShowFounder(false); return undefined; }
    let alive = true;
    let timer = null;
    // a slow / flaky network must not hide the Founder Pass entry: retry the card a few times
    const load = (attempt) => {
      fetch(`${API}/profile/card`, { headers: { Authorization: `Bearer ${tok()}` }, cache: 'no-store' })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((d) => { if (alive) setCard(d); })
        .catch(() => { if (alive && attempt < 3) timer = setTimeout(() => load(attempt + 1), 1200 * (attempt + 1)); });
    };
    load(0);
    return () => { alive = false; clearTimeout(timer); };
  }, [open]);

  const mainTon = card ? card.balance_ton : Number(user?.balance_ton || 0);
  const bonusTon = card ? card.bonus_balance : Number(user?.bonus_balance || 0);
  const alliance = user?.alliance_name ? `${user?.alliance_tag ? `[${user.alliance_tag}] ` : ''}${user.alliance_name}` : (user?.clan_name || '');
  let since = '';
  try { if (card?.registered_at) since = new Date(card.registered_at).toLocaleDateString(lang === 'zh' ? 'zh-CN' : lang); } catch (_) { since = ''; }

  return (
    <>
      <Dialog open={open && !showFounder} onOpenChange={(v) => { if (!v) onClose(); }}>
        <DialogContent className="bg-[#0d1526] border-white/10 rounded-2xl p-5 sm:max-w-sm gap-0" data-testid="player-profile-modal">
          <DialogTitle className="text-center text-xs uppercase tracking-[0.2em] text-text-muted font-bold">{t('fp_profile')}</DialogTitle>

          <div className="flex flex-col items-center mt-4 mb-5">
            <SmartAvatar
              avatar={user?.avatar}
              name={user?.display_name || user?.username}
              className="w-20 h-20 rounded-full border-2 border-cyber-cyan/60 shadow-lg shadow-cyber-cyan/20 text-2xl"
            />
            <div className="text-white font-bold text-xl mt-3" data-testid="profile-username">@{user?.username || 'user'}</div>
            {card?.investor && (
              <span className="mt-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/40" data-testid="profile-investor-badge">
                💎 {t('fp_investor')}
              </span>
            )}
            <button
              type="button" onClick={() => { onClose(); navigate('/alliance'); }}
              className="mt-1 flex items-center gap-1 text-xs text-text-muted hover:text-white" data-testid="profile-alliance"
            >
              <Shield className="w-3.5 h-3.5 text-cyber-cyan" />
              <span className={alliance ? 'text-fuchsia-200' : ''}>{alliance || t('fp_no_alliance')}</span>
              <ChevronRight className="w-3 h-3 opacity-60" />
            </button>
          </div>

          <div className="rounded-xl bg-black/30 border border-white/10 p-3 mb-4">
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-text-muted font-bold mb-2">
              <BarChart3 className="w-3.5 h-3.5" /> {t('fp_stats')}
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
              <Stat label={t('fp_balance')} value={`${formatCity(tonToCity(mainTon + bonusTon))} $CITY`} accent="text-cyber-cyan" />
              <Stat label={t('fp_businesses')} value={card ? card.businesses : '…'} />
              <Stat label={t('fp_main')} value={`${formatCity(tonToCity(mainTon))} $CITY`} />
              <Stat label={t('fp_bonus')} value={`${formatCity(tonToCity(bonusTon))} $CITY`} />
              {passLevel ? <Stat label={t('fp_pass_level')} value={passLevel} /> : null}
              {since ? <Stat label={t('fp_since')} value={since} /> : null}
            </div>
          </div>

          {card?.founder_pass && (
            <button
              type="button" onClick={() => setShowFounder(true)} data-testid="profile-founder-pass"
              className="w-full p-3.5 bg-gradient-to-r from-amber-950/50 via-yellow-900/20 to-slate-900 border border-amber-500/30 hover:border-amber-400 rounded-2xl transition-all flex items-center justify-between group text-left"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center">
                  <Gem className="w-5 h-5 text-amber-300" />
                </div>
                <div>
                  <div className="text-xs font-black text-amber-400 uppercase tracking-wide flex items-center gap-1.5">
                    {t('fp_title')}
                    <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1.5 rounded border border-amber-500/30">VIP</span>
                  </div>
                  <div className="text-[10px] text-text-muted">{t('fp_sub')}</div>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-white/40 group-hover:text-amber-400 transition-colors" />
            </button>
          )}
        </DialogContent>
      </Dialog>
      <FounderPassModal open={open && showFounder} onClose={() => setShowFounder(false)} />
    </>
  );
}
