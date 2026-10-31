/** «Игры» — a side button under «Задания» on «Бизнесы» (same size). It shimmers so the games are easy to spot and
 *  opens the «Игры» page: the Arcade games + the promotion game, rewards and lists of leaders.
 *  Hidden until the admin switches it on (admin → «Аркада» → «Кнопка «Игры»», GET /api/games/config). */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Gamepad2 } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslation } from '@/lib/translations';

export default function EventBanner() {
  const navigate = useNavigate();
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const [on, setOn] = useState(false);
  useEffect(() => {
    let alive = true;
    fetch(`${process.env.REACT_APP_BACKEND_URL || ''}/api/games/config`).then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (alive) setOn(!!d?.button_enabled); }).catch(() => {});
    return () => { alive = false; };
  }, []);
  if (!on) return null;
  return (
    <button type="button" onClick={() => navigate('/games')} data-testid="biz-side-game"
      className="games-shimmer relative overflow-hidden w-14 h-14 sm:w-16 sm:h-16 rounded-xl bg-gradient-to-b from-amber-400/25 via-fuchsia-500/15 to-cyber-cyan/15 border border-amber-300/60 flex flex-col items-center justify-center gap-0.5 text-amber-200 hover:brightness-110 active:scale-95 transition-all"
      aria-label={t('gm_title')}>
      <Gamepad2 className="relative z-[1] w-5 h-5" />
      <span className="relative z-[1] text-[8px] sm:text-[9px] font-bold uppercase tracking-wide text-center leading-tight">{t('gm_title')}</span>
      <style>{`.games-shimmer{box-shadow:0 0 12px rgba(251,191,36,.35)}
.games-shimmer::before{content:"";position:absolute;inset:-40%;background:linear-gradient(115deg,transparent 35%,rgba(255,255,255,.55) 48%,rgba(253,224,71,.35) 52%,transparent 65%);transform:translateX(-120%);animation:gamesShine 2.6s ease-in-out infinite}
@keyframes gamesShine{0%{transform:translateX(-120%)}55%,100%{transform:translateX(120%)}}
@media (prefers-reduced-motion: reduce){.games-shimmer::before{animation:none;opacity:0}}`}</style>
    </button>
  );
}
