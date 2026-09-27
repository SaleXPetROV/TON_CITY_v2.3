import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users, Menu, X, History, Store, Trophy, Settings, HelpCircle,
  ScrollText, Map as MapIcon, Lock, Shield, Wallet,
} from 'lucide-react';
import SmartAvatar from '@/components/SmartAvatar';
import ReferralsModal from '@/components/ReferralsModal';
import SupportModal from '@/components/SupportModal';
import BalanceOverviewModal from '@/components/BalanceOverviewModal';
import NotificationCenter, { NotificationBellIcon, useNotificationsCount } from '@/components/NotificationCenter';
import { useLanguage } from '@/context/LanguageContext';
import { tonToCity, formatCity } from '@/lib/currency';
import { showDevNotice } from '@/lib/devNotice';
import { ADMIN_PATH } from '@/lib/adminPath';

const T = {
  noAlliance: { ru: 'Без альянса', en: 'No alliance', es: 'Sin alianza', zh: '无联盟', fr: 'Sans alliance', de: 'Keine Allianz', ja: '同盟なし', ko: '동맹 없음', id: 'Tanpa aliansi' },
  cityPass: { ru: 'City Pass', en: 'City Pass', es: 'City Pass', zh: 'City Pass', fr: 'City Pass', de: 'City Pass', ja: 'City Pass', ko: 'City Pass', id: 'City Pass' },
  history: { ru: 'История', en: 'History', es: 'Historial', zh: '历史', fr: 'Historique', de: 'Verlauf', ja: '履歴', ko: '기록', id: 'Riwayat' },
  marketplace: { ru: 'Маркетплейс', en: 'Marketplace', es: 'Mercado', zh: '市场', fr: 'Marché', de: 'Marktplatz', ja: 'マーケット', ko: '마켓', id: 'Pasar' },
  leaderboard: { ru: 'Рейтинг', en: 'Rating', es: 'Ranking', zh: '排行榜', fr: 'Classement', de: 'Rangliste', ja: 'ランキング', ko: '랭킹', id: 'Peringkat' },
  settings: { ru: 'Настройки', en: 'Settings', es: 'Ajustes', zh: '设置', fr: 'Paramètres', de: 'Einstellungen', ja: '設定', ko: '설정', id: 'Pengaturan' },
  help: { ru: 'Помощь', en: 'Help', es: 'Ayuda', zh: '帮助', fr: 'Aide', de: 'Hilfe', ja: 'ヘルプ', ko: '도움말', id: 'Bantuan' },
  rules: { ru: 'Правила', en: 'Rules', es: 'Reglas', zh: '规则', fr: 'Règles', de: 'Regeln', ja: 'ルール', ko: '규칙', id: 'Aturan' },
  roadmap: { ru: 'Дорожная карта', en: 'Roadmap', es: 'Hoja de ruta', zh: '路线图', fr: 'Feuille de route', de: 'Roadmap', ja: 'ロードマップ', ko: '로드맵', id: 'Peta jalan' },
  admin: { ru: 'Админ-панель', en: 'Admin Panel', es: 'Panel de administración', zh: '管理面板', fr: 'Panneau admin', de: 'Admin-Panel', ja: '管理パネル', ko: '관리자 패널', id: 'Panel Admin' },
};

// Redesigned top block for the "My Businesses" page.
// Left 55%: avatar + username + alliance + $CITY balance.
// Right 45%: referrals / notifications / burger buttons + City Pass (locked).
export default function BusinessProfileHeader({ user, refreshBalance }) {
  const navigate = useNavigate();
  const { language: lang } = useLanguage();
  const tr = (k) => (T[k][lang] || T[k].ru);

  const [showReferrals, setShowReferrals] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showSupport, setShowSupport] = useState(false);
  const [showBalance, setShowBalance] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const notif = useNotificationsCount(user);

  const displayCity = tonToCity((user?.balance_ton || 0) + Number(user?.bonus_balance || 0));
  const allianceName = user?.alliance_name || user?.clan_name || tr('noAlliance');

  const menuItems = [
    { key: 'history', icon: History, to: '/history' },
    { key: 'marketplace', icon: Store, to: '/marketplace' },
    { key: 'leaderboard', icon: Trophy, to: '/leaderboard' },
    { key: 'settings', icon: Settings, to: '/settings' },
    { key: 'help', icon: HelpCircle, action: 'support' },
    { key: 'rules', icon: ScrollText, to: '/rules' },
    { key: 'roadmap', icon: MapIcon, to: '/roadmap' },
  ];

  const handleMenu = (item) => {
    setMenuOpen(false);
    if (item.action === 'support') { setShowSupport(true); return; }
    if (item.to) navigate(item.to);
  };

  return (
    <div className="tg-header-pad w-full" data-testid="business-profile-header">
      <div className="flex items-stretch gap-2 w-[calc(100vw-2rem)] lg:w-full max-w-full">
        {/* LEFT 55% */}
        <div className="w-[55%] min-w-0 flex flex-col gap-2">
          <div className="flex items-center gap-2.5 rounded-2xl bg-white/[0.04] border border-white/10 p-2.5">
            <SmartAvatar
              avatar={user?.avatar}
              name={user?.display_name || user?.username}
              className="w-11 h-11 sm:w-12 sm:h-12 rounded-full border-2 border-cyber-cyan/60 shadow-lg shadow-cyber-cyan/20 flex-shrink-0 text-base"
            />
            <div className="min-w-0 flex-1">
              <div className="text-white font-bold text-sm sm:text-base truncate" data-testid="header-username">
                @{user?.username || 'user'}
              </div>
              <div className="flex items-center gap-1 text-[11px] sm:text-xs text-text-muted truncate" data-testid="header-alliance">
                <Shield className="w-3 h-3 text-cyber-cyan shrink-0" />
                <span className="truncate">{allianceName}</span>
              </div>
            </div>
          </div>
          {/* $CITY balance — клик открывает модалку баланса (Пополнить/Вывести) */}
          <button
            type="button"
            onClick={() => setShowBalance(true)}
            data-testid="header-city-balance"
            aria-label="Balance"
            className="w-full flex items-center justify-between gap-2 rounded-2xl bg-gradient-to-r from-cyber-cyan/10 to-neon-purple/10 border border-cyber-cyan/20 px-3 py-2 hover:border-cyber-cyan/40 hover:brightness-110 active:scale-[0.99] transition-all text-left"
          >
            <div className="text-base sm:text-lg font-extrabold text-white leading-none truncate">
              {formatCity(displayCity)} <span className="text-yellow-400 text-xs align-middle">$CITY</span>
            </div>
            <Wallet className="w-5 h-5 text-green-400 shrink-0" data-testid="header-balance-wallet-icon" />
          </button>
        </div>

        {/* RIGHT 45% */}
        <div className="flex-1 min-w-0 flex flex-col gap-2">
          {/* Три кнопки одинаковой ширины — ряд растянут на всю колонку,
              чтобы City Pass ниже совпадал с ними по ширине (как на референсе). */}
          <div className="flex items-stretch gap-1.5 sm:gap-2 w-full">
            <button
              type="button"
              onClick={() => setShowReferrals(true)}
              data-testid="header-referrals-btn"
              className="flex-1 min-w-0 h-10 rounded-xl bg-white/[0.06] border border-white/10 text-cyber-cyan flex items-center justify-center hover:bg-white/10 transition-colors"
              aria-label="Referrals"
            >
              <Users className="w-5 h-5" />
            </button>
            <div className="flex-1 min-w-0">
              <NotificationBellIcon
                count={notif.count}
                hasCritical={notif.hasCritical}
                shake={notif.shake}
                onClick={() => setShowNotifications(true)}
                dataTestid="header-notif-bell"
                className="!w-full"
              />
            </div>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              data-testid="header-burger-btn"
              className="flex-1 min-w-0 h-10 rounded-xl bg-white/[0.06] border border-white/10 text-white flex items-center justify-center hover:bg-white/10 transition-colors"
              aria-label="Menu"
            >
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

          {/* City Pass — заблокирован (в разработке). Дизайн по референсу:
              градиентная карточка, название слева, замок в правом верхнем углу. */}
          <button
            type="button"
            onClick={() => showDevNotice(lang)}
            data-testid="header-city-pass"
            className="relative w-full flex-1 rounded-2xl border border-white/15 bg-gradient-to-br from-indigo-500/60 via-purple-500/45 to-blue-600/50 overflow-hidden text-left cursor-not-allowed shadow-lg shadow-indigo-500/20"
          >
            <div className="flex items-center h-full px-4 py-3">
              <span className="font-extrabold text-white text-sm sm:text-base tracking-wide drop-shadow">{tr('cityPass')}</span>
            </div>
            <span className="absolute top-2 right-2 w-6 h-6 rounded-lg bg-black/30 border border-white/25 flex items-center justify-center" data-testid="city-pass-progress">
              <Lock className="w-3.5 h-3.5 text-white/90" />
            </span>
          </button>
        </div>
      </div>

      {/* Burger dropdown menu */}
      <AnimatePresence>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-[80]" onClick={() => setMenuOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.18 }}
              className="absolute right-4 top-16 z-[90] w-56 rounded-2xl bg-[#12121c]/98 backdrop-blur-2xl border border-white/10 shadow-2xl shadow-black/60 p-2 space-y-1"
              data-testid="header-burger-menu"
            >
              {menuItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => handleMenu(item)}
                    data-testid={`header-menu-${item.key}`}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-white/85 hover:bg-white/8 hover:text-white transition-colors text-sm font-medium"
                  >
                    <span className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
                      <Icon className="w-4 h-4 text-cyber-cyan" />
                    </span>
                    {tr(item.key)}
                  </button>
                );
              })}

              {/* Admin-only entry — pinned to the very bottom of the menu */}
              {user?.is_admin && (
                <>
                  <div className="my-1 h-px bg-white/10" />
                  <button
                    type="button"
                    onClick={() => { setMenuOpen(false); navigate(ADMIN_PATH); }}
                    data-testid="header-menu-admin"
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-red-300 hover:bg-red-500/10 hover:text-red-200 transition-colors text-sm font-semibold"
                  >
                    <span className="w-8 h-8 rounded-lg bg-red-500/15 flex items-center justify-center shrink-0">
                      <Shield className="w-4 h-4 text-red-400" />
                    </span>
                    {tr('admin')}
                  </button>
                </>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <ReferralsModal open={showReferrals} onClose={() => setShowReferrals(false)} />
      <NotificationCenter open={showNotifications} onClose={() => setShowNotifications(false)} user={user} />
      <SupportModal open={showSupport} onOpenChange={setShowSupport} language={lang} currentUser={user} />
      <BalanceOverviewModal
        open={showBalance}
        onClose={() => setShowBalance(false)}
        user={user}
        onBalanceUpdate={() => { if (refreshBalance) refreshBalance(); }}
      />
    </div>
  );
}
