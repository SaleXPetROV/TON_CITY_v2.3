/**
 * «Награды» of ONE game (backend/game_nfts.py → GET /api/games/:game/nft-track):
 *   • every NFT of the game as a row: its small picture on the left, the 9-piece bar on the right (how many pieces the
 *     player has); a tap opens the NFT whole (picture / GIF / video), the map of the pieces and «Собрать» at 9/9;
 *   • the week: the player's place and the top 5 with their prizes; how pieces are obtained (the chest of a good
 *     game, given after every ad of the reward, always holds one piece).
 * NFT switched off for the game → a teaser («NFT are coming»), the points already count.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, Check, ChevronRight, Clock, Gift, Lock, Play, Puzzle, Trophy, Wallet, X } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslation } from '@/lib/translations';
import { fill } from '@/lib/translationsMore';
import { onProgress } from '@/lib/progressBus';
import { mgCall, nm, imgUrl, PrizeBadge, useLinkWallet, NFT_ST_KEY, tonviewer } from '@/components/minigames/mgShared';
import NftMedia from '@/components/minigames/NftMedia';
import { GAME_ICON, GAME_GRAD } from '@/arcade/core';

const nf = (n) => Number(n || 0).toLocaleString('ru-RU');
const gameIcon = (g) => (g === 'sorter' ? '📦' : GAME_ICON[g] || '🎮');
const gameName = (g, t) => (g === 'sorter' ? t('mg_sorter_title') : t(`ar_g_${g}`));
const gameGrad = (g) => GAME_GRAD[g] || 'from-amber-500 via-orange-600 to-rose-700';

const CSS = `
@keyframes gr-tile-in { 0% { transform: perspective(400px) rotateY(80deg) scale(.7); opacity: 0 } 100% { transform: none; opacity: 1 } }
@keyframes gr-spin { to { transform: rotate(360deg) } }
@keyframes gr-sheen { 0% { transform: translateX(-120%) } 60%, 100% { transform: translateX(220%) } }
@keyframes gr-sheet { 0% { transform: translateY(24px) scale(.98); opacity: 0 } 100% { transform: none; opacity: 1 } }
@keyframes gr-fade { from { opacity: 0 } to { opacity: 1 } }
.gr-tile-in { animation: gr-tile-in .55s cubic-bezier(.2,.9,.3,1.25) both }
.gr-sheet { animation: gr-sheet .32s cubic-bezier(.2,.9,.3,1) both }
.gr-fade { animation: gr-fade .2s ease-out both }
.gr-ring { position: absolute; inset: -1.5px; border-radius: 20px; padding: 1.5px; overflow: hidden; pointer-events: none;
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude }
.gr-ring::before { content: ''; position: absolute; inset: -150%; background: conic-gradient(from 0deg, #fde68a, #f2b134, #e879f9, #22d3ee, #fde68a); animation: gr-spin 3.2s linear infinite }
.gr-sheen::after { content: ''; position: absolute; inset: 0; width: 40%; background: linear-gradient(100deg, transparent, rgba(255,255,255,.55), transparent); animation: gr-sheen 2.4s ease-in-out infinite }
@media (prefers-reduced-motion: reduce) { .gr-tile-in, .gr-sheet, .gr-fade, .gr-ring::before, .gr-sheen::after { animation: none !important } }
`;

/** Nine segments: the pieces the player has, at a glance. */
function PieceBar({ have, done }) {
  return (
    <div className="flex gap-[3px]" aria-hidden>
      {Array.from({ length: 9 }, (_, i) => (
        <span key={i} className={`h-2 flex-1 rounded-[3px] ${done ? 'bg-emerald-400/80'
          : i < have ? 'bg-gradient-to-b from-[#fde68a] to-[#f2b134] shadow-[0_0_6px_rgba(253,230,138,.45)]' : 'bg-white/[0.09]'}`} />
      ))}
    </div>
  );
}

/** One NFT of the game: a small picture + the bar of pieces. */
function NftRow({ n, lang, t, onOpen }) {
  const complete = n.status === 'complete';
  const assembled = n.status === 'assembled';
  const soldOut = n.status === 'none' && n.left <= 0;
  return (
    <button type="button" onClick={() => onOpen(n)} data-testid={`gr-nft-${n.puzzle_id}`}
      className={`relative w-full text-left flex items-center gap-3 rounded-[20px] border p-2.5 pr-3 transition active:scale-[0.99] ${
        complete ? 'border-transparent bg-amber-300/[0.07]' : 'border-white/10 bg-white/[0.04] hover:bg-white/[0.06]'} ${soldOut ? 'opacity-55' : ''}`}>
      {complete && <span className="gr-ring" />}
      <div className="relative w-16 h-16 shrink-0 rounded-[14px] overflow-hidden bg-[#120d1f] ring-1 ring-white/10">
        <NftMedia src={n.media_url} type={n.media_type} poster={n.image_url} still className="w-full h-full object-cover" />
        {n.media_type === 'video' && (
          <span className="absolute right-1 bottom-1 w-5 h-5 rounded-full bg-black/65 flex items-center justify-center"><Play className="w-2.5 h-2.5 text-white fill-white" /></span>
        )}
        {assembled && (
          <span className="absolute left-1 top-1 w-5 h-5 rounded-full bg-emerald-400 flex items-center justify-center"><Check className="w-3 h-3 text-[#06281a]" strokeWidth={3.5} /></span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <div className="min-w-0 flex-1 truncate text-[15px] font-bold text-white">{nm(n, lang)}</div>
          <div className={`shrink-0 text-[15px] font-black tabular-nums ${assembled ? 'text-emerald-300' : 'text-amber-200'}`} data-testid="gr-have">
            {assembled ? '9/9' : `${n.have}/9`}
          </div>
        </div>
        <div className="mt-1.5"><PieceBar have={n.have} done={assembled} /></div>
        <div className="mt-1.5 flex items-center gap-1 text-[11px]">
          {complete ? <span className="font-bold text-amber-200">{t('pz_assemble')}</span>
            : assembled ? <span className="font-semibold text-emerald-300">{t('gr_assembled')}</span>
              : <span className="text-white/45 truncate">{soldOut ? t('gr_sold_out') : fill(t('gr_left'), { n: nf(n.left) })}</span>}
          <ChevronRight className="ml-auto w-3.5 h-3.5 text-white/30 shrink-0" />
        </div>
      </div>
    </button>
  );
}

/** The map of the 9 pieces: the collected ones are the real art, the missing ones dark. */
function PieceMap({ n }) {
  const have = new Set(n.pieces || []);
  const all = n.status === 'assembled';
  let k = 0;
  return (
    <div className="w-[104px] shrink-0 aspect-square rounded-[14px] overflow-hidden bg-[#120d1f] p-[2px]"
      style={n.ghost_url ? { backgroundImage: `url(${imgUrl(n.ghost_url)})`, backgroundSize: 'cover' } : undefined} data-testid="gr-map">
      <div className="grid grid-cols-3 grid-rows-3 gap-[2px] w-full h-full">
        {Array.from({ length: 9 }, (_, i) => i + 1).map((p) => {
          const got = all || have.has(p);
          const url = n.piece_urls?.[String(p)] || (all ? `/api/minigames/img/puzzle_${n.puzzle_id}_${p}.webp` : null);
          return got ? (
            <div key={p} className="gr-tile-in rounded-[4px] overflow-hidden ring-1 ring-amber-200/60" style={{ animationDelay: `${(k += 1) * 60}ms` }} data-testid={`gr-piece-${p}`}>
              {url ? <img src={imgUrl(url)} alt="" className="w-full h-full object-cover" /> : <div className="w-full h-full bg-gradient-to-br from-amber-300 to-fuchsia-500" />}
            </div>
          ) : (
            <div key={p} className="rounded-[4px] bg-black/50 border border-white/[0.06] flex items-center justify-center">
              <span className="text-[9px] font-bold text-white/25">{p}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** The NFT whole: the art (picture / GIF / video), the map of the pieces, «Собрать» at 9/9. */
function NftModal({ n, lang, t, net, walletLinked, howText, onAssemble, busy, onClose }) {
  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [onClose]);
  const complete = n.status === 'complete';
  const assembled = n.status === 'assembled';
  const st = NFT_ST_KEY(n.grant, walletLinked);
  return (
    <div className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center" role="dialog" aria-modal="true" data-testid="gr-modal">
      <div className="gr-fade absolute inset-0 bg-black/75 backdrop-blur-sm" onClick={onClose} />
      <div className="gr-sheet relative w-full max-w-md max-h-[94vh] overflow-y-auto rounded-t-[28px] sm:rounded-[28px] border border-white/10 bg-[#0f0c19] p-3"
        style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 0.9rem)' }}>
        <div className="relative rounded-[22px] overflow-hidden bg-[#120d1f] ring-1 ring-white/10 aspect-square">
          <NftMedia src={n.media_url} type={n.media_type} poster={n.image_url} className="w-full h-full object-cover" testid="gr-modal-media" />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/70 to-transparent" />
          <div className="absolute left-3 right-14 bottom-3">
            <div className="text-[20px] leading-tight font-black text-white drop-shadow">{nm(n, lang)}</div>
            <div className="text-[11px] text-white/70">{n.kind === 'sbt' ? 'SBT' : 'NFT'} · {fill(t('gr_left'), { n: nf(n.left) })}</div>
          </div>
          <button type="button" onClick={onClose} aria-label="close" data-testid="gr-modal-close"
            className="absolute right-2.5 top-2.5 w-9 h-9 rounded-full bg-black/55 backdrop-blur flex items-center justify-center text-white active:scale-95">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-3 flex gap-3 items-stretch">
          <PieceMap n={n} />
          <div className="min-w-0 flex-1 flex flex-col">
            <div className={`text-[26px] leading-none font-black tabular-nums ${assembled ? 'text-emerald-300' : 'text-amber-200'}`}>{assembled ? '9/9' : `${n.have}/9`}</div>
            <div className="mt-1 text-[12px] text-white/70">{fill(t('gr_have_of'), { a: assembled ? 9 : n.have })}</div>
            <div className="mt-2"><PieceBar have={n.have} done={assembled} /></div>
            {!complete && !assembled && <div className="mt-auto pt-2 text-[11px] leading-snug text-white/50">{howText}</div>}
          </div>
        </div>

        {complete && (
          <button type="button" disabled={busy} onClick={() => onAssemble(n)} data-testid="gr-assemble"
            className="gr-sheen relative overflow-hidden mt-3 w-full h-12 rounded-2xl bg-gradient-to-r from-[#fde68a] via-[#f2b134] to-[#f59e0b] text-[#2a1600] text-[15px] font-black active:scale-[0.98] disabled:opacity-60">
            {t('pz_assemble')}
          </button>
        )}
        {assembled && (
          <div className="mt-3 rounded-2xl bg-emerald-400/10 border border-emerald-300/25 px-3 py-2.5 text-[13px] font-semibold text-emerald-200">
            {t('gr_assembled')}
            {st && <span className="block text-[12px] text-white/70 font-normal mt-0.5">{t(st)}
              {n.grant?.status === 'delivered' && n.grant?.nft_address && (
                <a className="ml-1.5 underline text-cyan-300" href={tonviewer(n.grant.nft_address, net)} target="_blank" rel="noreferrer">{t('rw_tonviewer')}</a>
              )}
            </span>}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ icon: Icon, title, sub, children, testid }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-[#0f0c19]/80 p-4" data-testid={testid}>
      <div className="flex items-center gap-2 text-white font-bold"><Icon className="w-4 h-4 text-amber-300" />{title}</div>
      {sub && <div className="text-[12px] text-white/50 mt-0.5 mb-3 leading-snug">{sub}</div>}
      {!sub && <div className="h-3" />}
      {children}
    </section>
  );
}

export default function GameRewardsPage() {
  const { gameId: game } = useParams();
  const navigate = useNavigate();
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [needWallet, setNeedWallet] = useState(false);
  const [openId, setOpenId] = useState(null);

  const load = useCallback(async () => {
    try { setD(await mgCall(`/games/${encodeURIComponent(game)}/nft-track`)); } catch (e) { toast.error(e.message); }
  }, [game]);
  useEffect(() => { load(); return onProgress(load); }, [load]);
  const { link, busy: linking } = useLinkWallet(t, () => { setNeedWallet(false); load(); });

  const assemble = async (n) => {
    setBusy(true);
    try {
      const r = await mgCall(`/minigames/puzzles/${n.puzzle_id}/assemble`, { method: 'POST' });
      if (r.need_wallet) { setNeedWallet(true); setOpenId(null); } else { toast.success(t('pz_sent')); await load(); }
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  const nfts = useMemo(() => (d?.nfts || []).filter((n) => n.is_active || n.status !== 'none'), [d]);
  const opened = nfts.find((n) => n.puzzle_id === openId);
  const have = nfts.reduce((s, n) => s + (n.status === 'assembled' ? 9 : n.have), 0);
  const total = nfts.length * 9;
  const back = () => navigate(game === 'sorter' ? '/minigames/sorter' : `/games/${game}`);
  const week = d?.week;
  const daysLeft = week?.ends_at ? Math.max(0, Math.ceil((new Date(week.ends_at) - Date.now()) / 86400000)) : null;
  const on = d?.enabled && nfts.length > 0;
  const howText = d ? (d.chests?.after_ads ? fill(t('gr_how_chest'), { n: nf(d.chests?.min_score) }) : t('gr_how_chest_s')) : '';
  const close = useCallback(() => setOpenId(null), []);

  return (
    <div className="min-h-screen max-w-lg mx-auto px-4 pb-28 space-y-4" style={{ paddingTop: 'calc(var(--tg-safe-top, 0px) + 0.75rem)' }} data-testid="game-rewards">
      <style>{CSS}</style>
      <div className="flex items-center gap-2">
        <button type="button" onClick={back} className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-white active:scale-95" data-testid="gr-back">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="text-lg font-black text-white">{t('gm_rewards')}</div>
      </div>

      {/* hero: the game and how much of its collection is gathered */}
      <div className={`relative overflow-hidden rounded-[28px] bg-gradient-to-br ${gameGrad(game)} p-4`}>
        <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_100%_0%,rgba(0,0,0,0)_0%,rgba(10,6,20,.72)_70%)]" />
        <div className="absolute -right-4 -bottom-6 text-[110px] leading-none opacity-20 select-none">{gameIcon(game)}</div>
        <div className="relative">
          <div className="flex items-center gap-2 text-white/85 text-sm font-semibold"><span className="text-xl">{gameIcon(game)}</span>{gameName(game, t)}</div>
          {on ? (
            <>
              <div className="mt-3 text-[12px] text-white/70">{t('gr_pieces_got')}</div>
              <div className="flex items-baseline gap-1.5" data-testid="gr-total">
                <span className="text-[40px] leading-none font-black text-white tracking-tight tabular-nums">{have}</span>
                <span className="text-lg font-black text-white/55">/ {total}</span>
              </div>
              <div className="mt-3 h-2.5 rounded-full bg-black/35 overflow-hidden ring-1 ring-white/10">
                <div className="h-full rounded-full bg-gradient-to-r from-[#fde68a] to-[#f2b134] shadow-[0_0_12px_rgba(253,230,138,.6)]" style={{ width: `${total ? (have / total) * 100 : 0}%` }} />
              </div>
            </>
          ) : (
            <div className="mt-3 text-[13px] text-white/80 leading-snug max-w-[80%]">{d ? fill(t('gm_chest_need'), { n: nf(d.chests?.min_score) }) : '…'}</div>
          )}
        </div>
      </div>

      {!d ? <div className="h-64 rounded-3xl bg-white/5 animate-pulse" /> : (
        <>
          {needWallet && (
            <div className="rounded-2xl border border-cyan-400/40 bg-cyan-500/10 p-3 space-y-2">
              <div className="text-sm font-bold text-cyan-100 flex items-center gap-2"><Wallet className="w-4 h-4" />{t('pz_need_wallet_t')}</div>
              <div className="text-[12px] text-white/70">{t('pz_need_wallet')}</div>
              <button type="button" onClick={link} disabled={linking} className="w-full h-10 rounded-xl bg-cyan-400 text-black font-black disabled:opacity-60">{t('rw_link_wallet')}</button>
            </div>
          )}

          {/* the NFTs of the game (or the teaser while NFT are off for this game) */}
          {on ? (
            <Section icon={Puzzle} title={t('gr_collection')} sub={t('gr_collection_s')} testid="gr-collection">
              <div className="space-y-2">
                {nfts.map((n) => <NftRow key={n.puzzle_id} n={n} lang={lang} t={t} onOpen={(x) => setOpenId(x.puzzle_id)} />)}
              </div>
            </Section>
          ) : (
            <section className="relative overflow-hidden rounded-3xl border border-fuchsia-300/20 bg-gradient-to-b from-[#1d1233] to-[#0f0c19] p-4" data-testid="gr-soon">
              <div className="flex gap-4 items-center">
                <div className="relative w-28 shrink-0 aspect-square rounded-2xl bg-[#120d1f] p-[3px] overflow-hidden">
                  <div className="grid grid-cols-3 grid-rows-3 gap-[3px] w-full h-full">
                    {Array.from({ length: 9 }, (_, i) => (
                      <div key={i} className="rounded-[5px] bg-gradient-to-br from-fuchsia-400/20 to-cyan-300/10 border border-white/[0.06] flex items-center justify-center">
                        {i === 4 ? <Lock className="w-4 h-4 text-white/50" /> : null}
                      </div>
                    ))}
                  </div>
                  <span className="gr-sheen absolute inset-0" />
                </div>
                <div className="min-w-0">
                  <div className="text-lg font-black text-white">{t('gr_soon')}</div>
                  <div className="text-[12px] text-white/65 leading-snug mt-1">{t('gr_soon_t')}</div>
                </div>
              </div>
            </section>
          )}

          {week && (
            <Section icon={Trophy} title={t('gr_week')} sub={t('gr_week_top')} testid="gr-week">
              <div className="flex items-center justify-between gap-2 mb-2 text-[12px]">
                <span className="text-white/80 font-semibold">{week.place ? fill(t('gr_week_me'), { n: week.place, p: nf(week.points) }) : t('gr_week_none')}</span>
                {daysLeft !== null && <span className="flex items-center gap-1 text-white/50"><Clock className="w-3 h-3" />{fill(t('gm_ends_in'), { n: daysLeft })}</span>}
              </div>
              <div className="space-y-1">
                {Array.from({ length: 5 }, (_, i) => {
                  const r = (week.leaders || [])[i];
                  const prize = (week.prizes || []).find((p) => p.from <= i + 1 && i + 1 <= p.to);
                  const medal = ['from-[#fde68a] to-[#f2b134] text-[#2a1600]', 'from-slate-100 to-slate-400 text-slate-900', 'from-orange-300 to-amber-700 text-[#2a1600]'][i] || 'from-white/15 to-white/5 text-white/80';
                  const mine = r && r.user_id === d.user_id;
                  return (
                    <div key={i} className={`flex items-center gap-2 rounded-xl px-2 py-1.5 ${mine ? 'bg-cyan-400/10 ring-1 ring-cyan-300/40' : 'bg-white/[0.03]'}`}>
                      <span className={`w-7 h-7 shrink-0 rounded-full bg-gradient-to-b ${medal} flex items-center justify-center text-[12px] font-black`}>{i + 1}</span>
                      <span className="flex-1 min-w-0 truncate text-[13px] text-white/85">{r ? `@${r.username}` : '—'}</span>
                      {prize && <PrizeBadge prize={prize} lang={lang} t={t} />}
                      <span className="w-14 text-right text-[12px] font-bold text-amber-200">{r ? nf(r.points) : ''}</span>
                    </div>
                  );
                })}
              </div>
            </Section>
          )}

          <Section icon={Gift} title={t('gr_how')} testid="gr-how">
            <div className="space-y-2 text-[13px] text-white/80">
              <div className="flex gap-2.5"><span className="text-lg leading-none">🎁</span>
                <span>{on ? howText : fill(t('gm_chest_need'), { n: nf(d.chests?.min_score) })}
                  {d.chests?.per_day ? <span className="text-white/45"> · {fill(t('gm_chests'), { a: d.chests.today, b: d.chests.per_day })}</span> : null}</span>
              </div>
              {on && <div className="flex gap-2.5"><span className="text-lg leading-none">🧩</span><span>{t('gr_how_pick')}</span></div>}
            </div>
          </Section>
        </>
      )}

      {opened && (
        <NftModal n={opened} lang={lang} t={t} net={d?.nft_network} walletLinked={d?.has_wallet} howText={howText}
          onAssemble={assemble} busy={busy} onClose={close} />
      )}
    </div>
  );
}
