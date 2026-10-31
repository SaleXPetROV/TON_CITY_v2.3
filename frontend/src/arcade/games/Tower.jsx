/** «Небоскрёб» — tap to drop the moving floor. The overhang is cut off; a perfect drop (+5) keeps the width.
 *  +10 per floor. The game ends when a floor misses the tower. */
import { useEffect, useRef } from 'react';
import { fitCanvas, loop, sound } from '@/arcade/core';

const DIFF = { easy: { v: 150, acc: 4, perfect: 7 }, normal: { v: 190, acc: 6, perfect: 5 }, hard: { v: 240, acc: 8, perfect: 4 } };
const FH = 26;

export default function Tower({ difficulty, tuning, onHud, onEnd, pausedRef }) {
  const ref = useRef(null);
  const cbs = useRef({ onHud, onEnd });
  cbs.current = { onHud, onEnd };

  useEffect(() => {
    const canvas = ref.current;
    let { ctx, W, H } = fitCanvas(canvas);
    const base = DIFF[difficulty] || DIFF.normal;
    const sp = (tuning?.speed || 100) / 100;
    const D = { ...base, v: base.v * sp, acc: base.acc * sp };
    const w0 = Math.min(220, W * 0.55);
    const st = {
      floors: [{ x: (W - w0) / 2, w: w0, hue: 195 }], cur: null, floorsN: 0, perfect: 0, cam: 0, over: false, t: 0,
      chips: [], flash: 0, lastDrop: 0,
    };
    const newCur = () => {
      const top = st.floors[st.floors.length - 1];
      const fromLeft = st.floors.length % 2 === 0;
      st.cur = { x: fromLeft ? -top.w : W, w: top.w, dir: fromLeft ? 1 : -1, v: D.v + st.floorsN * D.acc, hue: (top.hue + 14) % 360 };
    };
    newCur();
    const score = () => st.floorsN * 10 + st.perfect * 5;
    const hud = () => cbs.current.onHud && cbs.current.onHud({ score: score(), stats: { floors: st.floorsN, perfect: st.perfect } });
    hud();
    const drop = () => {
      sound.unlock();
      if (st.over || !st.cur || pausedRef?.current || st.t - st.lastDrop < 0.5) return;
      st.lastDrop = st.t;
      const top = st.floors[st.floors.length - 1];
      const c = st.cur;
      const l = Math.max(c.x, top.x), r = Math.min(c.x + c.w, top.x + top.w);
      if (r - l <= 2) {
        st.over = true; sound.play('lose'); st.chips.push({ x: c.x, w: c.w, y: st.floors.length, vy: 0, hue: c.hue });
        st.cur = null;
        setTimeout(() => cbs.current.onEnd({ score: score(), stats: { floors: st.floorsN, perfect: st.perfect } }), 900);
        return;
      }
      let nf;
      if (Math.abs(c.x - top.x) <= D.perfect) { nf = { x: top.x, w: top.w, hue: c.hue }; st.perfect += 1; st.flash = 0.35; sound.play('pick'); } else {
        nf = { x: l, w: r - l, hue: c.hue };
        const cut = c.x < top.x ? { x: c.x, w: top.x - c.x } : { x: r, w: c.x + c.w - r };
        st.chips.push({ ...cut, y: st.floors.length, vy: 0, hue: c.hue });
      }
      if (!st.flash || st.flash < 0.34) sound.play('drop');
      st.floors.push(nf);
      st.floorsN += 1;
      hud();
      newCur();
    };
    const down = (e) => { e.preventDefault(); drop(); };
    const key = (e) => { if (e.key === ' ' || e.key === 'Enter') drop(); };
    canvas.addEventListener('pointerdown', down);
    window.addEventListener('keydown', key);
    const onResize = () => { const f = fitCanvas(canvas); ctx = f.ctx; W = f.W; H = f.H; };
    window.addEventListener('resize', onResize);

    const stop = loop((dt0) => {
      const dt = pausedRef?.current ? 0 : dt0;
      st.t += dt;
      st.flash = Math.max(0, st.flash - dt);
      if (st.cur) {
        const c = st.cur;
        c.x += c.dir * c.v * dt;
        if (c.x + c.w > W + 10) { c.dir = -1; } else if (c.x < -10) { c.dir = 1; }
      }
      const baseY = H - 50;
      const want = Math.max(0, st.floors.length * FH - H * 0.55);
      st.cam += (want - st.cam) * Math.min(1, dt * 5);
      st.chips.forEach((ch) => { ch.vy += 900 * dt; ch.dy = (ch.dy || 0) + ch.vy * dt; });
      st.chips = st.chips.filter((ch) => (ch.dy || 0) < H + 200);

      const sky = ctx.createLinearGradient(0, 0, 0, H);
      const k = Math.min(1, st.floorsN / 60);
      sky.addColorStop(0, `hsl(${220 - k * 40}, 60%, ${12 + k * 4}%)`); sky.addColorStop(1, `hsl(${200 - k * 60}, 60%, ${22 - k * 8}%)`);
      ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H);
      for (let i = 0; i < 30; i += 1) { ctx.fillStyle = '#ffffff22'; ctx.fillRect((i * 97) % W, ((i * 53) % H + st.cam * 0.3) % H, 2, 2); }
      const yOf = (i) => baseY - i * FH + st.cam;
      ctx.fillStyle = '#0f172a'; ctx.fillRect(0, yOf(0) + FH, W, H);
      const drawFloor = (f, y, alpha = 1) => {
        ctx.globalAlpha = alpha;
        ctx.fillStyle = `hsl(${f.hue}, 70%, 52%)`; ctx.fillRect(f.x, y, f.w, FH - 2);
        ctx.fillStyle = `hsl(${f.hue}, 80%, 72%)`; ctx.fillRect(f.x, y, f.w, 4);
        ctx.fillStyle = '#0b102099';
        for (let wx = f.x + 6; wx < f.x + f.w - 8; wx += 14) ctx.fillRect(wx, y + 9, 7, 9);
        ctx.globalAlpha = 1;
      };
      st.floors.forEach((f, i) => { const y = yOf(i); if (y > -FH && y < H) drawFloor(f, y); });
      st.chips.forEach((ch) => drawFloor(ch, yOf(ch.y) + (ch.dy || 0), 0.8));
      if (st.cur) drawFloor(st.cur, yOf(st.floors.length));
      if (st.flash > 0) {
        const top = st.floors[st.floors.length - 1];
        ctx.strokeStyle = `rgba(255,255,255,${st.flash * 2.5})`; ctx.lineWidth = 3;
        ctx.strokeRect(top.x - 3, yOf(st.floors.length - 1) - 3, top.w + 6, FH + 4);
        ctx.fillStyle = '#fde047'; ctx.font = 'bold 18px system-ui'; ctx.textAlign = 'center';
        ctx.fillText('PERFECT +5', W / 2, yOf(st.floors.length) - 20);
      }
      return true;
    });
    return () => { stop(); canvas.removeEventListener('pointerdown', down); window.removeEventListener('keydown', key); window.removeEventListener('resize', onResize); };
  }, [difficulty]); // eslint-disable-line react-hooks/exhaustive-deps

  return <canvas ref={ref} className="w-full h-full touch-none select-none block" data-testid="arcade-canvas-tower" />;
}
