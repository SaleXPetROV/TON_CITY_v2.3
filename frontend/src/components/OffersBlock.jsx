/**
 * OffersBlock — «Рекламные задания» on the Tasks page: offers that are always there, even when every own task is done.
 *   • AdsGram Task (<adsgram-task>): an advertiser's task (subscribe, open a bot / app). AdsGram confirms it to our
 *     server (Reward URL); the component's «reward» event is reported too (backend/offers.py pairs the two).
 *   • «Посмотри рекламу»: rewarded views (Monetag / AdsGram rewarded, in the admin's order), N per day.
 * When the day's limits are used up, the block says when new offers come (00:00 MSK) instead of disappearing.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Megaphone, Handshake, Play, Gift, Clock, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { fill } from '@/lib/translationsMore';
import { showRewardedAd, loadAdsgram } from '@/lib/monetag';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const getToken = () => localStorage.getItem('token') || localStorage.getItem('ton_city_token');
const auth = () => ({ headers: { Authorization: `Bearer ${getToken()}` } });

const pad = (n) => String(n).padStart(2, '0');
function left(iso, now) {
  const s = Math.max(0, Math.floor((new Date(iso).getTime() - now) / 1000));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return h ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
}
const inTelegram = () => !!(typeof window !== 'undefined' && window.Telegram?.WebApp?.initData);

function Row({ Icon, title, hint, reward, right, foot, testid }) {
  return (
    <Card className="glass-panel border-white/10" data-testid={testid}>
      <CardContent className="p-2.5 sm:p-3">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl flex-shrink-0 bg-white/5 flex items-center justify-center">
            <Icon className="w-6 h-6 sm:w-7 sm:h-7 text-cyber-cyan" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] sm:text-sm font-semibold text-white leading-snug break-words">{title}</p>
            <div className="flex items-center gap-1 mt-1 flex-wrap">
              {reward > 0 && (<><Gift className="w-4 h-4 text-yellow-400" /><span className="text-yellow-400 font-bold text-[13px] sm:text-sm">+{reward} $CITY</span></>)}
              {hint && <span className="text-[11px] text-text-muted ml-1.5">{hint}</span>}
            </div>
          </div>
          <div className="flex-shrink-0">{right}</div>
        </div>
        {foot}
      </CardContent>
    </Card>
  );
}

/** The AdsGram component, mounted once its script is loaded; reports its events up. */
function AdsgramTask({ blockId, t, onReward, onEmpty, onRestart }) {
  const ref = useRef(null);
  const cbs = useRef({ onReward, onEmpty, onRestart });
  cbs.current = { onReward, onEmpty, onRestart };
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let alive = true;
    loadAdsgram().then(() => { if (alive) setReady(true); }).catch(() => { if (alive) cbs.current.onEmpty(); });
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    const el = ref.current;
    if (!ready || !el) return undefined;
    const rew = () => cbs.current.onReward();
    const none = () => cbs.current.onEmpty();
    const tooLong = () => cbs.current.onRestart();
    el.addEventListener('reward', rew);
    el.addEventListener('onBannerNotFound', none);
    el.addEventListener('onError', none);
    el.addEventListener('onTooLongSession', tooLong);
    return () => {
      el.removeEventListener('reward', rew);
      el.removeEventListener('onBannerNotFound', none);
      el.removeEventListener('onError', none);
      el.removeEventListener('onTooLongSession', tooLong);
    };
  }, [ready]);
  if (!ready) return <div className="py-3 flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-white/40" /></div>;
  return (
    <adsgram-task data-block-id={blockId} className="gc-adsgram-task" ref={ref}>
      <span slot="reward" className="gc-ag-reward" />
      <div slot="button" className="gc-ag-btn">{t('of_do')}</div>
      <div slot="claim" className="gc-ag-btn gc-ag-claim">{t('of_claim')}</div>
      <div slot="done" className="gc-ag-btn gc-ag-done">{t('of_done')}</div>
    </adsgram-task>
  );
}

export default function OffersBlock({ t, onReward }) {
  const [st, setSt] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  const [taskState, setTaskState] = useState('live');          // live | empty | restart
  const [taskKey, setTaskKey] = useState(0);

  const load = useCallback(async () => {
    try { setSt((await axios.get(`${API}/offers`, auth())).data); } catch (_) { /* the block just stays as it was */ }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { const iv = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(iv); }, []);
  // a new day / a confirmation that waited for the network → refresh
  useEffect(() => {
    if (!st) return undefined;
    const waiting = (st.ad?.pending || 0) + (st.adsgram_task?.pending || 0);
    const iv = setInterval(load, waiting ? 10000 : 60000);
    return () => clearInterval(iv);
  }, [st, load]);
  useEffect(() => {
    if (st?.resets_at && new Date(st.resets_at).getTime() <= now) { load(); setTaskState('live'); setTaskKey((k) => k + 1); }
  }, [now, st, load]);

  const got = (key, n) => { toast.success(fill(t(key), { n })); if (onReward) onReward(); };

  const taskReward = async () => {
    try {
      const r = (await axios.post(`${API}/offers/adsgram-task/done`, {}, auth())).data;
      if (r.state) setSt(r.state);
      if (r.credited) got('of_task_got', r.state?.adsgram_task?.reward || st?.adsgram_task?.reward || 0);
      else if (r.pending) toast(t('of_task_pending'));
    } catch (_) { /* AdsGram's Reward URL still credits it */ }
    setTimeout(load, 4000);
  };

  const watch = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const cfg = (await axios.get(`${API}/ads/config`)).data;
      const { ymid } = (await axios.post(`${API}/offers/ad/start`, {}, auth())).data;
      const res = await showRewardedAd(cfg, ymid, 'offer');
      const r = (await axios.post(`${API}/offers/ad/watched`, { ymid, reward_event_type: res?.reward_event_type || '' }, auth())).data;
      if (r.state) setSt(r.state);
      if (r.credited) got('of_ad_got', r.state?.ad?.reward || 0);
      else if (r.pending) toast(t('of_ad_pending'));
    } catch (e) {
      const code = e?.code || e?.response?.data?.detail || '';
      if (code === 'skipped') toast(t('of_ad_skipped'));
      else if (code === 'cap' || code === 'too_fast') load();
      else {
        toast.error(t('of_ad_noad'));
        try { await axios.post(`${API}/ads/client-error`, { message: `offer:${String(e?.message || code || 'failed')}` }, auth()); } catch (_) { /* ignore */ }
      }
    } finally { setBusy(false); }
  };

  if (!st) return null;
  const task = st.adsgram_task || {};
  const ad = st.ad || {};
  if (!task.enabled && !ad.enabled) return null;
  const reset = left(st.resets_at, now);
  const taskOpen = task.enabled && task.left > 0;
  const adOpen = ad.enabled && ad.left > 0;
  const taskShown = taskOpen && inTelegram() && taskState === 'live';
  const allDone = (!task.enabled || task.left <= 0) && (!ad.enabled || ad.left <= 0);
  const adWait = ad.next_at && new Date(ad.next_at).getTime() > now ? left(ad.next_at, now) : '';

  return (
    <section className="space-y-2.5 sm:space-y-3" data-testid="offers-block">
      <div className="flex items-start gap-2 px-1 pt-1">
        <Megaphone className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-white">{t('of_title')}</h3>
          <p className="text-[11px] text-text-muted">{t('of_sub')}</p>
        </div>
      </div>

      {allDone && (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3 flex items-center gap-2 text-[12px] text-white/70" data-testid="offers-all-done">
          <Clock className="w-4 h-4 text-cyber-cyan shrink-0" />
          <span>{fill(t('of_all_done'), { time: reset })}</span>
        </div>
      )}

      {task.enabled && (
        <Row Icon={Handshake} testid="offer-adsgram-task" title={t('of_task_title')} reward={task.reward}
          hint={fill(t('of_left'), { a: task.done_today, b: task.cap })}
          right={null}
          foot={(
            <div className="mt-2">
              {!taskOpen ? (
                allDone ? null : <p className="text-[11px] text-text-muted">{fill(t('of_cap_done'), { time: reset })}</p>
              ) : !inTelegram() ? (
                <p className="text-[11px] text-text-muted">{t('of_task_tg')}</p>
              ) : taskState === 'restart' ? (
                <p className="text-[11px] text-text-muted">{t('of_task_restart')}</p>
              ) : taskState === 'empty' ? (
                <p className="text-[11px] text-text-muted">{t('of_task_none')}</p>
              ) : (
                <>
                  <p className="text-[11px] text-text-muted mb-2">{t('of_task_hint')}</p>
                  {taskShown && (
                    <AdsgramTask key={taskKey} blockId={task.block_id} t={t} onReward={taskReward}
                      onEmpty={() => setTaskState('empty')} onRestart={() => setTaskState('restart')} />
                  )}
                </>
              )}
              {task.pending > 0 && <p className="text-[11px] text-yellow-300/80 mt-1.5">{t('of_task_pending')}</p>}
            </div>
          )} />
      )}

      {ad.enabled && (
        <Row Icon={Play} testid="offer-ad" title={t('of_ad_title')} reward={ad.reward}
          hint={fill(t('of_left'), { a: ad.done_today, b: ad.cap })}
          right={adOpen ? (
            <Button size="sm" onClick={watch} disabled={busy || !!adWait} data-testid="offer-ad-watch"
              className="bg-yellow-500 text-black hover:bg-yellow-400 font-bold h-9 px-3 min-w-[92px]">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : adWait ? adWait : t('of_watch')}
            </Button>
          ) : null}
          foot={(
            <div className="mt-1.5">
              <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-yellow-400 to-amber-500 transition-all"
                  style={{ width: `${ad.cap ? Math.min(100, Math.round((ad.done_today / ad.cap) * 100)) : 0}%` }} />
              </div>
              <p className="text-[11px] text-text-muted mt-1.5">
                {!adOpen ? (allDone ? '' : fill(t('of_cap_done'), { time: reset })) : adWait ? fill(t('of_wait'), { time: adWait }) : t('of_ad_hint')}
              </p>
              {ad.pending > 0 && <p className="text-[11px] text-yellow-300/80 mt-1">{t('of_ad_pending')}</p>}
            </div>
          )} />
      )}
    </section>
  );
}
