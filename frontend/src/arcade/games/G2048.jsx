/** «2048» — swipe / arrows. Merges add their value to the score. Game over when no move is left.
 *  «hard»: a new tile is 4 in 30 % of cases (normal 10 %, easy 5 %). */
import { useCallback, useEffect, useRef, useState } from 'react';
import { mulberry32, onKeys, onSwipe, sound } from '@/arcade/core';

const N = 4;
const P4 = { easy: 0.05, normal: 0.1, hard: 0.3 };
const COLORS = {
  2: ['#1e293b', '#e2e8f0'], 4: ['#334155', '#f1f5f9'], 8: ['#f59e0b', '#fff'], 16: ['#f97316', '#fff'], 32: ['#ef4444', '#fff'],
  64: ['#dc2626', '#fff'], 128: ['#06b6d4', '#fff'], 256: ['#0ea5e9', '#fff'], 512: ['#6366f1', '#fff'], 1024: ['#a855f7', '#fff'],
  2048: ['#facc15', '#0b1020'], 4096: ['#22c55e', '#fff'],
};

function slide(row) {
  const v = row.filter((x) => x);
  let gain = 0;
  const out = [];
  for (let i = 0; i < v.length; i += 1) {
    if (v[i] === v[i + 1]) { out.push(v[i] * 2); gain += v[i] * 2; i += 1; } else out.push(v[i]);
  }
  while (out.length < N) out.push(0);
  return { row: out, gain };
}

function move(grid, dir) {
  const g = grid.map((r) => [...r]);
  let gain = 0, moved = false;
  for (let i = 0; i < N; i += 1) {
    let line = [];
    for (let j = 0; j < N; j += 1) {
      const [r, c] = dir === 'left' ? [i, j] : dir === 'right' ? [i, N - 1 - j] : dir === 'up' ? [j, i] : [N - 1 - j, i];
      line.push(g[r][c]);
    }
    const s = slide(line);
    gain += s.gain;
    for (let j = 0; j < N; j += 1) {
      const [r, c] = dir === 'left' ? [i, j] : dir === 'right' ? [i, N - 1 - j] : dir === 'up' ? [j, i] : [N - 1 - j, i];
      if (g[r][c] !== s.row[j]) moved = true;
      g[r][c] = s.row[j];
    }
    line = null;
  }
  return { grid: g, gain, moved };
}

const canMove = (g) => ['left', 'right', 'up', 'down'].some((d) => move(g, d).moved);

export default function G2048({ seed, difficulty, onHud, onEnd, pausedRef }) {
  const rnd = useRef(mulberry32(seed || 11)).current;
  const add = useCallback((g) => {
    const empty = [];
    g.forEach((r, i) => r.forEach((v, j) => { if (!v) empty.push([i, j]); }));
    if (!empty.length) return g;
    const [i, j] = empty[Math.floor(rnd() * empty.length)];
    const n = g.map((r) => [...r]);
    n[i][j] = rnd() < (P4[difficulty] ?? 0.1) ? 4 : 2;
    return n;
  }, [rnd, difficulty]);
  const [grid, setGrid] = useState(() => { let g = Array.from({ length: N }, () => Array(N).fill(0)); g = add(g); return add(g); });
  const [score, setScore] = useState(0);
  const [pop, setPop] = useState(null);
  const over = useRef(false);
  const wrap = useRef(null);
  const state = useRef({ grid, score });
  state.current = { grid, score };

  useEffect(() => { onHud && onHud({ score, stats: { best: Math.max(...grid.flat()) } }); }, [score]); // eslint-disable-line react-hooks/exhaustive-deps

  const go = useCallback((dir) => {
    sound.unlock();
    if (over.current || pausedRef?.current) return;
    const { grid: g, score: s } = state.current;
    const m = move(g, dir);
    if (!m.moved) return;
    const ng = add(m.grid);
    const ns = s + m.gain;
    setGrid(ng); setScore(ns);
    if (m.gain) { setPop(Date.now()); sound.play('drop'); } else sound.play('tick');
    if (!canMove(ng)) {
      over.current = true;
      sound.play('lose');
      setTimeout(() => onEnd({ score: ns, stats: { best: Math.max(...ng.flat()) } }), 700);
    }
  }, [add, onEnd]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const a = onSwipe(wrap.current, go, 20);
    const b = onKeys(go);
    return () => { a(); b(); };
  }, [go]);

  return (
    <div ref={wrap} className="w-full h-full flex items-center justify-center p-4 touch-none select-none bg-gradient-to-b from-[#1a1206] to-[#0b1020]" data-testid="arcade-g2048">
      <div className="w-full max-w-[360px] aspect-square rounded-2xl bg-[#2b2113] p-2 grid grid-cols-4 grid-rows-4 gap-2 shadow-2xl shadow-amber-500/10">
        {grid.flat().map((v, i) => {
          const [bg, fg] = COLORS[v] || ['#16a34a', '#fff'];
          return (
            <div key={`${i}-${v}-${v ? pop : 0}`} className={`rounded-xl flex items-center justify-center font-black transition-all ${v ? 'animate-[arcpop_.18s_ease-out]' : ''}`}
              style={{ background: v ? bg : '#3b2f1d', color: fg, fontSize: v >= 1024 ? 20 : v >= 128 ? 24 : 28, boxShadow: v >= 128 ? `0 0 18px ${bg}88` : undefined }}>
              {v || ''}
            </div>
          );
        })}
      </div>
      <style>{'@keyframes arcpop{0%{transform:scale(.8)}60%{transform:scale(1.08)}100%{transform:scale(1)}}'}</style>
    </div>
  );
}
