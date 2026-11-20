/** «Уличный баскетбол» — swipe up from the ball to throw it. 45 s. A clean shot 3 points (+1 for clean shots
 *  in a row), off the rim 2. The hoop moves on «normal» (after 15 s) and on «hard». */
import { useEffect, useRef } from 'react';
import { fitCanvas, loop, sound } from '@/arcade/core';

export const BASKET_SECONDS = 45;
const G = 1500;

export default function Basket({ difficulty, tuning, onHud, onEnd, pausedRef }) {
  const ref = useRef(null);
  const cbs = useRef({ onHud, onEnd });
  cbs.current = { onHud, onEnd };

  useEffect(() => {
    const canvas = ref.current;
    let { ctx, W, H } = fitCanvas(canvas);
    const R = 19;
    const st = { t: 0, score: 0, made: 0, shots: 0, streak: 0, over: false, ball: null, msg: null, hx: W / 2, net: 0 };
    const home = () => ({ x: W / 2, y: H - 70, vx: 0, vy: 0, fly: false, rim: false, scored: false, t: 0 });
    st.ball = home();
    const hy = () => Math.max(120, H * 0.3);
    // easy: wide rim, still hoop · normal: hoop starts moving at 15 s · hard: narrow rim, fast moving hoop
    const RIM = { easy: 1.18, normal: 1, hard: 0.84 }[difficulty] || 1;
    const sp = (tuning?.speed || 100) / 100;
    const rimHalf = () => Math.min(46, W * 0.12) * RIM;
    const hud = () => cbs.current.onHud && cbs.current.onHud({ score: st.score, timeLeft: Math.max(0, BASKET_SECONDS - st.t), stats: { made: st.made, shots: st.shots } });
    hud();

    let sw = null;
    const pt = (e) => { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
    const down = (e) => { sound.unlock(); if (st.ball.fly || st.over || pausedRef?.current) return; sw = pt(e); };
    const up = (e) => {
      if (!sw || st.ball.fly || st.over) { sw = null; return; }
      const p = pt(e);
      const dx = p.x - sw.x, dy = p.y - sw.y;
      sw = null;
      if (dy > -30) return;
      const len = Math.hypot(dx, dy);
      const power = Math.max(0.55, Math.min(1.3, len / (H * 0.32)));
      const need = Math.sqrt(2 * G * (st.ball.y - hy() + 70));    // just enough to fly a bit above the rim
      const v = need * power / Math.max(0.35, -dy / len);
      const ang = Math.atan2(dy, dx);
      st.ball.vx = Math.cos(ang) * v * 0.92;
      st.ball.vy = Math.sin(ang) * v;
      st.ball.vy = Math.max(st.ball.vy, -need * 1.35);
      st.ball.fly = true;
      st.shots += 1;
      sound.play('drop');
      hud();
    };
    canvas.addEventListener('pointerdown', down);
    window.addEventListener('pointerup', up);
    const onResize = () => { const f = fitCanvas(canvas); ctx = f.ctx; W = f.W; H = f.H; };
    window.addEventListener('resize', onResize);

    const stop = loop((dt0) => {
      const dt = pausedRef?.current ? 0 : dt0;
      st.t += dt;
      if (!st.over && st.t >= BASKET_SECONDS) {
        st.over = true;
        hud();
        setTimeout(() => cbs.current.onEnd({ score: st.score, stats: { made: st.made, shots: st.shots } }), 400);
      }
      if (Math.floor(st.t * 4) !== Math.floor((st.t - dt) * 4)) hud();
      const moving = difficulty === 'hard' || (difficulty === 'normal' && st.t > 15);
      const amp = difficulty === 'hard' ? W * 0.28 : W * 0.16;
      st.ph = (st.ph || 0) + dt * (difficulty === 'hard' ? 1.3 : 0.9) * sp;
      st.hx = W / 2 + (moving ? Math.sin(st.ph) * amp : 0);
      const HY = hy(), RH = rimHalf();
      const rimL = { x: st.hx - RH, y: HY }, rimR = { x: st.hx + RH, y: HY };
      const b = st.ball;
      if (b.fly) {
        b.t += dt;
        const py = b.y;
        b.vy += G * dt;
        b.x += b.vx * dt; b.y += b.vy * dt;
        [rimL, rimR].forEach((p) => {
          const dx = b.x - p.x, dy = b.y - p.y, d = Math.hypot(dx, dy);
          if (d < R + 3 && d > 0) {
            const nx = dx / d, ny = dy / d;
            b.x = p.x + nx * (R + 3); b.y = p.y + ny * (R + 3);
            const dot = b.vx * nx + b.vy * ny;
            if (dot < 0) { b.vx -= 1.6 * dot * nx; b.vy -= 1.6 * dot * ny; b.vx *= 0.8; b.vy *= 0.8; }
            if (!b.rim) sound.play('tick');
            b.rim = true;
          }
        });
        if (!b.scored && b.vy > 0 && py < HY && b.y >= HY && b.x > rimL.x + 4 && b.x < rimR.x - 4) {
          b.scored = true;
          const clean = !b.rim;
          const pts = clean ? 3 + (st.streak > 0 ? 1 : 0) : 2;
          st.streak = clean ? st.streak + 1 : 0;
          st.score += pts; st.made += 1; st.net = 0.5;
          st.msg = { text: `+${pts}${clean ? ' 🔥' : ''}`, t: 0.9 };
          sound.play(clean ? 'pick' : 'ok');
          hud();
        }
        if (b.y > H + 60 || b.x < -80 || b.x > W + 80 || b.t > 4) {
          if (!b.scored) st.streak = 0;
          st.ball = home();
        }
      }
      st.net = Math.max(0, st.net - dt);
      if (st.msg) { st.msg.t -= dt; if (st.msg.t <= 0) st.msg = null; }

      // draw
      const bg = ctx.createLinearGradient(0, 0, 0, H);
      bg.addColorStop(0, '#1f1235'); bg.addColorStop(0.6, '#3b1d4a'); bg.addColorStop(1, '#7c2d12');
      ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = '#ffffff10';
      for (let i = 0; i < 6; i += 1) ctx.fillRect((i * W) / 6, H * 0.72, 2, H);
      ctx.fillStyle = '#9a3412'; ctx.fillRect(0, H - 40, W, 40);
      // backboard
      const bw = RH * 3.2, bh = RH * 2.2;
      ctx.fillStyle = '#f8fafcdd'; ctx.fillRect(st.hx - bw / 2, HY - bh + 6, bw, bh);
      ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 3; ctx.strokeRect(st.hx - RH * 0.7, HY - RH * 1.2, RH * 1.4, RH * 1.1);
      // rim (back half)
      ctx.strokeStyle = '#f97316'; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.ellipse(st.hx, HY, RH, 7, 0, Math.PI, 0); ctx.stroke();
      // ball
      const drawBall = () => {
        ctx.save(); ctx.translate(b.x, b.y); ctx.rotate(b.t * (b.vx / 60));
        ctx.fillStyle = '#ea580c'; ctx.shadowColor = '#fb923c'; ctx.shadowBlur = 10;
        ctx.beginPath(); ctx.arc(0, 0, R, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
        ctx.strokeStyle = '#431407'; ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.arc(0, 0, R, 0, Math.PI * 2); ctx.moveTo(-R, 0); ctx.lineTo(R, 0); ctx.moveTo(0, -R); ctx.lineTo(0, R); ctx.stroke();
        ctx.beginPath(); ctx.arc(-R * 1.25, 0, R * 0.9, -0.9, 0.9); ctx.stroke();
        ctx.beginPath(); ctx.arc(R * 1.25, 0, R * 0.9, Math.PI - 0.9, Math.PI + 0.9); ctx.stroke();
        ctx.restore();
      };
      const behind = b.fly && b.y < HY && b.vy > 0;
      if (behind) drawBall();
      // net
      ctx.strokeStyle = '#e2e8f0aa'; ctx.lineWidth = 1.4;
      const sway = Math.sin(st.net * 20) * st.net * 8;
      for (let i = 0; i <= 6; i += 1) {
        const x = st.hx - RH + (2 * RH * i) / 6;
        ctx.beginPath(); ctx.moveTo(x, HY); ctx.lineTo(st.hx - RH * 0.6 + (1.2 * RH * i) / 6 + sway, HY + 38); ctx.stroke();
      }
      ctx.beginPath(); ctx.moveTo(st.hx - RH * 0.8, HY + 18); ctx.lineTo(st.hx + RH * 0.8, HY + 18); ctx.stroke();
      // rim (front half)
      ctx.strokeStyle = '#fb923c'; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.ellipse(st.hx, HY, RH, 7, 0, 0, Math.PI); ctx.stroke();
      if (!behind) drawBall();
      if (!b.fly && !st.over) {
        ctx.fillStyle = '#ffffff80'; ctx.font = 'bold 13px system-ui'; ctx.textAlign = 'center';
        ctx.fillText('⇡', W / 2, H - 104 + Math.sin(st.t * 5) * 4);
      }
      if (st.msg) {
        ctx.globalAlpha = Math.min(1, st.msg.t * 2);
        ctx.fillStyle = '#fde047'; ctx.font = 'bold 30px system-ui'; ctx.textAlign = 'center';
        ctx.fillText(st.msg.text, st.hx, HY - 70 - (0.9 - st.msg.t) * 40);
        ctx.globalAlpha = 1;
      }
      return true;
    });
    return () => { stop(); canvas.removeEventListener('pointerdown', down); window.removeEventListener('pointerup', up); window.removeEventListener('resize', onResize); };
  }, [difficulty]); // eslint-disable-line react-hooks/exhaustive-deps

  return <canvas ref={ref} className="w-full h-full touch-none select-none block" data-testid="arcade-canvas-basket" />;
}
