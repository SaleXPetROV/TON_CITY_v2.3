/** A card that opens the Arcade (shown only when the Arcade is visible to this player). */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Gamepad2 } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslation } from '@/lib/translations';
import { fill } from '@/lib/translationsMore';
import { GAME_ICON, arcadeCall } from '@/arcade/core';

export default function ArcadeEntry({ className = '' }) {
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const navigate = useNavigate();
  const [hub, setHub] = useState(null);
  useEffect(() => { arcadeCall('/arcade').then(setHub).catch(() => setHub(null)); }, []);
  if (!hub?.visible || !hub.games?.length) return null;
  const pending = (hub.pending_rewards || []).length;
  return (
    <button type="button" onClick={() => navigate('/arcade')} data-testid="arcade-entry"
      className={`w-full relative overflow-hidden rounded-2xl border border-fuchsia-400/30 bg-gradient-to-r from-[#1a0b2e] via-[#14143a] to-[#0b1d3a] p-3 flex items-center gap-3 text-left active:scale-[0.99] transition-transform ${className}`}>
      <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyber-cyan to-fuchsia-500 flex items-center justify-center shrink-0"><Gamepad2 className="w-6 h-6 text-white" /></div>
      <div className="flex-1 min-w-0">
        <div className="font-bold text-white text-sm flex items-center gap-1.5">{t('ar_title')}
          {pending > 0 && <span className="text-[10px] font-black text-[#1a1206] bg-amber-300 rounded-full px-1.5">{pending}</span>}
        </div>
        <div className="text-[11px] text-white/70 truncate">{fill(t('ar_entry_sub'), { n: hub.games.length })}</div>
      </div>
      <div className="hidden min-[360px]:flex -space-x-1 text-lg">{hub.games.slice(0, 4).map((g) => <span key={g.id}>{GAME_ICON[g.id]}</span>)}</div>
      <ChevronRight className="w-4 h-4 text-white/60 shrink-0" />
    </button>
  );
}
