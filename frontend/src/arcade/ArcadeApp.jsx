/**
 * ArcadeApp — the player-facing Arcade (close to ThunderWaves): list of games → game page (art, rules,
 * «Выигрыш до N XP», difficulty cards with lives / pace / XP / number of ads, «Играть», top 5 of today) →
 * countdown (difficulty · lives, hint, bonus legend) → the game (HUD: score, wave ring, sound, pause, hearts,
 * bonus chips, combo, boss bar) → «Продолжить?» (an ad brings you back once) → «Раунд завершён» sheet:
 * XP locked until the ads are watched (backend/arcade.py: few XP → 1 ad, more → 3 ads 2/4 + 1/4 + 1/4),
 * stats, top 5 by the best single game + my place, «В аркаду» / «Ещё раз».
 * A new game can't start while the last game's reward has no watched ad (the server refuses: arcade_watch_first).
 * With `preview` + `embedded` it runs inside the admin phone frame: no attempts used, no XP, ads can be simulated.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft, ChevronLeft, ChevronRight, Clapperboard, Clock, Crown, Flame, Gamepad2, Gift, Hand, Heart, Lock, LogOut, PartyPopper,
  Pause, Play, RotateCcw, Sprout, Swords, Timer, Trophy, Volume2, VolumeX, X, Zap,
} from 'lucide-react';
import { MgLeaderboard } from '@/components/minigames/mgShared';
import ChestReveal from '@/components/minigames/ChestReveal';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslation } from '@/lib/translations';
import { fill } from '@/lib/translationsMore';
import { showRewardedAd } from '@/lib/monetag';
import SmartAvatar from '@/components/SmartAvatar';
import { DIFFS, DIFF_NOTE, GAME_GRAD, GAME_ICON, LIVES, START_HINT, arcadeCall, sound } from '@/arcade/core';
import GameArt from '@/arcade/GameArt';
import Shooter, { SHOOTER_BUFFS } from '@/arcade/games/Shooter';
import Racer from '@/arcade/games/Racer';
import Basket from '@/arcade/games/Basket';
import Snake from '@/arcade/games/Snake';
import Tower from '@/arcade/games/Tower';
import G2048 from '@/arcade/games/G2048';
import Memory from '@/arcade/games/Memory';
import QuickMath from '@/arcade/games/QuickMath';
import TicTac from '@/arcade/games/TicTac';

const COMPONENTS = { shooter: Shooter, racer: Racer, basket: Basket, snake: Snake, tower: Tower, g2048: G2048, memory: Memory, math: QuickMath, tictac: TicTac };
const REVIVE = { shooter: true, racer: true };
const DIFF_ICON = { easy: Sprout, normal: Swords, hard: Flame };
const DIFF_TONE = { easy: 'bg-emerald-500/15 text-emerald-300', normal: 'bg-amber-400/15 text-amber-300', hard: 'bg-rose-500/15 text-rose-300' };
const STAT2 = { shooter: ['ar_st_kills', 'kills'], racer: ['ar_st_coins', 'coins'], basket: ['ar_st_made', 'made'], snake: ['ar_st_food', 'food'], tower: ['ar_st_floors', 'floors'], g2048: ['ar_st_best', 'best'], memory: ['ar_st_moves', 'moves'], math: ['ar_st_correct', 'correct'], tictac: ['ar_st_wins', 'wins'] };
const LS_DIFF = 'arcade_diff_v1';
const GOLD_BTN = 'bg-gradient-to-b from-[#fcd581] to-[#f0a443] text-[#2a1600] shadow-[0_8px_24px_-6px_rgba(245,166,35,0.55)]';
const PANEL = 'bg-gradient-to-b from-[#211a10] to-[#120e08] border border-[#4a3b1c]/70';

const readDiff = () => { try { return JSON.parse(localStorage.getItem(LS_DIFF) || '{}'); } catch (_) { return {}; } };
const saveDiff = (g, d) => { try { localStorage.setItem(LS_DIFF, JSON.stringify({ ...readDiff(), [g]: d })); } catch (_) { /* ignore */ } };
const nf = (n) => Number(n || 0).toLocaleString('en-US');
const hms = (ms) => { const x = Math.max(0, Math.floor(ms / 1000)); return [Math.floor(x / 3600), Math.floor((x % 3600) / 60), x % 60].map((v) => String(v).padStart(2, '0')).join(':'); };
function useNow(active) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { if (!active) return undefined; const id = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(id); }, [active]);
  return now;
}
const regenText = (min, t) => (min >= 60 ? `${Math.floor(min / 60)}${t('tl_h')}${min % 60 ? ` ${min % 60}${t('tl_m')}` : ''}` : `${min}${t('tl_m')}`);

let adsCfgCache = null;
async function adsConfig() {
  if (adsCfgCache) return adsCfgCache;
  const r = await fetch(`${process.env.REACT_APP_BACKEND_URL || ''}/api/ads/config`);
  adsCfgCache = await r.json();
  setTimeout(() => { adsCfgCache = null; }, 60000);
  return adsCfgCache;
}
const reportAdError = (e) => arcadeCall('/ads/client-error', { method: 'POST', body: JSON.stringify({ message: `arcade:${String(e?.message || e?.code || 'failed')}` }) }).catch(() => {});

/* ───────────────────────── top 5 ───────────────────────── */
function Top5({ game, t, refreshKey }) {
  const [d, setD] = useState(null);
  useEffect(() => { arcadeCall(`/arcade/${game}/top`).then(setD).catch(() => setD({ rows: [] })); }, [game, refreshKey]);
  if (!d) return null;
  const meIn = d.rows.some((r) => r.me);
  const badge = (p) => (p === 1 ? 'bg-gradient-to-b from-[#fde68a] to-[#f59e0b] text-[#3a2400]' : p === 2 ? 'bg-gradient-to-b from-slate-100 to-slate-400 text-slate-800' : p === 3 ? 'bg-gradient-to-b from-orange-300 to-orange-600 text-orange-950' : 'bg-white/5 text-white/70');
  return (
    <div className={`rounded-3xl ${PANEL} p-3`} data-testid="arcade-top5">
      <div className="flex items-center justify-between px-1 mb-2">
        <div className="flex items-center gap-1.5 text-[15px] font-black text-amber-300"><Trophy className="w-4 h-4" />{t('ar_top5')}</div>
        {d.me && <div className="text-xs font-bold text-white/70">{fill(t('ar_you_rank'), { n: d.me.place })}</div>}
      </div>
      {d.rows.length === 0 && <div className="text-xs text-white/50 text-center py-3">{t('ar_no_top')}</div>}
      <div className="space-y-1.5">
        {d.rows.map((r) => (
          <div key={r.user_id} className={`flex items-center gap-2.5 rounded-2xl px-2.5 py-2 ${r.me ? 'bg-amber-400/10 border border-amber-400/30' : 'bg-white/[0.04]'}`}>
            <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black shrink-0 ${badge(r.place)}`}>{r.place === 1 ? <Crown className="w-4 h-4" /> : r.place}</span>
            <SmartAvatar avatar={r.avatar} name={r.name} className="w-8 h-8 rounded-full shrink-0 text-xs" />
            <span className="flex-1 min-w-0 truncate text-sm font-semibold text-white">{r.name}</span>
            <span className="text-sm font-black text-amber-300 tabular-nums">{nf(r.score)} <span className="text-[10px] font-semibold text-amber-200/70">{t('ar_pts')}</span></span>
          </div>
        ))}
        {d.me && !meIn && (
          <div className="flex items-center gap-2.5 px-2.5 pt-2 mt-1 border-t border-dashed border-white/15" data-testid="arcade-top5-me">
            <span className="text-sm font-black text-amber-300">#{d.me.place}</span>
            <span className="flex-1 text-sm font-semibold text-white/80">{t('ar_you')}</span>
            <span className="text-sm font-black text-amber-300 tabular-nums">{nf(d.me.score)} <span className="text-[10px] font-semibold text-amber-200/70">{t('ar_pts')}</span></span>
          </div>
        )}
      </div>
    </div>
  );
}

function RefillIn({ at, t, onDone }) {
  const now = useNow(true);
  const ms = new Date(at).getTime() - now;
  useEffect(() => { if (ms <= 0 && onDone) onDone(); }, [ms <= 0]); // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="flex items-center justify-center gap-1.5 text-sm text-white/55"><Timer className="w-4 h-4" />{fill(t('ar_refill_in'), { t: hms(ms) })}</div>;
}

/* ───────────────────────── modal shell ───────────────────────── */
function Modal({ children, bottom = false, testid }) {
  return (
    <div className={`absolute inset-0 z-30 bg-black/55 backdrop-blur-md flex ${bottom ? 'items-end' : 'items-center'} justify-center p-3`} data-testid={testid}>
      <div className={`w-full max-w-sm rounded-[28px] ${PANEL} p-5 shadow-2xl ${bottom ? 'mb-1 max-h-[94%] overflow-y-auto' : ''}`}>{children}</div>
    </div>
  );
}

/* ───────────────────────── HUD ───────────────────────── */
function Hud({ hud, t, onExit, onPause, soundOn, onSound, embedded }) {
  const C = 2 * Math.PI * 15;
  const btn = 'w-10 h-10 rounded-2xl bg-[#0b0f1e]/80 border border-white/10 backdrop-blur flex items-center justify-center text-white active:scale-95 shrink-0';
  return (
    <div className={`absolute inset-x-0 top-0 z-20 px-2.5 pointer-events-none ${embedded ? 'pt-8' : ''}`}
      style={embedded ? undefined : { paddingTop: 'calc(max(var(--tg-safe-top, 0px), env(safe-area-inset-top, 0px)) + 8px)' }}>
      <div className="flex items-center gap-1.5 pointer-events-auto">
        <button type="button" onClick={onExit} className={btn} aria-label={t('ar_exit')} data-testid="arcade-exit"><X className="w-5 h-5" /></button>
        <div className="h-10 pl-1.5 pr-3 rounded-2xl bg-[#0b0f1e]/80 border border-amber-400/30 backdrop-blur flex items-center gap-1.5">
          <span className="w-7 h-7 rounded-full bg-gradient-to-b from-amber-300 to-amber-600 flex items-center justify-center"><Zap className="w-4 h-4 text-[#2a1600] fill-[#2a1600]" /></span>
          <span className="text-lg font-black text-white tabular-nums" data-testid="arcade-score">{nf(hud.score)}</span>
        </div>
        <div className="flex-1" />
        {hud.wave !== undefined && (
          <div className="relative w-[38px] h-[38px] rounded-full bg-[#0b0f1e]/80 flex items-center justify-center shrink-0" title={t('ar_wave')}>
            <svg width="38" height="38" viewBox="0 0 38 38" className="absolute inset-0">
              <circle cx="19" cy="19" r="15" stroke="#ffffff1f" strokeWidth="3" fill="none" />
              <circle cx="19" cy="19" r="15" stroke="#a78bfa" strokeWidth="3" fill="none" strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - Math.max(0, Math.min(1, hud.waveProgress || 0)))} transform="rotate(-90 19 19)" />
            </svg>
            <span className="relative text-[11px] font-black text-white">W{hud.wave}</span>
          </div>
        )}
        {hud.timeLeft !== undefined && (
          <div className="h-10 px-2.5 rounded-2xl bg-[#0b0f1e]/80 border border-white/10 flex items-center gap-1 text-sm font-black text-white tabular-nums"><Timer className="w-4 h-4 text-cyan-300" />{Math.ceil(hud.timeLeft)}</div>
        )}
        {hud.round !== undefined && <div className="h-10 px-2.5 rounded-2xl bg-[#0b0f1e]/80 border border-white/10 flex items-center text-xs font-black text-violet-200">{hud.roundTotal ? fill(t('ar_round'), { a: hud.round, b: hud.roundTotal }) : fill(t('ar_round_one'), { a: hud.round })}</div>}
        {hud.moves !== undefined && <div className="h-10 px-2.5 rounded-2xl bg-[#0b0f1e]/80 border border-white/10 flex items-center text-xs text-white/80">{t('ar_moves')}: <b className="ml-1 text-white">{hud.moves}</b></div>}
        <button type="button" onClick={onSound} className={btn} aria-label={t('ar_sound')}>{soundOn ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5 text-white/50" />}</button>
        <button type="button" onClick={onPause} className={btn} aria-label={t('ar_pause')} data-testid="arcade-pause"><Pause className="w-5 h-5 fill-white" /></button>
        {hud.maxLives > 0 && (
          <div className="h-10 px-2 rounded-2xl bg-[#0b0f1e]/80 border border-white/10 flex items-center gap-0.5 shrink-0" aria-label={t('ar_lives')}>
            {Array.from({ length: hud.maxLives }).map((_, i) => <Heart key={i} className={`w-4 h-4 ${i < hud.lives ? 'text-rose-500 fill-rose-500' : 'text-white/40'}`} />)}
          </div>
        )}
      </div>
      <div className="flex items-start justify-between gap-2 mt-2">
        <div className="flex flex-col gap-1.5">
          {(hud.buffs || []).map((b) => (
            <div key={b.k} className="relative overflow-hidden flex items-center gap-1.5 pl-2 pr-3 py-1 rounded-xl bg-[#0b0f1e]/85 border text-[12px] font-bold text-white" style={{ borderColor: `${b.color}aa` }}>
              <Zap className="w-3.5 h-3.5" style={{ color: b.color }} />{t(b.key)}
              <div className="absolute left-0 bottom-0 h-[3px] rounded-full" style={{ width: `${(b.left / b.dur) * 100}%`, background: b.color }} />
            </div>
          ))}
        </div>
        {hud.boss && (
          <div className="flex-1 max-w-[180px] mt-1">
            <div className="text-center text-[10px] font-black tracking-[0.2em] text-rose-200">☠ {String(t('ar_boss')).toUpperCase()}</div>
            <div className="h-1.5 rounded-full bg-white/15 overflow-hidden mt-0.5"><div className="h-full bg-gradient-to-r from-rose-500 to-amber-400" style={{ width: `${hud.boss.hp * 100}%` }} /></div>
          </div>
        )}
        {hud.combo > 1 && <div className="px-3 py-1 rounded-xl bg-fuchsia-600/30 border border-fuchsia-300/60 text-[13px] font-black italic text-white">{fill(t('ar_combo'), { n: hud.combo })}</div>}
      </div>
    </div>
  );
}

/* ───────────────────────── the round-over sheet ───────────────────────── */
function RoundSheet({ game, result, preview, adsActive, t, onReward, onArcade, onAgain, attemptsLeft, freePlay }) {
  const [busy, setBusy] = useState(false);
  const [adStep, setAdStep] = useState(null);           // {a, b}: «Реклама a из b…» while the chain plays
  const rw = result.reward;
  const xp = result.xp || 0;
  const unlocked = rw ? rw.xp_unlocked : xp;
  const total = rw ? rw.xp_total : xp;
  const n = rw?.ads_confirmed || 0;
  const m = rw?.ads_total || 0;
  const pending = !!rw && rw.status === 'pending';
  const locked = pending && unlocked < total;
  const [k2, statKey] = STAT2[game] || [];
  const st2 = result.stats?.[statKey];

  useEffect(() => {                                    // a view waiting for Monetag's postback → poll
    if (!rw || rw.status !== 'pending' || !rw.ads_pending) return undefined;
    let i = 0;
    const id = setInterval(async () => {
      i += 1;
      try { const r = await arcadeCall(`/arcade/reward/${rw.id}`); onReward(r); if (!r.ads_pending || i > 30) clearInterval(id); } catch (_) { clearInterval(id); }
    }, 3000);
    return () => clearInterval(id);
  }, [rw?.id, rw?.ads_pending]); // eslint-disable-line react-hooks/exhaustive-deps

  // ONE press plays every ad still needed (the number the admin set), one after another; each ad is reported
  // and counted on its own, so a chain cut in the middle keeps the ads already watched
  const watch = async (simulate) => {
    if (busy || !rw) return;
    setBusy(true);
    const left = Math.max(1, (rw.ads_total || 1) - (rw.ads_confirmed || 0) - (rw.ads_pending || 0));
    try {
      let cur = rw;
      for (let i = 0; i < left; i += 1) {
        setAdStep({ a: i + 1, b: left });
        if (simulate) {
          cur = await arcadeCall(`/arcade/reward/${rw.id}/ad/watched`, { method: 'POST', body: JSON.stringify({ simulate: true }) });
          onReward(cur); sound.play('coin');
        } else {
          const cfg = await adsConfig();
          if (!cfg?.enabled) { toast.error(t('ar_ad_fail')); return; }
          const s = await arcadeCall(`/arcade/reward/${rw.id}/ad/start`, { method: 'POST' });
          let res;
          try { res = await showRewardedAd(cfg, s.ymid, s.request_var); } catch (e) { toast.error(t(e?.code === 'no_fill' ? 'ar_ad_nofill' : 'ar_ad_fail')); reportAdError(e); return; }
          let tries = 0;
          for (;;) {                                     // the server keeps a minimum gap between two ads
            try {
              cur = await arcadeCall(`/arcade/reward/${rw.id}/ad/watched`, { method: 'POST', body: JSON.stringify({ ymid: s.ymid, reward_event_type: res?.reward_event_type || '' }) });
              break;
            } catch (e) {
              if (e?.detail !== 'ad_too_fast' || tries > 6) throw e;
              tries += 1; await new Promise((ok) => setTimeout(ok, 1500));
            }
          }
          onReward(cur); sound.play('coin');
        }
        if (!cur || cur.status !== 'pending') break;
      }
    } catch (e) { toast.error(t(e?.detail === 'ad_too_fast' ? 'ar_ad_fast' : 'ar_ad_fail')); } finally { setBusy(false); setAdStep(null); }
  };

  const collected = !locked && total > 0;
  return (
    <Modal bottom testid="arcade-result">
      <div className="text-center">
        <div className="relative mx-auto w-20 h-20 mb-2">
          {collected && <div className="absolute -inset-10 rounded-full arc-rays" />}
          <div className="relative w-20 h-20 rounded-full bg-gradient-to-b from-[#fde68a] to-[#f2b134] flex items-center justify-center shadow-[0_0_30px_rgba(245,185,66,0.45)]"><PartyPopper className="w-9 h-9 text-[#2a1600]" /></div>
        </div>
        <div className="text-2xl font-black text-white">{t('ar_round_done')}</div>
        <div className={`flex items-center justify-center gap-2 mt-2 ${locked ? 'opacity-75' : ''}`} data-testid="arcade-result-xp">
          {locked && <Lock className="w-6 h-6 text-white/60" />}
          <span className={`w-9 h-9 rounded-full flex items-center justify-center border-2 ${locked ? 'border-amber-300/50' : 'border-amber-300 bg-amber-400/15'}`}><Zap className="w-5 h-5 text-amber-300" /></span>
          <span className={`text-5xl font-black tabular-nums ${locked ? 'text-amber-200/70' : 'text-amber-300'}`}>{result.loading ? '…' : `+${locked ? total : unlocked}`}</span>
          <span className="text-lg font-black text-amber-200/80 self-end mb-1">XP</span>
        </div>
        {!result.loading && !result.ok && <div className="text-xs text-rose-300 mt-2">{t(result.error ? 'ar_err' : 'ar_rejected')}</div>}
        {!result.loading && result.ok && !xp && !result.fromList && <div className="text-xs text-white/60 mt-2">{t(result.free ? 'ar_free_round' : 'ar_zero_xp')}</div>}
      </div>

      {pending && (
        <div className="mt-3 space-y-2.5">
          <div className="flex items-center justify-center gap-1.5 text-sm font-semibold text-amber-100/90 text-center">
            <Lock className="w-4 h-4 shrink-0" />
            {n === 0 ? fill(t('ar_watch_claim'), { n: m, x: total }) : fill(t('ar_collected'), { a: unlocked, b: total })}
          </div>
          <div className="flex justify-center gap-1.5">
            {Array.from({ length: m }).map((_, i) => <span key={i} className={`w-3 h-3 rounded-full border-2 ${i < n ? 'bg-violet-400 border-violet-300' : 'border-white/40'}`} />)}
          </div>
          {rw.ads_pending > 0 && (
            <div className="flex items-center justify-center gap-2 text-[11px] text-amber-200/90"><span className="w-3 h-3 border-2 border-amber-300 border-t-transparent rounded-full animate-spin" />{t('ar_ad_wait')}</div>
          )}
          <button type="button" disabled={busy} onClick={() => watch(false)} data-testid="arcade-watch-ad"
            className="w-full h-14 rounded-2xl bg-gradient-to-b from-[#8b6cf6] to-[#6d3fe0] text-white text-lg font-black flex items-center justify-center gap-2 shadow-[0_10px_26px_-8px_rgba(124,58,237,0.75)] disabled:opacity-60 active:scale-[0.99]">
            {busy ? <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Clapperboard className="w-5 h-5" />}
            {busy && adStep ? fill(t('gm_ad_of'), adStep) : (m - n > 1 ? fill(t('gm_watch_all'), { n: m - n }) : fill(t('ar_watch_n'), { n: n + 1, m }))}
            {!busy && rw.next_xp ? <span className="text-sm font-bold text-violet-100/90">· +{m - n > 1 ? total - unlocked : rw.next_xp} XP</span> : null}
          </button>
          {preview && (
            <button type="button" disabled={busy} onClick={() => watch(true)} data-testid="arcade-sim-ad" className="w-full h-9 rounded-xl border border-dashed border-cyan-400/50 text-cyan-200 text-xs font-semibold">
              Превью: имитировать просмотр рекламы
            </button>
          )}
        </div>
      )}
      {rw && rw.status === 'done' && rw.xp_capped > 0 && <div className="text-center text-[11px] text-amber-300/90 mt-2">{fill(t('ar_capped'), { n: rw.xp_capped })}</div>}
      {rw && rw.status === 'done' && rw.no_ads && <div className="text-center text-[11px] text-emerald-300 mt-2">✅ {t('ar_credited')}</div>}

      {result.fromList && rw?.chest && (rw.chest.state === 'pending' || rw.chest.state === 'given') && (
        <div className="mt-3 rounded-2xl border border-violet-400/30 bg-violet-500/[0.08] px-3 py-2 text-center text-[12px] font-semibold text-violet-100" data-testid="arcade-chest-ads">
          🎁 {rw.chest.state === 'given' ? t('gm_chest_won') : t('gr_chest_ads')}
          {rw.chest.nft_piece ? <div className="text-[13px] font-black text-fuchsia-200">🧩 {t('gr_piece_won')}</div> : null}
        </div>
      )}
      {result.promo?.counted && (
        <div className="mt-3 rounded-2xl border border-amber-400/30 bg-amber-400/[0.07] px-3 py-2 text-center space-y-0.5" data-testid="arcade-promo">
          <div className="text-sm font-black text-amber-200">{fill(t('gm_promo_pts'), { n: nf(result.score) })}</div>
          {result.promo.place ? <div className="text-[12px] text-white/75">{fill(t('gm_promo_rank'), { n: result.promo.place })}</div> : null}
          <div className="text-[12px] font-semibold text-white/80">
            {(rw?.chest?.state === 'given' || result.promo.chest?.given) ? `🎁 ${t('gm_chest_won')}`
              : rw?.chest?.state === 'none' && rw.chest.reason === 'daily_limit' ? t('gm_chest_limit')
                : (rw?.chest?.state === 'pending' || result.promo.chest?.pending)
                  ? <span className="text-violet-200" data-testid="arcade-chest-ads">🎁 {t(result.promo.nft_enabled ? 'gr_chest_ads_nft' : 'gr_chest_ads')}</span>
                  : result.promo.chest?.reason === 'daily_limit' ? t('gm_chest_limit')
                    : result.promo.chest?.reason === 'low_score' ? fill(t('gm_chest_need'), { n: nf(result.promo.chest.min_score) }) : null}
          </div>
          {(rw?.chest?.nft_piece || result.promo.chest?.nft_piece) ? (
            <div className="text-[13px] font-black text-fuchsia-200" data-testid="arcade-nft-pieces">🧩 {t('gr_piece_won')}</div>
          ) : null}
        </div>
      )}

      {!result.fromList && (
        <div className="flex justify-center gap-2 mt-4">
          <div className="min-w-[96px] rounded-2xl bg-black/30 px-4 py-2 text-center">
            <div className="text-[10px] font-bold tracking-[0.18em] text-amber-200/60 uppercase">{t('ar_score')}</div>
            <div className="text-xl font-black text-white tabular-nums" data-testid="arcade-result-score">{nf(result.score)}</div>
          </div>
          {st2 !== undefined && (
            <div className="min-w-[96px] rounded-2xl bg-black/30 px-4 py-2 text-center">
              <div className="text-[10px] font-bold tracking-[0.18em] text-amber-200/60 uppercase">{t(k2)}</div>
              <div className="text-xl font-black text-white tabular-nums">{nf(st2)}</div>
            </div>
          )}
        </div>
      )}

      {!pending && !result.loading && <div className="mt-4"><Top5 game={game} t={t} refreshKey={`${result.score}-${rw?.id || ''}`} /></div>}

      <div className="grid grid-cols-2 gap-2.5 mt-4">
        <button type="button" onClick={onArcade} className="h-12 rounded-2xl bg-white/[0.06] border border-[#4a3b1c] text-white font-bold flex items-center justify-center gap-1.5" data-testid="arcade-to-hub">
          <ArrowLeft className="w-4 h-4" />{t('ar_to_arcade')}
        </button>
        <button type="button" disabled={!attemptsLeft && !preview && !freePlay} onClick={onAgain} data-testid="arcade-again"
          className={`h-12 rounded-2xl font-black flex items-center justify-center gap-1.5 disabled:opacity-45 ${pending && n === 0 && adsActive ? 'bg-[#6b5326] text-[#2a1600]' : GOLD_BTN}`}>
          <RotateCcw className="w-4 h-4" />{t('ar_again')}
        </button>
      </div>
      {!attemptsLeft && !preview && <div className="text-center text-xs text-white/45 mt-2.5">{t(freePlay ? 'ar_free_note' : 'ar_no_games')}</div>}
      {preview && <div className="text-center text-[10px] text-cyan-300/80 mt-2">Превью: попытки не тратятся, XP не начисляются</div>}
      <style>{'.arc-rays{background:repeating-conic-gradient(from 0deg,#f5b94250 0deg 8deg,transparent 8deg 30deg);animation:spin 14s linear infinite;-webkit-mask-image:radial-gradient(circle,black 30%,transparent 70%);mask-image:radial-gradient(circle,black 30%,transparent 70%)}'}</style>
    </Modal>
  );
}

/* ───────────────────────── the app ───────────────────────── */
export default function ArcadeApp({ preview = false, embedded = false, initialGame = null }) {
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const navigate = useNavigate();
  const [hub, setHub] = useState(null);
  const [gh, setGh] = useState(null);                   // «Игры»: promotion, chests today, my place in every game
  const [chests, setChests] = useState(null);
  const [view, setView] = useState(initialGame ? 'detail' : 'hub');
  const [gameId, setGameId] = useState(initialGame);
  const [diff, setDiff] = useState('normal');
  const [session, setSession] = useState(null);
  const [count, setCount] = useState(0);
  const [hud, setHud] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [paused, setPaused] = useState(false);
  const [quitAsk, setQuitAsk] = useState(false);
  const [revive, setRevive] = useState(null);           // {revive, decline, left, busy}
  const [soundOn, setSoundOn] = useState(sound.on);
  const pausedRef = useRef(false);
  const hudRef = useRef({});
  const started = useRef(0);
  const ended = useRef(false);

  pausedRef.current = paused || quitAsk || !!revive;

  const load = useCallback(async () => {
    if (!preview && !embedded) arcadeCall('/games/hub').then(setGh).catch(() => setGh(null));
    try { setHub(await arcadeCall(`/arcade${preview ? '?preview=true' : ''}`)); } catch (_) { setHub({ visible: false }); }
  }, [preview, embedded]);
  useEffect(() => { load(); }, [load]);

  const game = hub?.games?.find((g) => g.id === gameId);
  const openGame = (id) => { setGameId(id); setDiff(readDiff()[id] || 'normal'); setView('detail'); };
  useEffect(() => { if (initialGame) setDiff(readDiff()[initialGame] || 'normal'); }, [initialGame]);

  const showOwed = async (rid) => {
    try {
      const r = await arcadeCall(`/arcade/reward/${rid}`);
      setGameId(r.game); setSession(null);
      setResult({ ok: true, score: r.score, xp: r.xp_total, reward: r, fromList: true });
      setView('result');
    } catch (_) { /* ignore */ }
  };

  const start = async (g = game, d = diff, free = false) => {
    if (busy || !g) return;
    sound.unlock();
    setBusy(true);
    try {
      saveDiff(g.id, d);
      const s = await arcadeCall(`/arcade/${g.id}/start`, { method: 'POST', body: JSON.stringify({ difficulty: d, preview, free }) });
      setGameId(g.id); setSession(s); setHud({}); hudRef.current = {}; setResult(null); ended.current = false;
      setPaused(false); setQuitAsk(false); setRevive(null);
      setCount(3); setView('play');
    } catch (e) {
      if (e?.detail?.code === 'arcade_watch_first') { toast.error(t('ar_watch_first')); await showOwed(e.detail.reward_id); return; }
      toast.error(t(e?.detail === 'arcade_no_attempts' ? 'ar_no_attempts' : e?.detail === 'arcade_closed' ? 'ar_closed' : 'ar_err'));
      load();
    } finally { setBusy(false); }
  };

  useEffect(() => {                                     // 3-2-1, then the game starts (its time is counted from here)
    if (view !== 'play' || count <= 0) return undefined;
    sound.play('tick');
    const id = setTimeout(() => { setCount((c) => c - 1); if (count === 1) started.current = performance.now(); }, 800);
    return () => clearTimeout(id);
  }, [view, count]);

  const onHud = useCallback((h) => { hudRef.current = { ...hudRef.current, ...h }; setHud((x) => ({ ...x, ...h })); }, []);

  const finish = useCallback(async ({ score, stats, abandoned }) => {
    if (ended.current || !session) return;
    ended.current = true;
    setRevive(null); setPaused(false); setQuitAsk(false);
    const duration_ms = Math.round(performance.now() - (started.current || performance.now()));
    if (abandoned) {                                    // «Выйти»: this run does not count
      arcadeCall(`/arcade/session/${session.session_id}/finish`, { method: 'POST', body: JSON.stringify({ abandoned: true }) }).catch(() => {}).finally(load);
      setSession(null); setView('detail');
      return;
    }
    setView('result');
    setResult({ loading: true, score, stats });
    try {
      const r = await arcadeCall(`/arcade/session/${session.session_id}/finish`, {
        method: 'POST', body: JSON.stringify({ score: Math.floor(score || 0), duration_ms, stats: stats || {} }),
      });
      setResult({ ...r, stats });
      if (r.promo?.opened_chests?.length) setTimeout(() => setChests(r.promo.opened_chests), 700);   // the chest flies in
      sound.play(r.xp > 0 ? 'win' : 'lose');
    } catch (_) { setResult({ ok: false, score, stats, xp: 0, error: true }); }
    load();
  }, [session, load]);

  const onDeath = useCallback((h) => {
    const canAd = hub?.ads?.active || preview;
    if (!canAd || !session) { h.decline(); return; }
    setRevive({ ...h, left: 8 });
  }, [hub, preview, session]);

  useEffect(() => {                                     // «Нет, спасибо (8)» counts down and declines by itself
    if (!revive || revive.busy) return undefined;
    if (revive.left <= 0) { const h = revive; setRevive(null); h.decline(); return undefined; }
    const id = setTimeout(() => setRevive((r) => (r && !r.busy ? { ...r, left: r.left - 1 } : r)), 1000);
    return () => clearTimeout(id);
  }, [revive]);

  const doRevive = async (simulate) => {
    if (!revive || revive.busy) return;
    const h = revive;
    setRevive({ ...h, busy: true });
    try {
      if (!simulate) {
        const cfg = await adsConfig();
        const s = await arcadeCall(`/arcade/session/${session.session_id}/revive/start`, { method: 'POST' });
        await showRewardedAd(cfg, s.ymid, s.request_var);
      }
      setRevive(null);
      h.revive();
      sound.play('pick');
    } catch (e) {
      toast.error(t(e?.code === 'no_fill' ? 'ar_ad_nofill' : 'ar_ad_fail'));
      if (e?.code) reportAdError(e);
      setRevive(null); h.decline();
    }
  };

  const updateReward = (r) => {
    let fly = null;
    setResult((x) => {
      if (!x) return x;
      // the last ad → the chest that waited for it flies in (once)
      if (r?.chest?.state === 'given' && r.chest.chest && x.reward?.chest?.state !== 'given') fly = r.chest.chest;
      return { ...x, reward: r };
    });
    setTimeout(() => { if (fly) setChests([fly]); }, 500);
    load();
  };
  const shell = embedded ? 'absolute inset-0' : 'fixed inset-0 z-[160]';
  const adsActive = !!hub?.ads?.active;

  if (hub === null) return <div className="py-16 text-center text-white/50 text-sm">…</div>;
  // the Arcade switched off: the «Игры» page still shows the promotion game and the rewards
  if (!hub.visible && (preview || embedded || !gh || !(gh.games || []).length)) return <div className="py-16 text-center text-white/50 text-sm" data-testid="arcade-closed">{t('ar_closed')}</div>;
  const arcadeGames = hub.visible ? hub.games : [];
  const ghGame = (id) => (gh?.games || []).find((x) => x.id === id);
  const promoOn = !!gh;                                  // no promotion: every game always has its rating of the week
  const chestReveal = chests && <ChestReveal chests={chests} lang={lang} t={t} onClose={() => setChests(null)} />;

  /* ── playing / round-over over the frozen game ── */
  if ((view === 'play' && session) || (view === 'result' && result)) {
    const gid = session?.game || gameId;
    const G = COMPONENTS[gid];
    const g = hub.games.find((x) => x.id === gid) || {};
    const lives = session?.tuning?.lives || LIVES[gid]?.[session?.difficulty || diff];
    return (
      <div className={`${shell} bg-[#05060A] overflow-hidden`} data-testid="arcade-play">
        <div className={`absolute inset-0 ${view === 'result' ? 'blur-md opacity-60 pointer-events-none' : ''}`}>
          {session && count <= 0 && (
            <G key={session.session_id} seed={session.seed} difficulty={session.difficulty} tuning={session.tuning} onHud={onHud} onEnd={finish} t={t} pausedRef={pausedRef}
              onDeath={REVIVE[gid] ? onDeath : undefined} />
          )}
          {!session && <div className={`absolute inset-0 bg-gradient-to-br ${GAME_GRAD[gid]} opacity-30`} />}
        </div>
        {view === 'play' && count <= 0 && (
          <Hud hud={hud} t={t} embedded={embedded} soundOn={soundOn} onSound={() => setSoundOn(sound.toggle())}
            onExit={() => setQuitAsk(true)} onPause={() => setPaused(true)} />
        )}

        {view === 'play' && count > 0 && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-gradient-to-b from-[#0b0a1a] to-[#05060A] px-6" data-testid="arcade-countdown">
            <div className="px-3 py-1 rounded-full border border-amber-400/40 bg-amber-400/10 text-[12px] font-black tracking-[0.18em] text-amber-300 flex items-center gap-1.5 uppercase">
              {t(`ar_${session.difficulty}`)}{lives ? <><span>·</span><Heart className="w-3.5 h-3.5" />{lives}</> : null}
            </div>
            {session.free && <div className="mt-2 text-[11px] text-white/55">{t('ar_free_round')}</div>}
            <div key={count} className="text-[120px] leading-none font-black bg-gradient-to-b from-white to-violet-400 bg-clip-text text-transparent my-4 arc-pop">{count}</div>
            <div className="flex items-center gap-2 text-white font-semibold"><Hand className="w-5 h-5 text-white/80" />{t(START_HINT[gid])}</div>
            {gid === 'shooter' && (
              <div className="flex flex-wrap justify-center gap-2 mt-5 max-w-[300px]">
                {Object.entries(SHOOTER_BUFFS).map(([k, b]) => (
                  <span key={k} className="flex items-center gap-1.5 pl-1 pr-2.5 py-1 rounded-full bg-white/[0.06] border border-white/10 text-[12px] font-semibold text-white">
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-black text-[#0b0f1e]" style={{ background: b.color }}>{b.token}</span>{t(b.key)}
                  </span>
                ))}
              </div>
            )}
            <style>{'@keyframes arcpop{0%{transform:scale(1.5);opacity:0}100%{transform:scale(1);opacity:1}}.arc-pop{animation:arcpop .5s ease-out}'}</style>
          </div>
        )}

        {paused && view === 'play' && (
          <Modal testid="arcade-pause-modal">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 rounded-full bg-gradient-to-b from-[#fde68a] to-[#f2b134] flex items-center justify-center shadow-[0_0_26px_rgba(245,185,66,0.45)]"><Pause className="w-8 h-8 text-[#2a1600] fill-[#2a1600]" /></div>
              <div className="text-2xl font-black text-white mt-3 mb-4">{t('ar_pause')}</div>
              <button type="button" onClick={() => setPaused(false)} className={`w-full h-12 rounded-2xl font-black flex items-center justify-center gap-2 ${GOLD_BTN}`} data-testid="arcade-resume"><Play className="w-5 h-5 fill-current" />{t('ar_resume')}</button>
              <div className="grid grid-cols-2 gap-2.5 mt-2.5">
                <button type="button" onClick={() => setSoundOn(sound.toggle())} className="h-11 rounded-2xl bg-white/[0.06] border border-[#4a3b1c] text-white font-bold flex items-center justify-center gap-1.5">{soundOn ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}{t('ar_sound')}</button>
                <button type="button" onClick={() => { setPaused(false); setQuitAsk(true); }} className="h-11 rounded-2xl bg-white/[0.06] border border-[#4a3b1c] text-white font-bold flex items-center justify-center gap-1.5"><LogOut className="w-4 h-4" />{t('ar_exit')}</button>
              </div>
            </div>
          </Modal>
        )}

        {quitAsk && view === 'play' && (
          <Modal testid="arcade-quit-modal">
            <div className="text-center text-white/90 font-semibold mb-4">{t('ar_quit_q')}</div>
            <div className="grid grid-cols-2 gap-2.5">
              <button type="button" onClick={() => setQuitAsk(false)} className="h-11 rounded-2xl bg-white/[0.06] border border-white/10 text-white font-bold">{t('ar_cancel')}</button>
              <button type="button" onClick={() => finish({ abandoned: true })} className="h-11 rounded-2xl bg-sky-500 text-white font-bold" data-testid="arcade-quit-ok">{t('ar_ok')}</button>
            </div>
          </Modal>
        )}

        {revive && view === 'play' && (
          <Modal testid="arcade-revive-modal">
            <div className="text-center">
              <div className="relative mx-auto w-20 h-20">
                <svg viewBox="0 0 80 80" className="absolute inset-0"><circle cx="40" cy="40" r="37" stroke="#f5b942" strokeWidth="4" fill="none" strokeDasharray={232} strokeDashoffset={232 * (1 - revive.left / 8)} transform="rotate(-90 40 40)" strokeLinecap="round" /></svg>
                <div className="absolute inset-[7px] rounded-full bg-gradient-to-b from-emerald-300 to-emerald-600 flex items-center justify-center"><Heart className="w-8 h-8 text-[#04201a]" /></div>
              </div>
              <div className="text-2xl font-black text-white mt-3">{t('ar_cont_q')}</div>
              <div className="text-sm text-white/70 mt-1 mb-4">{t('ar_cont_desc')}</div>
              <button type="button" disabled={revive.busy} onClick={() => doRevive(false)} className={`w-full h-12 rounded-2xl font-black flex items-center justify-center gap-2 disabled:opacity-60 ${GOLD_BTN}`} data-testid="arcade-revive-ad">
                {revive.busy ? <span className="w-5 h-5 border-2 border-[#2a1600] border-t-transparent rounded-full animate-spin" /> : <Clapperboard className="w-5 h-5" />}{t('ar_cont_ad')}
              </button>
              {preview && <button type="button" disabled={revive.busy} onClick={() => doRevive(true)} className="w-full h-9 mt-2 rounded-xl border border-dashed border-cyan-400/50 text-cyan-200 text-xs font-semibold" data-testid="arcade-revive-sim">Превью: имитировать рекламу</button>}
              <button type="button" disabled={revive.busy} onClick={() => { const h = revive; setRevive(null); h.decline(); }} className="w-full h-11 mt-2.5 rounded-2xl bg-white/[0.06] border border-[#4a3b1c] text-white font-bold" data-testid="arcade-revive-no">
                {t('ar_no_thanks')} <span className="text-white/40 font-semibold">({revive.left})</span>
              </button>
            </div>
          </Modal>
        )}

        {chestReveal}
        {view === 'result' && result && (
          <RoundSheet game={gid} result={result} preview={preview} adsActive={adsActive} t={t} onReward={updateReward} attemptsLeft={g.attempts_left} freePlay={g.free_play}
            onArcade={() => { setResult(null); setSession(null); setView('hub'); load(); }}
            onAgain={() => {
              const rw = result.reward;
              if (rw && rw.status === 'pending' && !(rw.ads_confirmed || rw.ads_pending) && adsActive && !preview) { toast.error(t('ar_watch_first')); return; }
              setResult(null); setSession(null);
              start(g, readDiff()[gid] || diff, !preview && !g.attempts_left);
            }} />
        )}
      </div>
    );
  }

  /* ── game page ── */
  if (view === 'detail' && game) {
    const noAttempts = !preview && game.attempts_left <= 0;
    const canFree = noAttempts && game.free_play;
    return (
      <div className="space-y-4 pb-4" data-testid={`arcade-detail-${game.id}`}>
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => setView('hub')} className="w-12 h-12 rounded-2xl bg-black/50 border border-white/10 flex items-center justify-center text-white shrink-0" aria-label={t('ar_all_games')}><ChevronLeft className="w-6 h-6" /></button>
          <div className="flex-1 min-w-0">
            <div className="text-[22px] font-black text-white leading-tight line-clamp-2">{t(`ar_g_${game.id}`)}</div>
            <div className="text-sm text-white/50">{noAttempts ? t('ar_paid_over') : fill(t('ar_paid_left'), { n: game.attempts_left })}</div>
          </div>
          <div className="h-11 px-3 rounded-full border border-amber-400/40 bg-amber-400/10 flex items-center gap-1.5 text-amber-300 font-black shrink-0">
            <Zap className="w-4 h-4" />{game.xp_by_difficulty?.[diff] ?? game.max_xp}
          </div>
        </div>

        <GameArt game={game.id} />

        <p className="text-center text-[15px] leading-relaxed text-white/80 px-1">{t(`ar_r_${game.id}`)}</p>

        <div className="flex justify-center">
          <div className="px-4 py-2 rounded-full border border-amber-400/50 bg-amber-400/10 flex items-center gap-2 text-amber-300 font-black">
            <span className="w-6 h-6 rounded-full border-2 border-amber-300 flex items-center justify-center"><Zap className="w-3.5 h-3.5" /></span>
            {fill(t('ar_win_up_to'), { n: game.xp_by_difficulty?.[diff] ?? game.max_xp })}
          </div>
        </div>

        <div>
          <div className="text-xs font-black tracking-[0.2em] text-white/50 uppercase mb-2 px-1">{t('ar_difficulty')}</div>
          <div className={`rounded-3xl ${PANEL} p-1.5 grid grid-cols-3 gap-1.5`}>
            {DIFFS.map((d) => {
              const Ic = DIFF_ICON[d];
              const active = diff === d;
              const lv = game.tuning?.[d]?.lives || LIVES[game.id]?.[d];
              const note = DIFF_NOTE[game.id]?.[d];
              return (
                <button type="button" key={d} onClick={() => setDiff(d)} data-testid={`arcade-diff-${d}`}
                  className={`rounded-[20px] px-1.5 py-3 text-center transition-all border-2 ${active ? 'border-amber-400 bg-amber-400/10 shadow-[0_0_20px_-6px_rgba(245,185,66,0.6)]' : 'border-transparent'}`}>
                  <span className={`mx-auto w-10 h-10 rounded-full flex items-center justify-center ${active ? 'bg-amber-400 text-[#1a1206]' : DIFF_TONE[d]}`}><Ic className="w-5 h-5" /></span>
                  <div className="text-[15px] font-black text-white mt-1.5">{t(`ar_${d}`)}</div>
                  <div className="text-[11px] text-white/55 leading-tight min-h-[28px] mt-0.5 flex items-center justify-center gap-1 flex-wrap">
                    {lv ? <span className="inline-flex items-center gap-0.5"><Heart className="w-3 h-3" />{lv}</span> : null}
                    {lv && note ? <span>·</span> : null}
                    {note ? <span>{t(note)}</span> : null}
                  </div>
                  <div className="flex items-center justify-center gap-1 text-amber-300 font-black text-sm mt-1"><Zap className="w-3.5 h-3.5" />{game.xp_by_difficulty?.[d] ?? 0}</div>
                  {(adsActive || preview) && (
                    <div className="mt-1.5 mx-auto w-fit px-2 py-0.5 rounded-full bg-white/[0.07] text-[11px] font-bold text-violet-200 flex items-center gap-1"><Clapperboard className="w-3 h-3" />{fill(t('ar_ads_n'), { n: game.ads_by_difficulty?.[d] ?? 1 })}</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <button type="button" disabled={busy || (noAttempts && !canFree)} onClick={() => start(game, diff, canFree)} data-testid="arcade-play-btn"
          className={`w-full h-16 rounded-[22px] font-black text-xl flex items-center justify-center gap-2.5 disabled:opacity-45 active:scale-[0.99] transition-all ${GOLD_BTN}`}>
          {noAttempts && !canFree ? <><Lock className="w-5 h-5" />{t('ar_no_attempts')}</> : <><Play className="w-6 h-6" />{t(canFree ? 'ar_play_free' : 'ar_play')}</>}
        </button>
        {noAttempts && (
          <div className="text-center -mt-1 space-y-1.5" data-testid="arcade-free-note">
            {canFree && <div className="text-sm text-white/55">{t('ar_free_note')}</div>}
            {game.next_attempt_at && <RefillIn at={game.next_attempt_at} t={t} onDone={load} />}
          </div>
        )}

        <div className={`rounded-3xl ${PANEL} p-3.5 space-y-1.5 text-sm`}>
          {[
            [t('ar_cond_target'), nf(game.target_score)],
            [t('ar_cond_att'), `${game.attempts_left} / ${game.attempts_max}`],
            ...(hub.daily_xp_cap > 0 ? [[t('ar_cond_daily'), `${hub.xp_today} / ${hub.daily_xp_cap}`]] : []),
          ].map(([k, v]) => <div key={k} className="flex justify-between gap-3"><span className="text-white/55">{k}</span><span className="font-bold text-white">{v}</span></div>)}
          <div className="text-[11px] text-white/45 pt-1">{game.regen_minutes > 0 ? fill(t('ar_regen'), { t: regenText(game.regen_minutes, t) }) : t('ar_regen_daily')}</div>
          {(adsActive || preview) && <div className="text-[11px] text-white/45 pt-1">{t('ar_reward_ads')} {(hub.ads?.shares || []).map((p, i) => fill(t('ar_ad_part'), { n: i + 1, p })).join(' · ')}</div>}
          {(hub.xp_bonus_pct > 0 || hub.extra_attempts > 0) && <div className="text-[11px] text-amber-300">💎 {fill(t('ar_founder'), { p: hub.xp_bonus_pct, n: hub.extra_attempts })}</div>}
        </div>

        <Top5 game={game.id} t={t} />

        {promoOn && (
          <div className="space-y-2" data-testid="arcade-promo-detail">
            <div className="rounded-2xl border border-amber-400/25 bg-amber-500/[0.06] p-3 text-[12px] text-white/80 flex items-start gap-2">
              <Gift className="w-4 h-4 text-amber-300 shrink-0 mt-0.5" />
              <span>{fill(t('gm_chest_from'), { n: nf(ghGame(game.id)?.chest_score || game.target_score), b: gh.chests_per_day })}</span>
            </div>
            <MgLeaderboard lang={lang} t={t} game={game.id} myId={gh?.user_id} compact title={t('gm_leaders')} refreshKey={`${game.id}-${gh?.chests_today}`} />
            <button type="button" onClick={() => navigate(`/games/${game.id}/rewards`)} data-testid="arcade-rewards-btn"
              className="w-full h-12 rounded-2xl bg-gradient-to-r from-[#fde68a] via-[#f2b134] to-[#f59e0b] text-[#2a1600] font-black flex items-center justify-center gap-2 active:scale-[0.98] shadow-[0_6px_18px_rgba(242,177,52,.25)]">
              <Gift className="w-4 h-4" />{t('gr_open')}
              {ghGame(game.id)?.nft ? <span className="ml-1 rounded-md bg-black/15 px-1.5 py-0.5 text-[11px]">🧩 {ghGame(game.id).nft.have}/{ghGame(game.id).nft.total}</span> : null}
            </button>
          </div>
        )}
      </div>
    );
  }

  /* ── hub ── */
  const cap = hub.daily_xp_cap || 0;
  return (
    <div className="space-y-4 pb-4" data-testid="arcade-hub">
      {chestReveal}
      {preview && hub.preview_only && (
        <div className="rounded-xl border border-cyan-400/40 bg-cyan-500/10 text-cyan-100 text-[11px] p-2.5">Превью: Аркада выключена — игроки её пока не видят. Здесь можно сыграть: попытки не тратятся, XP не начисляются.</div>
      )}
      <div className="relative overflow-hidden rounded-3xl border border-amber-400/25 bg-gradient-to-br from-[#2a1d0b] via-[#17120a] to-[#1a0b2e] p-4">
        <div className="pointer-events-none absolute -right-10 -top-10 w-40 h-40 rounded-full bg-amber-500/20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-b from-[#fde68a] to-[#f2b134] flex items-center justify-center shadow-lg"><Gamepad2 className="w-6 h-6 text-[#2a1600]" /></div>
          <div className="min-w-0 flex-1">
            <div className="text-xl font-black text-white">{embedded || preview ? t('ar_title') : t('gm_title')}</div>
            <div className="text-[12px] text-white/65">{embedded || preview ? t('ar_sub') : t('gm_sub')}</div>
          </div>
          {!embedded && !preview && (
            <button type="button" onClick={() => navigate('/minigames/rewards')} data-testid="games-rewards-btn"
              className="shrink-0 h-10 px-3 rounded-xl bg-gradient-to-b from-[#fde68a] to-[#f2b134] text-[#2a1600] text-xs font-black flex items-center gap-1.5 active:scale-95">
              <Gift className="w-4 h-4" />{t('gm_rewards')}
            </button>
          )}
        </div>
        {hub.visible && <div className="relative mt-3">
          <div className="text-[12px] text-white/80 mb-1 flex items-center gap-1"><Zap className="w-3.5 h-3.5 text-amber-300" />{cap ? fill(t('ar_xp_today'), { a: hub.xp_today, b: cap }) : fill(t('ar_xp_today_nl'), { a: hub.xp_today })}</div>
          {cap > 0 && <div className="h-1.5 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-gradient-to-r from-amber-300 to-amber-500" style={{ width: `${Math.min(100, (hub.xp_today / cap) * 100)}%` }} /></div>}
        </div>}
      </div>

      {hub.pending_rewards?.length > 0 && (
        <div className="rounded-2xl border border-violet-400/30 bg-violet-500/[0.07] p-3 space-y-2" data-testid="arcade-unclaimed">
          <div className="text-[11px] uppercase tracking-wider text-violet-200 font-bold">{t('ar_unclaimed')}</div>
          {hub.pending_rewards.map((r) => (
            <button type="button" key={r.id} onClick={() => showOwed(r.id)} className="w-full flex items-center gap-2.5 text-left rounded-xl bg-black/25 p-2 hover:bg-black/35">
              <span className="text-2xl">{GAME_ICON[r.game]}</span>
              <span className="flex-1 min-w-0">
                <span className="block text-sm font-bold text-white truncate">{t(`ar_g_${r.game}`)}</span>
                <span className="block text-[11px] text-amber-200/90">{fill(t('ar_collected'), { a: r.xp_unlocked, b: r.xp_total })}</span>
              </span>
              <span className="text-[11px] font-bold text-white bg-violet-600 rounded-lg px-2 py-1 flex items-center gap-1"><Clapperboard className="w-3 h-3" />{t('ar_get_rest')}</span>
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        {gh && ghGame('sorter') && (
          <button type="button" onClick={() => (ghGame('sorter').playable ? navigate('/minigames/sorter') : toast(t('gm_sorter_off')))} data-testid="games-card-sorter"
            className={`relative overflow-hidden rounded-3xl bg-gradient-to-br from-amber-500 via-orange-600 to-rose-700 p-3 text-left min-h-[140px] flex flex-col active:scale-[0.98] transition-transform shadow-lg ${ghGame('sorter').playable ? '' : 'opacity-55'}`}>
            <div className="absolute -right-3 -bottom-4 text-6xl opacity-25 select-none">📦</div>
            <div className="text-3xl drop-shadow">📦</div>
            <div className="mt-auto relative">
              <div className="text-[14px] font-black text-white leading-tight drop-shadow">{t('mg_sorter_title')}</div>
              <div className="text-[10px] text-white/85">{ghGame('sorter').playable ? t('gm_sorter_sub') : t('gm_sorter_off')}</div>
              <div className="flex items-center justify-between mt-1.5 gap-1">
                <span className="text-[10px] font-black text-amber-100 bg-black/35 rounded-md px-1.5 py-0.5 flex items-center gap-0.5"><Gift className="w-3 h-3" />{ghGame('sorter').place ? fill(t('gm_place'), { n: ghGame('sorter').place }) : t('gm_rewards')}</span>
                {ghGame('sorter').nft ? <span className="text-[10px] font-black rounded-md px-1.5 py-0.5 bg-black/35 text-amber-100">🧩 {ghGame('sorter').nft.have}/{ghGame('sorter').nft.total}</span>
                  : ghGame('sorter').best > 0 && <span className="text-[10px] font-bold rounded-md px-1.5 py-0.5 bg-white/20 text-white truncate">{nf(ghGame('sorter').best)}</span>}
              </div>
            </div>
            <ChevronRight className="absolute right-2 top-3 w-4 h-4 text-white/60" />
          </button>
        )}
        {arcadeGames.map((g) => (
          <button type="button" key={g.id} onClick={() => openGame(g.id)} data-testid={`arcade-game-${g.id}`}
            className={`relative overflow-hidden rounded-3xl bg-gradient-to-br ${GAME_GRAD[g.id]} p-3 text-left min-h-[140px] flex flex-col active:scale-[0.98] transition-transform shadow-lg ${!g.enabled ? 'opacity-50' : ''}`}>
            <div className="absolute -right-3 -bottom-4 text-6xl opacity-25 select-none">{GAME_ICON[g.id]}</div>
            <div className="text-3xl drop-shadow">{GAME_ICON[g.id]}</div>
            <div className="mt-auto relative">
              <div className="text-[14px] font-black text-white leading-tight drop-shadow">{t(`ar_g_${g.id}`)}</div>
              <div className="text-[10px] text-white/85">{t(`ar_t_${g.id}`)}{!g.enabled ? ' · выкл.' : ''}</div>
              <div className="flex items-center justify-between mt-1.5 gap-1">
                <span className="text-[10px] font-black text-amber-200 bg-black/35 rounded-md px-1.5 py-0.5 flex items-center gap-0.5"><Zap className="w-3 h-3" />{g.max_xp}</span>
                <span className={`text-[10px] font-bold rounded-md px-1.5 py-0.5 ${g.attempts_left ? 'bg-white/20 text-white' : 'bg-black/40 text-white/60'}`}>{g.attempts_left}/{g.attempts_max}</span>
              </div>
              {(promoOn && ghGame(g.id)?.place) || ghGame(g.id)?.nft ? (
                <div className="mt-1 flex items-center gap-1.5 text-[10px] font-black text-amber-100">
                  {promoOn && ghGame(g.id)?.place ? <span>🏆 {fill(t('gm_place'), { n: ghGame(g.id).place })}</span> : null}
                  {ghGame(g.id)?.nft ? <span className="rounded-md bg-black/35 px-1.5 py-0.5">🧩 {ghGame(g.id).nft.have}/{ghGame(g.id).nft.total}</span> : null}
                </div>
              ) : null}
            </div>
            <ChevronRight className="absolute right-2 top-3 w-4 h-4 text-white/60" />
          </button>
        ))}
      </div>
    </div>
  );
}
