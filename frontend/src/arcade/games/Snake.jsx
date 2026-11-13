/** «Змейка» — swipe / arrows / on-screen pad to turn. 🍎 = +10. Faster with every apple.
 *  easy: slow, the snake passes through the walls · normal: walls kill · hard: fast, walls kill + rocks on the field. */
import { useEffect, useRef } from 'react';
import { fitCanvas, loop, mulberry32, onKeys, onSwipe, roundRect, sound } from '@/arcade/core';

const DIFF = { easy: { tick: 0.19, min: 0.1, wrap: true, rocks: 0 }, normal: { tick: 0.15, min: 0.075, wrap: false, rocks: 0 }, hard: { tick: 0.115, min: 0.06, wrap: false, rocks: 8 } };
const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

export default function Snake({ seed, difficulty, tuning, onHud, onEnd, pausedRef }) {
  const ref = useRef(null);
  const wrap = useRef(null);
  const cbs = useRef({ onHud, onEnd });
  cbs.current = { onHud, onEnd };
  const turnRef = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    let { ctx, W, H } = fitCanvas(canvas);
    const rnd = mulberry32(seed || 3);
    const base = DIFF[difficulty] || DIFF.normal;
    const sp = (tuning?.speed || 100) / 100;
    const D = { ...base, tick: base.tick / sp, min: base.min / sp };
    const COLS = 15;
    const geo = () => { const cell = Math.floor(Math.min(W / COLS, H / 20)); const rows = Math.floor(H / cell); return { cell, rows, ox: (W - cell * COLS) / 2, oy: (H - cell * rows) / 2 }; };
    let g = geo();
    const mid = Math.floor(g.rows / 2);
    const st = { snake: [[4, mid], [3, mid], [2, mid]], dir: 'right', queue: [], food: null, food_n: 0, acc: 0, tick: D.tick, over: false, t: 0, pop: 0 };
    st.rocks = [];
    for (let i = 0; i < 400 && st.rocks.length < D.rocks; i += 1) {
      const r = [Math.floor(rnd() * COLS), Math.floor(rnd() * g.rows)];
      if (Math.abs(r[1] - mid) <= 1 || st.rocks.some((q) => Math.abs(q[0] - r[0]) + Math.abs(q[1] - r[1]) < 3)) continue;
      st.rocks.push(r);
    }
    const isRock = (x, y) => st.rocks.some((q) => q[0] === x && q[1] === y);
    const place = () => {
      for (let i = 0; i < 400; i += 1) {
        const f = [Math.floor(rnd() * COLS), Math.floor(rnd() * g.rows)];
        if (!st.snake.some((s) => s[0] === f[0] && s[1] === f[1]) && !isRock(f[0], f[1])) { st.food = f; return; }
      }
    };
    place();
    const hud = () => cbs.current.onHud && cbs.current.onHud({ score: st.food_n * 10, stats: { food: st.food_n } });
    hud();
    const opp = { up: 'down', down: 'up', left: 'right', right: 'left' };
    const turn = (d) => {
      sound.unlock();
      if (pausedRef?.current) return;
      const last = st.queue.length ? st.queue[st.queue.length - 1] : st.dir;
      if (d !== last && d !== opp[last] && st.queue.length < 3) st.queue.push(d);
    };
    turnRef.current = turn;
    const offSwipe = onSwipe(wrap.current, turn, 18);
    const offKeys = onKeys(turn);
    const onResize = () => { const f = fitCanvas(canvas); ctx = f.ctx; W = f.W; H = f.H; g = geo(); };
    window.addEventListener('resize', onResize);

    const stop = loop((dt0) => {
      const dt = pausedRef?.current ? 0 : dt0;
      st.t += dt;
      st.pop = Math.max(0, st.pop - dt);
      if (!st.over) {
        st.acc += dt;
        while (st.acc >= st.tick && !st.over) {
          st.acc -= st.tick;
          if (st.queue.length) st.dir = st.queue.shift();
          const [dx, dy] = DIRS[st.dir];
          let head = [st.snake[0][0] + dx, st.snake[0][1] + dy];
          if (D.wrap) head = [(head[0] + COLS) % COLS, (head[1] + g.rows) % g.rows];
          const eat = st.food && head[0] === st.food[0] && head[1] === st.food[1];
          const body = eat ? st.snake : st.snake.slice(0, -1);
          if (head[0] < 0 || head[1] < 0 || head[0] >= COLS || head[1] >= g.rows || body.some((s) => s[0] === head[0] && s[1] === head[1]) || isRock(head[0], head[1])) {
            st.over = true;
            sound.play('lose');
            if (navigator.vibrate) try { navigator.vibrate(80); } catch (_) { /* ignore */ }
            setTimeout(() => cbs.current.onEnd({ score: st.food_n * 10, stats: { food: st.food_n } }), 700);
            break;
          }
          st.snake = [head, ...body];
          if (eat) { sound.play('coin'); st.food_n += 1; st.tick = Math.max(D.min, st.tick - 0.003); st.pop = 0.25; place(); hud(); }
        }
      }
      // draw
      ctx.fillStyle = '#04150f'; ctx.fillRect(0, 0, W, H);
      const { cell, rows, ox, oy } = g;
      for (let y = 0; y < rows; y += 1) for (let x = 0; x < COLS; x += 1) {
        ctx.fillStyle = (x + y) % 2 ? '#0a2a1e' : '#0c3324';
        ctx.fillRect(ox + x * cell, oy + y * cell, cell, cell);
      }
      ctx.strokeStyle = D.wrap ? '#10b98133' : '#f43f5e88'; ctx.lineWidth = D.wrap ? 1 : 3;
      if (D.wrap) ctx.setLineDash([6, 6]);
      ctx.strokeRect(ox, oy, cell * COLS, cell * rows); ctx.setLineDash([]);
      st.rocks.forEach(([x, y]) => {
        const gr = ctx.createLinearGradient(0, oy + y * cell, 0, oy + (y + 1) * cell);
        gr.addColorStop(0, '#6b7280'); gr.addColorStop(1, '#374151');
        ctx.fillStyle = gr; roundRect(ctx, ox + x * cell + 1.5, oy + y * cell + 1.5, cell - 3, cell - 3, cell * 0.25); ctx.fill();
        ctx.fillStyle = '#9ca3af55'; ctx.fillRect(ox + x * cell + cell * 0.25, oy + y * cell + cell * 0.25, cell * 0.2, cell * 0.15);
      });
      if (st.food) {
        const s = 1 + Math.sin(st.t * 6) * 0.08;
        ctx.font = `${Math.floor(cell * 0.9 * s)}px system-ui`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText('🍎', ox + st.food[0] * cell + cell / 2, oy + st.food[1] * cell + cell / 2 + 1);
      }
      const n = st.snake.length;
      st.snake.forEach((p, i) => {
        const k = 1 - i / Math.max(8, n * 1.4);
        ctx.fillStyle = st.over ? '#ef4444' : `hsl(${150 - i * 1.5}, 80%, ${38 + k * 22}%)`;
        const pad = i === 0 ? 1 : 2 + (st.pop > 0 && i === 0 ? -1 : 0);
        roundRect(ctx, ox + p[0] * cell + pad, oy + p[1] * cell + pad, cell - pad * 2, cell - pad * 2, cell * 0.3); ctx.fill();
      });
      const h = st.snake[0], [dx, dy] = DIRS[st.dir];
      ctx.fillStyle = '#04150f';
      const cx = ox + h[0] * cell + cell / 2, cy = oy + h[1] * cell + cell / 2;
      [[-1, 1], [1, 1]].forEach(([a]) => {
        ctx.beginPath(); ctx.arc(cx + dx * cell * 0.18 + dy * a * cell * 0.2, cy + dy * cell * 0.18 - dx * a * cell * 0.2, cell * 0.09, 0, Math.PI * 2); ctx.fill();
      });
      return true;
    });
    return () => { stop(); offSwipe(); offKeys(); window.removeEventListener('resize', onResize); };
  }, [seed, difficulty]); // eslint-disable-line react-hooks/exhaustive-deps

  const pad = (d, label) => (
    <button type="button" onPointerDown={(e) => { e.stopPropagation(); turnRef.current && turnRef.current(d); }}
      className="w-14 h-11 rounded-xl bg-white/10 border border-white/15 text-white text-lg active:bg-emerald-500/40" aria-label={d}>{label}</button>
  );
  return (
    <div ref={wrap} className="w-full h-full flex flex-col touch-none select-none" data-testid="arcade-canvas-snake">
      <canvas ref={ref} className="w-full flex-1 min-h-0 block" />
      <div className="flex flex-col items-center gap-1.5 py-2 bg-[#04150f]">
        {pad('up', '▲')}
        <div className="flex gap-1.5">{pad('left', '◀')}{pad('down', '▼')}{pad('right', '▶')}</div>
      </div>
    </div>
  );
}
