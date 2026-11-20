/** Админка → Данные → игрок: «Путь новичка» — сколько шагов пройдено, и кнопка «Отметить пройденным». */
import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { formatErrorDetail } from '@/lib/apiErrors';
import { getResource } from '@/lib/resourceConfig';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;

export default function PlayerOnboardingCell({ userId, headers }) {
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);
  const hdr = useRef(headers);            // the parent makes a new headers object on every render
  hdr.current = headers;
  const load = useCallback(async () => {
    if (!userId) return;
    try { setSt((await axios.get(`${API}/admin/quests/onboarding/user/${userId}`, { headers: hdr.current })).data); } catch (_) { setSt(null); }
  }, [userId]);
  useEffect(() => { setSt(null); load(); }, [load]);

  const complete = async (rewardReceived) => {
    const q = rewardReceived
      ? 'Отметить «Путь новичка» пройденным и считать бесплатный ресурс тира 3 уже выданным?\nНаграды за шаги и ресурс НЕ начисляются.'
      : 'Отметить «Путь новичка» пройденным?\nНаграды за шаги НЕ начисляются. Бесплатный ресурс тира 3 игрок выберет сам в «Заданиях».';
    if (!window.confirm(q)) return;
    setBusy(true);
    try {
      setSt((await axios.post(`${API}/admin/quests/onboarding/user/${userId}/complete`, { reward_received: rewardReceived }, { headers: hdr.current })).data);
      toast.success('«Путь новичка» отмечен пройденным');
    } catch (e) {
      toast.error(formatErrorDetail(e?.response?.data?.detail) || 'Не удалось отметить');
    } finally { setBusy(false); }
  };

  const allowReward = async () => {
    if (!window.confirm('Снова показать игроку выбор бесплатного ресурса тира 3?\nЕсли он уже получал ресурс (например, в старом обучении), он сможет получить ещё один.')) return;
    setBusy(true);
    try {
      setSt((await axios.post(`${API}/admin/quests/onboarding/user/${userId}/allow-reward`, {}, { headers: hdr.current })).data);
      toast.success('Игрок снова может выбрать ресурс тира 3 в «Заданиях»');
    } catch (e) {
      toast.error(formatErrorDetail(e?.response?.data?.detail) || 'Не удалось');
    } finally { setBusy(false); }
  };

  return (
    <div className="p-2 rounded-lg bg-gray-900/40 col-span-2" data-testid="admin-player-onboarding">
      <div className="text-xs text-gray-500">Путь новичка</div>
      {!st ? (
        <div className="text-xs text-gray-400">…</div>
      ) : (
        <>
          <div className="text-xs mt-0.5">
            {st.completed
              ? <span className="text-green-400 font-bold">✅ Пройден ({st.done}/{st.total})</span>
              : <span className="text-amber-300 font-bold">⏳ Шагов пройдено: {st.done} из {st.total}</span>}
            <span className="text-gray-400"> · награда тира 3: </span>
            {st.reward_received
              ? <span className="text-white">{st.reward_choice ? `получена: ${getResource(st.reward_choice, 'ru').icon} ${getResource(st.reward_choice, 'ru').name}` : 'отмечена выданной'}</span>
              : <span className="text-gray-300">{st.completed ? 'ещё не выбрана' : 'нет'}</span>}
            {st.marked_by_admin_at && <span className="text-gray-500"> · отмечено админом {new Date(st.marked_by_admin_at).toLocaleDateString('ru')}</span>}
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5" data-testid="admin-player-quests-biz">
            Задания видят бизнес: {st.has_business === true ? <span className="text-green-400">да</span> : st.has_business === false ? <span className="text-amber-300">нет</span> : '—'}
            {' · '}цели на сегодня: {st.daily_today?.length ? st.daily_today.join(', ') : 'ещё не выданы'}
          </div>
          {st.completed && st.reward_received && (
            <div className="mt-2">
              <p className="text-[10px] text-gray-500 mb-1">Награда уже получена, поэтому игрок не видит окно выбора ресурса.</p>
              <Button size="sm" disabled={busy} variant="outline" onClick={allowReward} className="h-7 text-xs border-purple-500/50 text-purple-200" data-testid="admin-onboarding-allow-reward">
                Разрешить выбрать награду заново
              </Button>
            </div>
          )}
          {(!st.completed || !st.reward_received) && (
            <div className="flex flex-wrap gap-2 mt-2">
              {!st.completed && (
                <Button size="sm" disabled={busy} onClick={() => complete(false)} className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700" data-testid="admin-onboarding-complete">
                  Отметить пройденным
                </Button>
              )}
              <Button size="sm" disabled={busy} variant="outline" onClick={() => complete(true)} className="h-7 text-xs border-gray-600 text-gray-300" data-testid="admin-onboarding-complete-reward">
                {st.completed ? 'Считать награду выданной' : 'Пройден + награда уже выдана'}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
