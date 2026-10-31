/** «Память» — no score limit: find pairs against the clock. A cleared board is dealt again (a new shuffle), so the
 *  only limit is TIME (easy 90 s · normal 75 s · hard 60 s; pause stops the clock).
 *  Score (the server checks the same formula): pair +50 · combo (pairs in a row without a miss) +10 per step, up to +50 ·
 *  cleared board +100. easy: 6 pairs, each new board is shown for 2 s · normal: 8 pairs, shown for 1 s · hard: 10 pairs. */
import { useEffect, useMemo, useRef, useState } from 'react';
import { MEMORY_PAIRS, MEMORY_SECONDS, memoryPoints, mulberry32, sound } from '@/arcade/core';

const ICONS = ['🏦', '⚡', '💎', '🚀', '🧬', '🔮', '🎲', '🔑', '📜', '🛡️', '🏭', '🌴'];

function makeDeck(seed, board, total) {
  const r = mulberry32(((seed || 5) + board * 7919) >>> 0);
  const icons = [...ICONS].sort(() => r() - 0.5).slice(0, total);
  const d = [...icons, ...icons].map((ic, i) => ({ id: `${board}-${i}`, ic }));
  for (let i = d.length - 1; i > 0; i -= 1) { const j = Math.floor(r() * (i + 1)); [d[i], d[j]] = [d[j], d[i]]; }
  return d;
}

export default function Memory({ seed, difficulty, onHud, onEnd, pausedRef }) {
  const total = MEMORY_PAIRS[difficulty] || 8;
  const seconds = MEMORY_SECONDS[difficulty] || 75;
  const peekMs = { easy: 2000, normal: 1000, hard: 0 }[difficulty] ?? 1000;
  const [board, setBoard] = useState(0);
  const deck = useMemo(() => makeDeck(seed, board, total), [seed, board, total]);
  const [peek, setPeek] = useState(peekMs > 0);
  useEffect(() => {                                     // every new board is shown for a moment (easy / normal)
    if (!peekMs) return undefined;
    setPeek(true);
    const id = setTimeout(() => setPeek(false), peekMs);
    return () => clearTimeout(id);
  }, [board, peekMs]);
  const [open, setOpen] = useState([]);
  const [done, setDone] = useState(() => new Set());
  const st = useRef({ pairs: 0, moves: 0, boards: 0, combo: 0, bonus: 0, score: 0 });
  const [, force] = useState(0);
  const [left, setLeft] = useState(seconds);
  const lock = useRef(false);
  const finished = useRef(false);
  const t0 = useRef(performance.now());

  const stats = () => ({ pairs: st.current.pairs, moves: st.current.moves, boards: st.current.boards, combo_bonus: st.current.bonus });
  const hud = () => onHud && onHud({ score: st.current.score, timeLeft: left, combo: st.current.combo, stats: stats() });

  useEffect(() => {                                     // the clock (stops during the pause)
    let last = performance.now();
    const id = setInterval(() => {
      const now = performance.now();
      if (pausedRef?.current) t0.current += now - last;
      last = now;
      const l = Math.max(0, seconds - (now - t0.current) / 1000);
      setLeft(l);
      if (l <= 0 && !finished.current) {
        finished.current = true;
        clearInterval(id);
        sound.play('win');
        setTimeout(() => onEnd({ score: st.current.score, stats: stats() }), 300);
      }
    }, 200);
    return () => clearInterval(id);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { hud(); }, [Math.ceil(left), done]); // eslint-disable-line react-hooks/exhaustive-deps

  const flip = (c) => {
    sound.unlock();
    if (peek || lock.current || finished.current || pausedRef?.current || open.includes(c.id) || done.has(c.id)) return;
    sound.play('tick');
    const next = [...open, c.id];
    setOpen(next);
    if (next.length < 2) return;
    st.current.moves += 1;
    const [a, b] = next.map((id) => deck.find((x) => x.id === id));
    if (a.ic === b.ic) {
      const s = st.current;
      s.pairs += 1;
      s.combo += 1;
      const extra = Math.min(50, 10 * (s.combo - 1));
      s.bonus += extra;
      const nd = new Set(done); nd.add(a.id); nd.add(b.id);
      setOpen([]); sound.play('ok');
      if (nd.size === deck.length) {                    // board cleared → +100 and a new board
        s.boards += 1;
        sound.play('coin');
        s.score = memoryPoints(s.pairs, s.boards, s.bonus);
        lock.current = true;
        setDone(nd);
        setTimeout(() => { setDone(new Set()); setBoard((x) => x + 1); lock.current = false; force((x) => x + 1); }, 450);
      } else {
        s.score = memoryPoints(s.pairs, s.boards, s.bonus);
        setDone(nd);
      }
    } else {
      st.current.combo = 0;
      lock.current = true;
      sound.play('bad');
      setTimeout(() => { setOpen([]); lock.current = false; }, 650);
      force((x) => x + 1);
    }
  };

  const cols = deck.length <= 12 ? 3 : 4;
  return (
    <div className="w-full h-full flex items-center justify-center p-3 select-none bg-gradient-to-b from-[#2a0a1f] to-[#0b1020]" data-testid="arcade-memory">
      <div className="w-full max-w-[380px] grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
        {deck.map((c) => {
          const up = peek || open.includes(c.id) || done.has(c.id);
          return (
            <button type="button" key={c.id} onClick={() => flip(c)} data-testid="memory-card"
              className="relative aspect-[3/4] [perspective:600px]" aria-label="card">
              <div className={`absolute inset-0 transition-transform duration-300 [transform-style:preserve-3d] ${up ? '[transform:rotateY(180deg)]' : ''}`}>
                <div className="absolute inset-0 rounded-xl border border-pink-400/30 bg-gradient-to-br from-pink-600 to-fuchsia-800 flex items-center justify-center [backface-visibility:hidden] shadow-lg">
                  <span className="text-white/40 text-2xl font-black">G</span>
                </div>
                <div className={`absolute inset-0 rounded-xl border flex items-center justify-center text-3xl sm:text-4xl [backface-visibility:hidden] [transform:rotateY(180deg)] ${done.has(c.id) ? 'bg-emerald-500/20 border-emerald-400/60' : 'bg-white/10 border-white/25'}`}>
                  {c.ic}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
