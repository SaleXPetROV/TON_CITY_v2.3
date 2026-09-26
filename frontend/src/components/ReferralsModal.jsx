import { useEffect, useState } from 'react';
import { Users, X } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

const L = {
  title: { ru: 'Мои рефералы', en: 'My referrals', es: 'Mis referidos', zh: '我的推荐', fr: 'Mes filleuls', de: 'Meine Empfehlungen', ja: '紹介一覧', ko: '내 추천', id: 'Referral saya' },
  total: { ru: 'Всего приглашено:', en: 'Total invited:', es: 'Total invitados:', zh: '总邀请:', fr: 'Total invités :', de: 'Eingeladen gesamt:', ja: '招待合計:', ko: '총 초대:', id: 'Total diundang:' },
  income: { ru: 'Доход:', en: 'Income:', es: 'Ingresos:', zh: '收入:', fr: 'Revenu :', de: 'Einnahmen:', ja: '収入:', ko: '수익:', id: 'Pendapatan:' },
  empty: { ru: 'У вас пока нет рефералов', en: 'You have no referrals yet', es: 'Aún no tienes referidos', zh: '您还没有推荐', fr: "Vous n'avez pas encore de filleuls", de: 'Noch keine Empfehlungen', ja: 'まだ紹介はありません', ko: '아직 추천이 없습니다', id: 'Belum ada referral' },
};

// Self-contained referrals list modal. Fetches /api/referrals/me and mirrors the
// legendary card styling used in Settings.
export default function ReferralsModal({ open, onClose }) {
  const { language: lang } = useLanguage();
  const tr = (k) => (L[k][lang] || L[k].ru);
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!open) return;
    const token = localStorage.getItem('token');
    fetch(`${API}/referrals/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setData(d); })
      .catch(() => {});
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
      data-testid="referral-modal-overlay"
    >
      <div
        className="referral-legendary rounded-2xl p-[1.5px] w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
        data-testid="referral-modal"
      >
        <div className="referral-legendary__inner rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" style={{ color: '#00E5FF' }} />
              <h3 className="text-lg font-extrabold text-white uppercase tracking-wide">{tr('title')}</h3>
            </div>
            <button onClick={onClose} data-testid="referral-modal-close" className="text-text-muted hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex items-center justify-between mb-4 text-sm">
            <span className="text-cyan-300/70">{tr('total')} <b className="text-white">{data?.count ?? 0}</b></span>
            <span className="text-cyan-300/70">{tr('income')} <b className="text-cyan-400">{(data?.total_earned_city ?? 0).toLocaleString()} $CITY</b></span>
          </div>

          <div className="referral-scroll" data-testid="referral-modal-list">
            {(!data?.referrals || data.referrals.length === 0) ? (
              <div className="text-center text-text-muted py-10 text-sm">{tr('empty')}</div>
            ) : (
              data.referrals.map((r, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-3 rounded-xl bg-white/5 border border-white/5 mb-2" data-testid={`referral-row-${i}`}>
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-7 h-7 rounded-full bg-cyan-400/20 text-cyan-300 flex items-center justify-center text-xs font-bold shrink-0">
                      {(r.username || 'U')[0].toUpperCase()}
                    </span>
                    <span className="text-white text-sm truncate">{r.username}</span>
                  </div>
                  <span className="text-cyan-400 font-bold text-sm whitespace-nowrap">+{(r.earned_city ?? 0).toLocaleString()} $CITY</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
