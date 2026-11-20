/** «Крестики-нолики» — no score limit: rounds go on until you lose 3 times (3 lives) or the time runs out
 *  (120 s, the pause stops the clock); the first move alternates (round 1: the player). The player is ✕.
 *  Win 100 + 25 per win in a row (up to +100), draw 30, loss 0 and −1 life (the server replays every round).
 *  AI: easy — mostly random, normal — wins / blocks, hard — minimax (only a draw is possible). */
import { useEffect, useRef, useState } from 'react';
import { mulberry32, sound, TICTAC_SECONDS, TICTAC_LIVES, tictacPoints } from '@/arcade/core';

const LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
const winner = (b) => { for (const [a, c, d] of LINES) if (b[a] && b[a] === b[c] && b[a] === b[d]) return { w: b[a], line: [a, c, d] }; return b.every(Boolean) ? { w: 'draw' } : null; };

function minimax(b, me) {
  const w = winner(b);
  if (w) return { s: w.w === 'ai' ? 10 : w.w === 'p' ? -10 : 0 };
  let best = { s: me === 'ai' ? -99 : 99, m: -1 };
  for (let i = 0; i < 9; i += 1) {
    if (b[i]) continue;
    b[i] = me;
    const r = minimax(b, me === 'ai' ? 'p' : 'ai');
    b[i] = '';
    const s = r.s * 0.9;
    if (me === 'ai' ? s > best.s : s < best.s) best = { s, m: i };
  }
  return best;
}

function aiMove(b, diff, rnd) {
  const free = b.map((v, i) => (v ? -1 : i)).filter((i) => i >= 0);
  const pickRandom = () => free[Math.floor(rnd() * free.length)];
  const finish = (who) => { for (const i of free) { b[i] = who; const w = winner(b); b[i] = ''; if (w && w.w === who) return i; } return -1; };
  if (diff === 'hard') return minimax([...b], 'ai').m;
  if (diff === 'easy' && rnd() < 0.7) return pickRandom();
  const win = finish('ai'); if (win >= 0) return win;
  const block = finish('p'); if (block >= 0) return block;
  if (!b[4] && rnd() < 0.7) return 4;
  return pickRandom();
}

export default function TicTac({ seed, difficulty, onHud, onEnd, t, pausedRef }) {
  const rnd = useRef(mulberry32(seed || 9)).current;
  const [round, setRound] = useState(0);
  const [board, setBoard] = useState(Array(9).fill(''));
  const [res, setRes] = useState(null);
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(TICTAC_LIVES);
  const [left, setLeft] = useState(TICTAC_SECONDS);
  const rounds = useRef([]);
  const moves = useRef([]);
  const busy = useRef(false);
  const wins = useRef(0);
  const streak = useRef(0);
  const over = useRef(false);
  const t0 = useRef(performance.now());
  const sc = useRef(0);
  sc.current = score;

  const finish = () => {
    if (over.current) return;
    over.current = true;
    // a round cut by the clock is sent too (unfinished → 0 points on the server)
    const all = moves.current.length ? [...rounds.current, { moves: [...moves.current] }] : rounds.current;
    setTimeout(() => onEnd({ score: sc.current, stats: { rounds: all, wins: wins.current } }), 500);
  };

  useEffect(() => {                                        // the clock (stops during the pause)
    let last = performance.now();
    const id = setInterval(() => {
      const now = performance.now();
      if (pausedRef?.current) t0.current += now - last;
      last = now;
      const l = Math.max(0, TICTAC_SECONDS - (now - t0.current) / 1000);
      setLeft(l);
      if (l <= 0) { clearInterval(id); finish(); }
    }, 200);
    return () => clearInterval(id);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // the top bar keeps only score + time (fits a phone); round, lives and the win streak are shown above the board
    onHud && onHud({ score, timeLeft: left, stats: { rounds: rounds.current, wins: wins.current } });
  }, [score, round, lives, Math.ceil(left)]); // eslint-disable-line react-hooks/exhaustive-deps

  const end = (b, w) => {
    rounds.current.push({ moves: [...moves.current] });
    moves.current = [];                                    // the round is closed (an unfinished one is sent separately)
    const r = w.w === 'p' ? 'win' : w.w === 'draw' ? 'draw' : 'loss';
    streak.current = r === 'win' ? streak.current + 1 : 0;
    const pts = tictacPoints(r, streak.current);
    if (r === 'win') wins.current += 1;
    sound.play(r === 'win' ? 'win' : r === 'loss' ? 'lose' : 'ok');
    setScore((s0) => s0 + pts);
    const nl = r === 'loss' ? lives - 1 : lives;
    if (r === 'loss') setLives(nl);
    setRes({ ...w, pts, last: nl <= 0 });
    if (nl <= 0) { sc.current += pts; finish(); }
  };

  const ai = (b) => {
    busy.current = true;
    setTimeout(() => {
      if (over.current) return;
      const m = aiMove(b, difficulty, rnd);
      const nb = [...b]; nb[m] = 'ai';
      moves.current.push(m);
      setBoard(nb);
      busy.current = false;
      const w = winner(nb);
      if (w) end(nb, w);
    }, 380);
  };

  useEffect(() => {                                        // even rounds (2, 4, …): the computer starts
    if (round % 2 === 1 && !res && board.every((v) => !v)) ai(board);
  }, [round]); // eslint-disable-line react-hooks/exhaustive-deps

  const tap = (i) => {
    sound.unlock();
    if (busy.current || res || over.current || board[i] || pausedRef?.current) return;
    sound.play('tick');
    const nb = [...board]; nb[i] = 'p';
    moves.current.push(i);
    setBoard(nb);
    const w = winner(nb);
    if (w) end(nb, w); else ai(nb);
  };

  const next = () => {
    if (over.current) return;
    moves.current = [];
    setBoard(Array(9).fill(''));
    setRes(null);
    setRound((r) => r + 1);
  };

  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-4 p-4 select-none bg-gradient-to-b from-[#1c0b33] to-[#0b1020]" data-testid="arcade-tictac">
      <div className="flex items-center gap-3 text-sm font-bold" data-testid="tictac-status">
        <span className="px-3 py-1 rounded-xl bg-white/5 border border-white/10 text-violet-200">{t('ar_round_one').replace('{a}', round + 1)}</span>
        <span className="flex items-center gap-0.5" aria-label="lives">
          {Array.from({ length: TICTAC_LIVES }).map((_, i) => <span key={i} className={i < lives ? 'text-rose-500' : 'text-white/20'}>♥</span>)}
        </span>
        {streak.current > 1 && <span className="px-2 py-1 rounded-xl bg-fuchsia-600/30 border border-fuchsia-300/50 text-white text-xs">🔥 ×{streak.current}</span>}
      </div>
      <div className="w-full max-w-[320px] aspect-square grid grid-cols-3 grid-rows-3 gap-2">
        {board.map((v, i) => {
          const hot = res?.line?.includes(i);
          return (
            <button type="button" key={i} onClick={() => tap(i)} data-testid="tictac-cell"
              className={`rounded-2xl border text-5xl font-black flex items-center justify-center transition-all ${hot ? 'bg-violet-500/30 border-violet-300' : 'bg-white/5 border-white/15 active:bg-white/15'}`}>
              {v === 'p' && <span className="text-cyan-300 drop-shadow-[0_0_10px_#22d3ee]">✕</span>}
              {v === 'ai' && <span className="text-pink-400 drop-shadow-[0_0_10px_#f472b6]">○</span>}
            </button>
          );
        })}
      </div>
      <div className="h-16 flex flex-col items-center justify-center">
        {res && (
          <>
            <div className={`font-bold ${res.w === 'p' ? 'text-emerald-300' : res.w === 'ai' ? 'text-pink-300' : 'text-white'}`}>
              {t(res.w === 'p' ? 'ar_win' : res.w === 'ai' ? 'ar_loss' : 'ar_draw')}{res.pts ? ` +${res.pts}` : ''}
            </div>
            {!res.last && <button type="button" onClick={next} data-testid="tictac-next" className="mt-1.5 px-6 py-1.5 rounded-xl bg-violet-500 text-white font-bold text-sm">{t('ar_next')}</button>}
          </>
        )}
      </div>
    </div>
  );
}
