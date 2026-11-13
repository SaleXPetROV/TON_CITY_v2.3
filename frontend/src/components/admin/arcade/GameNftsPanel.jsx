/**
 * «NFT по играм» (backend/game_nfts.py). Click a game → its NFTs: add / take out, how many of each can be collected
 * (− / +), how many are given / being collected; NFT in the game on / off (off = the game runs for points only).
 * A chest of a good game is given after EVERY ad of the game's reward and holds a 1/9 piece for sure.
 * An NFT is a picture, a GIF or a video (its frame is cut into the 9 pieces).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { ImagePlus, Minus, Plus, Puzzle, Trash2, X } from 'lucide-react';
import { MG_GAMES } from '@/components/admin/minigames/mgAdminKit';
import NftMedia, { videoPoster } from '@/components/minigames/NftMedia';
import { GAME_GRAD } from '@/arcade/core';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/admin`;
const nameOf = (g) => (MG_GAMES.find(([id]) => id === g) || [g, g])[1];
const nf = (v) => Number(v || 0).toLocaleString('ru-RU');

export default function GameNftsPanel({ token }) {
  const h = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(null);
  const load = useCallback(async () => {
    try { setData((await axios.get(`${API}/game-nfts`, h)).data); } catch (e) { toast.error(e?.response?.data?.detail || 'Не удалось загрузить NFT игр'); }
  }, [h]);
  useEffect(() => { load(); }, [load]);
  if (!data) return <div className="text-sm text-text-muted">Загрузка…</div>;
  const game = data.games.find((g) => g.game === open);

  return (
    <div className="space-y-4" data-testid="game-nfts">
      <div className="rounded-xl border border-fuchsia-400/25 bg-fuchsia-500/5 p-3 text-[12px] text-white/75 leading-relaxed">
        У каждой игры — свой набор NFT (картинка, GIF или видео). Каждый NFT делится на 9 частей (3×3), их игрок собирает в этой игре.
        <b className="text-white">Сундук за хорошую партию даётся только после просмотра всех реклам награды</b> (1-я реклама — 2/4 XP, каждая следующая +1/4, последняя — вся награда + сундук),
        и в сундуке <b className="text-white">всегда 1 часть NFT</b> этой игры. Какой из NFT игры — выбирается случайно среди тех, что ещё можно собрать.
        9/9 → «Собрать» → NFT на кошелёк игрока. Пока «NFT в игре» выключено, игра идёт только за очки, сундук — без части NFT.
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-2.5">
        {data.games.map((g) => (
          <button key={g.game} type="button" onClick={() => setOpen(g.game)} data-testid={`gn-game-${g.game}`}
            className={`relative overflow-hidden text-left rounded-2xl p-3 border transition ${open === g.game ? 'border-amber-300/80 ring-1 ring-amber-300/50' : 'border-white/10 hover:border-white/30'}`}>
            <div className={`absolute inset-0 opacity-25 bg-gradient-to-br ${GAME_GRAD[g.game] || 'from-amber-500 via-orange-600 to-rose-600'}`} />
            <div className="relative">
              <div className="text-sm font-bold text-white truncate">{nameOf(g.game)}</div>
              <div className="mt-1.5 flex items-center gap-1.5 text-[11px]">
                <span className={`px-1.5 py-0.5 rounded-md font-bold ${g.enabled ? 'bg-emerald-500/25 text-emerald-200' : 'bg-white/10 text-white/60'}`}>{g.enabled ? 'NFT вкл.' : 'только очки'}</span>
                <span className="text-white/70">NFT: <b className="text-white">{g.nfts.length}</b></span>
              </div>
              <div className="mt-1 text-[10px] text-white/55">собирают: {nf(g.players_with_pieces)}</div>
            </div>
          </button>
        ))}
      </div>
      {game && <GameDetail key={game.game} g={game} free={data.free_puzzles} h={h} onData={setData} onClose={() => setOpen(null)} />}
    </div>
  );
}

function GameDetail({ g, free, h, onData, onClose }) {
  const [busy, setBusy] = useState(false);
  const run = async (fn, ok) => {
    setBusy(true);
    try { const r = await fn(); onData(r.data); if (ok) toast.success(ok); return true; } catch (e) { toast.error(e?.response?.data?.detail || 'Ошибка'); return false; } finally { setBusy(false); }
  };
  const put = (body, ok) => run(() => axios.put(`${API}/game-nfts/${g.game}`, body, h), ok);
  const totalLeft = g.nfts.reduce((s, n) => s + n.left, 0);

  return (
    <div className="rounded-2xl border border-white/10 bg-[#0f0d18] overflow-hidden" data-testid="gn-detail">
      <div className={`relative px-4 py-3 bg-gradient-to-r ${GAME_GRAD[g.game] || 'from-amber-500 via-orange-600 to-rose-600'}`}>
        <div className="absolute inset-0 bg-black/45" />
        <div className="relative flex items-center gap-3">
          <div className="text-lg font-black text-white flex-1 truncate">{nameOf(g.game)} · NFT</div>
          <label className="flex items-center gap-2 text-sm text-white font-semibold" data-testid="gn-enabled">
            <Switch checked={g.enabled} disabled={busy} onCheckedChange={(v) => put({ enabled: v }, v ? 'NFT в игре включены' : 'Игра идёт только за очки')} />
            NFT в этой игре
          </label>
          <button type="button" onClick={onClose} className="text-white/70 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
      </div>

      <div className="p-4 space-y-5">
        {!g.enabled && (
          <div className="rounded-lg border border-white/10 bg-white/5 p-2.5 text-[12px] text-white/70">
            Сейчас игра идёт <b className="text-white">только за очки</b>: в сундуках нет частей NFT. Добавьте NFT ниже и включите переключатель.
          </div>
        )}
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-[12px] text-white/70 space-y-1">
          <div className="text-sm font-bold text-white">🎁 Как игрок получает часть</div>
          <div>Партия от <b className="text-white">{nf(g.good_game_score)}</b> очков → игрок смотрит <b className="text-white">все рекламы награды</b> → сундук → в нём 1/9 часть одного из NFT игры (100 %).</div>
          <div className="text-[11px] text-text-muted">Очки партии для сундука, лимит сундуков в день — в «Рейтинг недели, призы, сундук»; число реклам и доли XP — в настройках Аркады. Если реклама выключена, сундук даётся сразу.</div>
        </div>

        {/* the NFTs of the game */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-bold text-white flex items-center gap-2"><Puzzle className="w-4 h-4 text-fuchsia-300" />NFT игры: {g.nfts.length} · можно ещё собрать: {nf(totalLeft)}</div>
          </div>
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
            {g.nfts.map((n) => <NftCard key={n.puzzle_id} n={n} g={g} h={h} run={run} busy={busy} />)}
            <AddNft g={g} h={h} run={run} busy={busy} />
          </div>
          {free.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-text-muted">
              Добавить уже созданный NFT (из «🧩 Пазлы»):
              <select className="bg-panel border border-grid-border rounded-md px-2 py-1 text-white" defaultValue=""
                onChange={(e) => { const pid = e.target.value; e.target.value = ''; if (pid) run(() => axios.post(`${API}/game-nfts/${g.game}/attach`, { puzzle_id: pid }, h), 'NFT добавлен в игру'); }}>
                <option value="">выбрать…</option>
                {free.map((p) => <option key={p.puzzle_id} value={p.puzzle_id}>{p.name}</option>)}
              </select>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function NftCard({ n, g, h, run, busy }) {
  const [val, setVal] = useState(n.supply_total);
  useEffect(() => { setVal(n.supply_total); }, [n.supply_total]);
  const floor = Math.max(1, n.granted + n.collecting);
  const setSupply = (v) => run(() => axios.put(`${API}/game-nfts/supply/${n.nft_id}`, { supply_total: v }, h), `«${n.name}»: можно получить ${v}`);
  const usedPct = n.supply_total ? Math.min(100, ((n.granted + n.collecting) / n.supply_total) * 100) : 0;
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 flex gap-3" data-testid={`gn-nft-${n.puzzle_id}`}>
      <div className="relative w-24 h-24 shrink-0 rounded-lg overflow-hidden border border-white/10 bg-black/40">
        {n.media_url || n.image_url
          ? <NftMedia src={n.media_url} type={n.media_type} poster={n.image_url} className="w-full h-full object-cover" />
          : <div className="w-full h-full flex items-center justify-center text-white/30 text-[10px]">нет файла</div>}
        {n.media_type && n.media_type !== 'image' && (
          <span className="absolute left-1 top-1 px-1 rounded bg-black/70 text-[9px] font-bold text-white">{n.media_type === 'video' ? 'ВИДЕО' : 'GIF'}</span>
        )}
      </div>
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex items-start gap-1">
          <div className="text-sm font-bold text-white truncate flex-1">{n.name}</div>
          <button type="button" title="Убрать из игры (собранные части остаются у игроков)" disabled={busy}
            onClick={() => { if (window.confirm(`Убрать «${n.name}» из игры? Новые части выпадать не будут; уже собранные части останутся у игроков.`)) run(() => axios.delete(`${API}/game-nfts/${g.game}/nfts/${n.puzzle_id}`, h), 'Убрано из игры'); }}
            className="text-white/40 hover:text-red-300"><Trash2 className="w-4 h-4" /></button>
        </div>
        <div className="text-[10px] text-white/50">{n.kind === 'sbt' ? 'SBT (не передаётся)' : 'передаваемый'}</div>
        <div className="text-[11px] text-white/70">Можно получить:</div>
        <div className="flex items-center gap-1">
          <button type="button" disabled={busy || n.supply_total <= floor} onClick={() => setSupply(n.supply_total - 1)} className="w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 disabled:opacity-30 flex items-center justify-center"><Minus className="w-3.5 h-3.5" /></button>
          <Input type="number" min={floor} value={val} onChange={(e) => setVal(e.target.value)} onBlur={() => { const v = Number(val); if (v && v !== n.supply_total) setSupply(v); }}
            className="w-16 h-7 text-center bg-panel border-grid-border" data-testid={`gn-supply-${n.puzzle_id}`} />
          <button type="button" disabled={busy} onClick={() => setSupply(n.supply_total + 1)} className="w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 flex items-center justify-center"><Plus className="w-3.5 h-3.5" /></button>
        </div>
        <div className="h-1.5 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-gradient-to-r from-fuchsia-400 to-amber-300" style={{ width: `${usedPct}%` }} /></div>
        <div className="text-[10px] text-white/60 leading-snug">
          выдано {nf(n.granted)} · собирают {nf(n.collecting)} · собрали {nf(n.assembled)} · <b className={n.left > 0 ? 'text-emerald-300' : 'text-red-300'}>осталось {nf(n.left)}</b>
        </div>
      </div>
    </div>
  );
}

function AddNft({ g, h, run, busy }) {
  const [name, setName] = useState('');
  const [media, setMedia] = useState(null);            // {media_url, media_type, image_url}
  const [qty, setQty] = useState(100);
  const [kind, setKind] = useState('tradable');
  const [up, setUp] = useState(false);
  const upload = async (file) => {
    if (!file) return;
    setUp(true);
    try {
      if (file.size > 30 * 1024 * 1024) { toast.error('Файл больше 30 МБ'); return; }
      const fd = new FormData(); fd.append('file', file);
      if ((file.type || '').startsWith('video/')) {          // the frame for the 9 pieces: taken here (no ffmpeg needed)
        const poster = await videoPoster(file);
        if (poster) fd.append('poster', poster, 'poster.png');
      }
      const r = await axios.post(`${API}/game-nfts/upload`, fd, { headers: { ...h.headers, 'Content-Type': 'multipart/form-data' } });
      setMedia(r.data);
    } catch (e) {
      toast.error(e?.response?.status === 413 ? 'Файл слишком большой для сервера (nginx client_max_body_size)' : e?.response?.data?.detail || 'Не удалось загрузить файл');
    } finally { setUp(false); }
  };
  const add = async () => {
    const ok = await run(() => axios.post(`${API}/game-nfts/${g.game}/nfts`, { name, ...media, supply_total: Number(qty), kind }, h), `NFT «${name}» добавлен`);
    if (ok) { setName(''); setMedia(null); setQty(100); }
  };
  return (
    <div className="rounded-xl border border-dashed border-fuchsia-400/40 bg-fuchsia-500/[0.04] p-3 space-y-2" data-testid="gn-add">
      <div className="text-sm font-bold text-fuchsia-100">+ Новый NFT игры</div>
      <div className="flex gap-2">
        <label className="relative w-16 h-16 shrink-0 rounded-lg border border-white/15 bg-black/30 flex items-center justify-center cursor-pointer overflow-hidden" title="Картинка, GIF или видео (mp4 / webm), лучше квадратные; кадр режется на 9 частей">
          {media ? <NftMedia src={media.media_url} type={media.media_type} poster={media.image_url} className="w-full h-full object-cover" />
            : <ImagePlus className={`w-5 h-5 text-white/50 ${up ? 'animate-pulse' : ''}`} />}
          {media && media.media_type !== 'image' && <span className="absolute left-0.5 top-0.5 px-1 rounded bg-black/70 text-[8px] font-bold text-white">{media.media_type === 'video' ? 'ВИДЕО' : 'GIF'}</span>}
          <input type="file" accept="image/*,video/mp4,video/webm,video/quicktime,.gif,.webp,.mp4,.webm,.mov" className="hidden" onChange={(e) => upload(e.target.files?.[0])} data-testid="gn-add-file" />
        </label>
        <div className="flex-1 space-y-1.5">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Название (переведётся на 9 языков)" className="h-8 bg-panel border-grid-border" data-testid="gn-add-name" />
          <div className="flex gap-1.5">
            <Input type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} className="h-8 w-24 bg-panel border-grid-border" title="Сколько можно получить" data-testid="gn-add-qty" />
            <select value={kind} onChange={(e) => setKind(e.target.value)} className="h-8 flex-1 bg-panel border border-grid-border rounded-md px-2 text-xs text-white">
              <option value="tradable">передаваемый</option><option value="sbt">SBT (привязан к аккаунту)</option>
            </select>
          </div>
        </div>
      </div>
      <div className="text-[10px] text-white/50">Картинка, GIF или видео (mp4 / webm, до 30 МБ), лучше квадратные. Для частей 3×3 берётся кадр (у видео — кадр на 0,5 с). Число — сколько игроков смогут собрать этот NFT.</div>
      <Button size="sm" disabled={busy || up || !name.trim() || !media || !(Number(qty) > 0)} onClick={add} className="btn-cyber w-full" data-testid="gn-add-btn">Добавить NFT в игру</Button>
    </div>
  );
}
