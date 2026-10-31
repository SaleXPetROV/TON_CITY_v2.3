/** «Ночная трасса» — 3-lane racer. Tap left / right half (or swipe, or arrows) to change lanes.
 *  Points: distance (speed / 20 per second) + coins (+25). 3 lives, the speed keeps growing. */
import { useEffect, useRef } from 'react';
import { LIVES, fitCanvas, loop, mulberry32, onKeys, roundRect, sound } from '@/arcade/core';

const DIFF = { easy: { v0: 380, acc: 6, gap: 1.25 }, normal: { v0: 440, acc: 9, gap: 1 }, hard: { v0: 520, acc: 12, gap: 0.82 } };
const VMAX = 1000;
const CAR_COLORS = ['#f43f5e', '#f59e0b', '#22c55e', '#a855f7', '#e2e8f0', '#3b82f6'];

function drawCar(ctx, x, y, w, h, color, mine) {
  ctx.save();
  ctx.translate(x, y);
  ctx.shadowColor = color; ctx.shadowBlur = mine ? 18 : 8;
  ctx.fillStyle = color;
  roundRect(ctx, -w / 2, -h / 2, w, h, w * 0.28); ctx.fill();
  ctx.shadowBlur = 0;
  ctx.fillStyle = '#0b1020cc';
  roundRect(ctx, -w * 0.36, -h * 0.28, w * 0.72, h * 0.22, 4); ctx.fill();
  roundRect(ctx, -w * 0.34, h * 0.12, w * 0.68, h * 0.16, 4); ctx.fill();
  ctx.fillStyle = mine ? '#fef9c3' : '#fecaca';
  const ly = mine ? -h / 2 + 3 : h / 2 - 6;
  ctx.fillRect(-w * 0.38, ly, w * 0.18, 3); ctx.fillRect(w * 0.2, ly, w * 0.18, 3);
  ctx.restore();
}

export default function Racer({ seed, difficulty, tuning, onHud, onEnd, onDeath, pausedRef }) {
  const ref = useRef(null);
  const cbs = useRef({ onHud, onEnd, onDeath });
  cbs.current = { onHud, onEnd, onDeath };

  useEffect(() => {
    const canvas = ref.current;
    let { ctx, W, H } = fitCanvas(canvas);
    const rnd = mulberry32(seed || 7);
    const base = DIFF[difficulty] || DIFF.normal;
    const sp = (tuning?.speed || 100) / 100;
    const D = { ...base, v0: base.v0 * sp, acc: base.acc * sp };
    const maxLives = tuning?.lives || LIVES.racer[difficulty] || 3;
    const st = { t: 0, v: D.v0, dist: 0, score: 0, coins: 0, lives: maxLives, inv: 0, over: false, lane: 1, x: 0, objs: [], spawn: 0.8, road: 0, parts: [] };
    const road = () => { const rw = Math.min(W * 0.92, 420); return { x0: (W - rw) / 2, rw, lw: rw / 3 }; };
    const laneX = (l) => { const r = road(); return r.x0 + r.lw * (l + 0.5); };
    st.x = laneX(1);
        const hud = () => cbs.current.onHud && cbs.current.onHud({ score: Math.floor(st.score), lives: st.lives, maxLives, stats: { coins: st.coins } });
    hud();
    const go = (d) => { sound.unlock(); if (st.over || pausedRef?.current || st.waiting) return; if (d === 'left' || d === 'right') sound.play('tick'); st.lane = Math.max(0, Math.min(2, st.lane + (d === 'left' ? -1 : d === 'right' ? 1 : 0))); };
    let sx = null;
    const down = (e) => { sx = { x: e.clientX, y: e.clientY }; };
    const up = (e) => {
      if (!sx) return;
      const dx = e.clientX - sx.x;
      if (Math.abs(dx) > 24) go(dx > 0 ? 'right' : 'left');
      else { const r = canvas.getBoundingClientRect(); go(e.clientX - r.left < r.width / 2 ? 'left' : 'right'); }
      sx = null;
    };
    canvas.addEventListener('pointerdown', down);
    canvas.addEventListener('pointerup', up);
    const offKeys = onKeys(go);
    const onResize = () => { const f = fitCanvas(canvas); ctx = f.ctx; W = f.W; H = f.H; };
    window.addEventListener('resize', onResize);

    const stop = loop((dt0) => {
      const dt = (pausedRef?.current || st.waiting) ? 0 : dt0;
      st.t += dt;
      const R = road();
      const carW = Math.min(46, R.lw * 0.62), carH = carW * 1.8;
      const py = H - carH - 26;
      if (!st.over) {
        st.v = Math.min(VMAX, st.v + D.acc * dt * 10);
        st.dist += st.v * dt;
        st.score += (st.v / 20) * dt;
        st.inv = Math.max(0, st.inv - dt);
        st.spawn -= dt;
        if (st.spawn <= 0) {
          const lane = Math.floor(rnd() * 3);
          if (rnd() < 0.78) st.objs.push({ kind: 'car', lane, y: -carH, c: CAR_COLORS[Math.floor(rnd() * CAR_COLORS.length)], sp: 0.35 + rnd() * 0.25 });
          else st.objs.push({ kind: 'coin', lane, y: -30 });
          if (rnd() < 0.25 + st.t / 300) {                   // a second object in another lane (never all three blocked)
            const l2 = (lane + 1 + Math.floor(rnd() * 2)) % 3;
            st.objs.push({ kind: rnd() < 0.5 ? 'coin' : 'car', lane: l2, y: -carH - 70, c: CAR_COLORS[Math.floor(rnd() * 6)], sp: 0.4 });
          }
          st.spawn = Math.max(0.42, (1.05 - st.t / 160)) * D.gap * (420 / Math.max(420, st.v * 0.7));
        }
        st.x += (laneX(st.lane) - st.x) * Math.min(1, dt * 16);
      }
      st.road = (st.road + st.v * dt) % 80;
      st.objs.forEach((o) => { o.y += st.v * dt * (o.kind === 'car' ? (1 - o.sp) : 1); });
      if (!st.over) {
        st.objs.forEach((o) => {
          if (o.dead) return;
          const ox = laneX(o.lane);
          if (Math.abs(ox - st.x) < carW * 0.8) {
            if (o.kind === 'coin' && Math.abs(o.y - (py + carH / 2)) < carH * 0.6) {
              o.dead = true; st.coins += 1; st.score += 25; hud(); sound.play('coin');
              for (let i = 0; i < 8; i += 1) st.parts.push({ x: ox, y: o.y, vx: (rnd() - 0.5) * 200, vy: (rnd() - 0.5) * 200, life: 0.5, c: '#fde047' });
            } else if (o.kind === 'car' && st.inv <= 0 && Math.abs(o.y - (py + carH / 2)) < carH * 0.9) {
              o.dead = true; st.lives -= 1; st.inv = 1.5; st.v = Math.max(D.v0, st.v * 0.7);
              for (let i = 0; i < 20; i += 1) st.parts.push({ x: st.x, y: py, vx: (rnd() - 0.5) * 300, vy: (rnd() - 0.5) * 300, life: 0.7, c: '#fb7185' });
              if (navigator.vibrate) try { navigator.vibrate(60); } catch (_) { /* ignore */ }
              sound.play('hit');
              hud();
              if (st.lives <= 0) {
                st.over = true;
                const end = () => cbs.current.onEnd({ score: Math.floor(st.score), stats: { coins: st.coins, dist: Math.floor(st.dist) } });
                if (cbs.current.onDeath && !st.revived) {
                  setTimeout(() => {
                    st.waiting = true;
                    cbs.current.onDeath({
                      revive: () => { st.revived = true; st.waiting = false; st.over = false; st.lives = 1; st.inv = 2.5; st.objs = []; st.v = Math.max(D.v0, st.v * 0.8); hud(); },
                      decline: () => { st.waiting = false; end(); },
                    });
                  }, 700);
                } else setTimeout(end, 700);
              }
            }
          }
        });
        if (Math.floor(st.t * 4) !== Math.floor((st.t - dt) * 4)) hud();
      }
      st.objs = st.objs.filter((o) => !o.dead && o.y < H + 100);
      st.parts.forEach((p) => { p.x += p.vx * dt; p.y += p.vy * dt; p.life -= dt; });
      st.parts = st.parts.filter((p) => p.life > 0);

      // draw
      const bg = ctx.createLinearGradient(0, 0, 0, H);
      bg.addColorStop(0, '#12002a'); bg.addColorStop(1, '#1e0b3a');
      ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
      for (let i = 0; i < 2; i += 1) {                        // roadside lights
        const x = i === 0 ? R.x0 - 14 : R.x0 + R.rw + 14;
        for (let y = -80 + (st.road * 2) % 160; y < H; y += 160) {
          ctx.fillStyle = '#f0abfc'; ctx.shadowColor = '#e879f9'; ctx.shadowBlur = 14;
          ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
        }
      }
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#1a1530'; ctx.fillRect(R.x0, 0, R.rw, H);
      ctx.strokeStyle = '#e879f9'; ctx.lineWidth = 3; ctx.shadowColor = '#e879f9'; ctx.shadowBlur = 12;
      ctx.beginPath(); ctx.moveTo(R.x0, 0); ctx.lineTo(R.x0, H); ctx.moveTo(R.x0 + R.rw, 0); ctx.lineTo(R.x0 + R.rw, H); ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = '#ffffff55'; ctx.lineWidth = 3; ctx.setLineDash([36, 44]); ctx.lineDashOffset = -st.road;
      for (let l = 1; l < 3; l += 1) { ctx.beginPath(); ctx.moveTo(R.x0 + R.lw * l, 0); ctx.lineTo(R.x0 + R.lw * l, H); ctx.stroke(); }
      ctx.setLineDash([]);
      st.objs.forEach((o) => {
        const ox = laneX(o.lane);
        if (o.kind === 'coin') {
          const sc = Math.abs(Math.sin(st.t * 5));
          ctx.fillStyle = '#facc15'; ctx.shadowColor = '#facc15'; ctx.shadowBlur = 14;
          ctx.beginPath(); ctx.ellipse(ox, o.y, 11 * (0.35 + 0.65 * sc), 11, 0, 0, Math.PI * 2); ctx.fill();
          ctx.shadowBlur = 0;
        } else drawCar(ctx, ox, o.y + carH / 2, carW, carH, o.c, false);
      });
      if (!st.over && (st.inv <= 0 || Math.floor(st.t * 12) % 2 === 0)) drawCar(ctx, st.x, py + carH / 2, carW, carH, '#22d3ee', true);
      st.parts.forEach((p) => { ctx.globalAlpha = Math.max(0, p.life * 1.5); ctx.fillStyle = p.c; ctx.fillRect(p.x - 2, p.y - 2, 4, 4); });
      ctx.globalAlpha = 1;
      ctx.fillStyle = '#ffffffaa'; ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'right';
      ctx.fillText(`${Math.round(st.v / 4)} km/h`, W - 10, H - 10);
      return true;
    });
    return () => { stop(); offKeys(); canvas.removeEventListener('pointerdown', down); canvas.removeEventListener('pointerup', up); window.removeEventListener('resize', onResize); };
  }, [seed, difficulty]); // eslint-disable-line react-hooks/exhaustive-deps

  return <canvas ref={ref} className="w-full h-full touch-none select-none block" data-testid="arcade-canvas-racer" />;
}
