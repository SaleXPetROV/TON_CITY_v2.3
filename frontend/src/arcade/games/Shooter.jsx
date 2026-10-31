/** «Небесный патруль» — vertical space shooter (close to the ThunderWaves one).
 *  Drag to steer, the ship shoots by itself. Lives by difficulty: easy 5 · normal 3 · hard 2 (and the pace).
 *  Waves: shoot down the wave's quota → the FLAGSHIP arrives; beat it → next wave (stronger, faster).
 *  Glowing enemies drop a bonus token:
 *    3x  triple shot (10 s) · W  two wingmen (12 s) · S  slow-motion for enemies (7 s) · ◈  shield (8 s)
 *  Kills in quick succession build a combo: ×2 from 5, ×3 from 12 in a row (reset by a hit or a pause in kills). */
import { useEffect, useRef } from 'react';
import { fitCanvas, loop, mulberry32, sound } from '@/arcade/core';

export const SHOOTER_BUFFS = {
  triple: { dur: 10, color: '#facc15', token: '3x', key: 'ar_buff_triple' },
  wings: { dur: 12, color: '#34d399', token: 'W', key: 'ar_buff_wings' },
  slow: { dur: 7, color: '#c4b5fd', token: 'S', key: 'ar_buff_slow' },
  shield: { dur: 8, color: '#38bdf8', token: '◈', key: 'ar_buff_shield' },
};
const BUFF_KEYS = Object.keys(SHOOTER_BUFFS);
const DIFF = {
  easy: { lives: 5, speed: 0.78, fire: 1.55, spawn: 1.3 },
  normal: { lives: 3, speed: 1, fire: 1, spawn: 1 },
  hard: { lives: 2, speed: 1.28, fire: 0.62, spawn: 0.78 },
};
const PTS = { scout: 15, fighter: 25, heavy: 60, boss: 400 };

/* ───────── art ───────── */
function makeBackdrop(W, H, rnd) {
  const c = document.createElement('canvas');
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  c.width = W * dpr; c.height = H * 2 * dpr;
  const g = c.getContext('2d');
  g.scale(dpr, dpr);
  const bg = g.createLinearGradient(0, 0, 0, H * 2);
  bg.addColorStop(0, '#0a0718'); bg.addColorStop(0.5, '#140d2e'); bg.addColorStop(1, '#0a0718');
  g.fillStyle = bg; g.fillRect(0, 0, W, H * 2);
  for (let i = 0; i < 5; i += 1) {                               // nebula
    const x = rnd() * W, y = rnd() * H * 2, r = 120 + rnd() * 200;
    const n = g.createRadialGradient(x, y, 0, x, y, r);
    const hue = [270, 300, 230, 330, 250][i];
    n.addColorStop(0, `hsla(${hue},70%,45%,0.18)`); n.addColorStop(1, 'hsla(0,0%,0%,0)');
    g.fillStyle = n; g.fillRect(0, 0, W, H * 2);
  }
  for (let i = 0; i < 160; i += 1) {
    g.fillStyle = `rgba(220,225,255,${0.15 + rnd() * 0.45})`;
    const s = rnd() < 0.1 ? 1.6 : 0.9;
    g.fillRect(rnd() * W, rnd() * H * 2, s, s);
  }
  return c;
}

function drawPlanet(ctx, x, y, r, t) {
  ctx.save();
  // ring (back)
  ctx.strokeStyle = 'rgba(160,150,220,0.35)'; ctx.lineWidth = r * 0.09;
  ctx.beginPath(); ctx.ellipse(x, y, r * 1.75, r * 0.42, -0.32, Math.PI * 1.02, Math.PI * 1.98); ctx.stroke();
  const p = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
  p.addColorStop(0, '#6d5fd6'); p.addColorStop(0.55, '#3b2f8f'); p.addColorStop(1, '#170f3d');
  ctx.fillStyle = p; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  ctx.save(); ctx.clip();
  ctx.globalAlpha = 0.18; ctx.fillStyle = '#c7bfff';
  for (let i = -3; i <= 3; i += 1) ctx.fillRect(x - r, y + i * r * 0.22 + Math.sin(t * 0.2 + i) * 2, r * 2, r * 0.06);
  ctx.restore();
  // ring (front)
  ctx.strokeStyle = 'rgba(180,170,240,0.45)';
  ctx.beginPath(); ctx.ellipse(x, y, r * 1.75, r * 0.42, -0.32, Math.PI * -0.02, Math.PI * 1.02); ctx.stroke();
  ctx.restore();
}

function drawPlayer(ctx, x, y, s, t, tint) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  // flames
  [-6, 6].forEach((ox) => {
    const fl = 14 + Math.sin(t * 45 + ox) * 4;
    const g = ctx.createLinearGradient(0, 16, 0, 16 + fl);
    g.addColorStop(0, '#fff'); g.addColorStop(0.3, '#fdba74'); g.addColorStop(1, 'rgba(249,115,22,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(ox - 3.5, 16); ctx.quadraticCurveTo(ox, 16 + fl * 1.2, ox + 3.5, 16); ctx.fill();
  });
  // wings
  const wing = ctx.createLinearGradient(-26, 0, 26, 0);
  wing.addColorStop(0, '#6b7280'); wing.addColorStop(0.5, '#e5e7eb'); wing.addColorStop(1, '#6b7280');
  ctx.fillStyle = wing;
  ctx.beginPath(); ctx.moveTo(-5, -2); ctx.lineTo(-26, 12); ctx.lineTo(-24, 17); ctx.lineTo(-6, 12); ctx.lineTo(6, 12); ctx.lineTo(24, 17); ctx.lineTo(26, 12); ctx.lineTo(5, -2); ctx.closePath(); ctx.fill();
  ctx.fillStyle = tint || '#f59e0b';                               // orange accents
  ctx.beginPath(); ctx.moveTo(-20, 11); ctx.lineTo(-11, 6); ctx.lineTo(-10, 9); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.moveTo(20, 11); ctx.lineTo(11, 6); ctx.lineTo(10, 9); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#ef4444'; ctx.fillRect(-26, 11, 2, 3); ctx.fillRect(24, 11, 2, 3);
  // fuselage
  const body = ctx.createLinearGradient(-7, 0, 7, 0);
  body.addColorStop(0, '#9ca3af'); body.addColorStop(0.45, '#f9fafb'); body.addColorStop(1, '#6b7280');
  ctx.fillStyle = body;
  ctx.beginPath(); ctx.moveTo(0, -26); ctx.quadraticCurveTo(7, -14, 7, 4); ctx.lineTo(8, 17); ctx.lineTo(-8, 17); ctx.lineTo(-7, 4); ctx.quadraticCurveTo(-7, -14, 0, -26); ctx.fill();
  ctx.fillStyle = tint || '#f97316'; ctx.beginPath(); ctx.moveTo(0, -26); ctx.lineTo(2.4, -20); ctx.lineTo(-2.4, -20); ctx.closePath(); ctx.fill();
  const cp = ctx.createLinearGradient(0, -16, 0, -2);
  cp.addColorStop(0, '#7dd3fc'); cp.addColorStop(1, '#1e3a8a');
  ctx.fillStyle = cp; ctx.beginPath(); ctx.ellipse(0, -9, 3.2, 7, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.7)'; ctx.beginPath(); ctx.ellipse(-1, -12, 0.9, 2.2, 0, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

function drawEnemy(ctx, e, t) {
  ctx.save(); ctx.translate(e.x, e.y);
  const hit = e.flash > 0;
  if (e.glow) {                                                 // carries a bonus
    const a = 0.5 + Math.sin(t * 6) * 0.25;
    const g = ctx.createRadialGradient(0, 0, 4, 0, 0, e.r * 1.9);
    g.addColorStop(0, `rgba(255,240,170,${a})`); g.addColorStop(1, 'rgba(255,200,80,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, e.r * 1.9, 0, Math.PI * 2); ctx.fill();
  }
  if (e.kind === 'scout') {
    const g = ctx.createLinearGradient(0, -14, 0, 18);
    g.addColorStop(0, hit ? '#fff' : '#fdba74'); g.addColorStop(1, hit ? '#fff' : '#c2410c');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(0, 20); ctx.lineTo(7, 2); ctx.lineTo(18, -14); ctx.lineTo(4, -8); ctx.lineTo(0, -16); ctx.lineTo(-4, -8); ctx.lineTo(-18, -14); ctx.lineTo(-7, 2); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#7c2d12'; ctx.fillRect(-1, -10, 2, 22);
    ctx.fillStyle = '#fde68a'; ctx.beginPath(); ctx.arc(0, 0, 2.6, 0, Math.PI * 2); ctx.fill();
  } else if (e.kind === 'fighter') {
    const g = ctx.createLinearGradient(-22, 0, 22, 0);
    g.addColorStop(0, hit ? '#fff' : '#9d174d'); g.addColorStop(0.5, hit ? '#fff' : '#f472b6'); g.addColorStop(1, hit ? '#fff' : '#9d174d');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(-24, -14); ctx.lineTo(-8, -2); ctx.lineTo(-5, -12); ctx.lineTo(5, -12); ctx.lineTo(8, -2); ctx.lineTo(24, -14); ctx.lineTo(18, 6); ctx.lineTo(6, 8); ctx.lineTo(0, 20); ctx.lineTo(-6, 8); ctx.lineTo(-18, 6); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#4a044e'; ctx.beginPath(); ctx.ellipse(0, 0, 5, 9, 0, 0, Math.PI * 2); ctx.fill();
    ctx.shadowColor = '#22d3ee'; ctx.shadowBlur = 12; ctx.fillStyle = '#67e8f9';
    ctx.beginPath(); ctx.arc(0, -6, 3, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
    ctx.fillStyle = '#fb7185'; ctx.beginPath(); ctx.arc(0, 8, 2, 0, Math.PI * 2); ctx.fill();
  } else if (e.kind === 'heavy') {
    const g = ctx.createLinearGradient(0, -20, 0, 20);
    g.addColorStop(0, hit ? '#fff' : '#7c3aed'); g.addColorStop(1, hit ? '#fff' : '#3b0764');
    ctx.fillStyle = g;
    ctx.beginPath();
    for (let i = 0; i < 6; i += 1) { const a = Math.PI / 6 + (i * Math.PI) / 3; ctx[i ? 'lineTo' : 'moveTo'](Math.cos(a) * 26, Math.sin(a) * 24); }
    ctx.closePath(); ctx.fill();
    ctx.strokeStyle = '#a78bfa'; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.fillStyle = '#1e1b4b';
    [-10, 10].forEach((ox) => { ctx.beginPath(); ctx.arc(ox, 4, 5, 0, Math.PI * 2); ctx.fill(); ctx.fillRect(ox - 1.5, 4, 3, 16); });
    ctx.shadowColor = '#e879f9'; ctx.shadowBlur = 14; ctx.fillStyle = '#f0abfc';
    ctx.beginPath(); ctx.arc(0, -6, 4, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
  } else {                                                      // flagship
    const w = e.r * 1.6;
    const g = ctx.createLinearGradient(0, -30, 0, 34);
    g.addColorStop(0, hit ? '#fff' : '#f87171'); g.addColorStop(0.6, hit ? '#fff' : '#b91c1c'); g.addColorStop(1, hit ? '#fff' : '#450a0a');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(-w, -8); ctx.lineTo(-w * 0.55, -26); ctx.lineTo(w * 0.55, -26); ctx.lineTo(w, -8); ctx.lineTo(w * 0.5, 14); ctx.lineTo(0, 34); ctx.lineTo(-w * 0.5, 14); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = '#fecaca55'; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = '#1f2937';
    [-0.62, -0.28, 0.28, 0.62].forEach((k) => { ctx.beginPath(); ctx.arc(w * k, -2 + Math.abs(k) * 6, 6, 0, Math.PI * 2); ctx.fill(); });
    ctx.shadowColor = '#fde047'; ctx.shadowBlur = 20; ctx.fillStyle = '#fef08a';
    ctx.beginPath(); ctx.arc(0, -4, 7 + Math.sin(t * 8) * 1.5, 0, Math.PI * 2); ctx.fill();
    ctx.shadowColor = '#f472b6';
    [-1, -0.5, 0.5, 1].forEach((k, i) => { ctx.fillStyle = Math.sin(t * 6 + i) > 0 ? '#f9a8d4' : '#be185d'; ctx.beginPath(); ctx.arc(w * k * 0.95, -12, 4, 0, Math.PI * 2); ctx.fill(); });
    ctx.shadowBlur = 0;
  }
  ctx.restore();
  if (e.kind === 'heavy' && e.hp < e.maxHp) {
    ctx.fillStyle = '#0009'; ctx.fillRect(e.x - 20, e.y - e.r - 9, 40, 3);
    ctx.fillStyle = '#c084fc'; ctx.fillRect(e.x - 20, e.y - e.r - 9, 40 * (e.hp / e.maxHp), 3);
  }
}

/* ───────── the game ───────── */
export default function Shooter({ seed, difficulty, tuning, onHud, onEnd, onDeath, pausedRef, t }) {
  const ref = useRef(null);
  const cbs = useRef({ onHud, onEnd, onDeath, t });
  cbs.current = { onHud, onEnd, onDeath, t };

  useEffect(() => {
    const canvas = ref.current;
    let { ctx, W, H } = fitCanvas(canvas);
    const rnd = mulberry32(seed || 1);
    // difficulty preset × the admin's tuning (speed %, lives)
    const base = DIFF[difficulty] || DIFF.normal;
    const sp = (tuning?.speed || 100) / 100;
    const D = { ...base, speed: base.speed * sp, spawn: base.spawn / sp, lives: tuning?.lives || base.lives };
    const S = Math.min(1.2, Math.max(0.85, W / 380));
    let backdrop = makeBackdrop(W, H, rnd);
    const st = {
      t: 0, score: 0, lives: D.lives, inv: 0, over: false, kills: 0,
      px: W / 2, py: H - 110, tx: W / 2, ty: H - 110,
      fireT: 0.3, spawnT: 1.2, wave: 1, waveKills: 0, boss: null, banner: { text: 1, t: 1.6 },
      bullets: [], ebullets: [], enemies: [], drops: [], parts: [], pops: [], streaks: [],
      buffs: {}, combo: 0, comboT: 0, scroll: 0, planetY: H * 0.35,
    };
    const quota = () => 10 + st.wave * 4;
    const mult = () => (st.combo >= 12 ? 3 : st.combo >= 5 ? 2 : 1);
    let hudT = 0;
    const hud = () => cbs.current.onHud && cbs.current.onHud({
      score: st.score, lives: st.lives, maxLives: D.lives, wave: st.wave,
      waveProgress: st.boss ? 1 - st.boss.hp / st.boss.maxHp : Math.min(1, st.waveKills / quota()),
      combo: mult() > 1 ? mult() : 0,
      boss: st.boss ? { hp: st.boss.hp / st.boss.maxHp } : null,
      buffs: BUFF_KEYS.filter((k) => st.buffs[k] > 0).map((k) => ({ k, ...SHOOTER_BUFFS[k], left: st.buffs[k] })),
      stats: { kills: st.kills, wave: st.wave },
    });
    hud();

    const pt = (e) => { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
    let drag = null;
    const down = (e) => { sound.unlock(); const p = pt(e); drag = { sx: p.x, sy: p.y, px: st.tx, py: st.ty }; canvas.setPointerCapture?.(e.pointerId); };
    const move = (e) => {
      if (!drag || pausedRef?.current) return;
      const p = pt(e);
      st.tx = Math.max(20, Math.min(W - 20, drag.px + (p.x - drag.sx) * 1.3));
      st.ty = Math.max(H * 0.3, Math.min(H - 34, drag.py + (p.y - drag.sy) * 1.3));
    };
    const up = () => { drag = null; };
    const keys = {};
    const kd = (e) => { keys[e.key] = true; };
    const ku = (e) => { keys[e.key] = false; };
    canvas.addEventListener('pointerdown', down);
    canvas.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    window.addEventListener('keydown', kd);
    window.addEventListener('keyup', ku);
    const onResize = () => { const f = fitCanvas(canvas); ctx = f.ctx; W = f.W; H = f.H; backdrop = makeBackdrop(W, H, rnd); };
    window.addEventListener('resize', onResize);

    const boom = (x, y, color, n = 16, sp = 200) => {
      for (let i = 0; i < n; i += 1) {
        const a = rnd() * Math.PI * 2, v = 40 + rnd() * sp;
        st.parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: 0.35 + rnd() * 0.5, c: rnd() < 0.3 ? '#fff' : color, s: 1.5 + rnd() * 2.5 });
      }
    };
    const slowK = () => (st.buffs.slow > 0 ? 0.45 : 1);
    const spawn = () => {
      const lvl = st.wave;
      const roll = rnd();
      const x = 30 + rnd() * (W - 60);
      let e;
      const pHeavy = Math.min(0.22, 0.06 + lvl * 0.03);
      const pFighter = Math.min(0.45, 0.25 + lvl * 0.04);
      if (roll < pHeavy) e = { kind: 'heavy', hp: 5 + lvl, r: 26, vy: (55 + lvl * 3) * D.speed, fire: 1.4 + rnd(), stopY: H * (0.14 + rnd() * 0.16), vx: (rnd() < 0.5 ? -1 : 1) * 40 };
      else if (roll < pHeavy + pFighter) e = { kind: 'fighter', hp: 2, r: 20, vy: (85 + lvl * 6) * D.speed, ph: rnd() * 6, fire: 1 + rnd() * 1.6, amp: 30 + rnd() * 40 };
      else e = { kind: 'scout', hp: 1, r: 15, vy: (140 + lvl * 9) * D.speed, aim: rnd() < 0.35 };
      const glow = rnd() < 0.16;
      st.enemies.push({ ...e, x, x0: x, y: -30, maxHp: e.hp, flash: 0, glow });
      if (e.kind === 'scout' && rnd() < 0.4) {                      // scouts come in pairs / triples
        const n = 1 + Math.floor(rnd() * 2);
        for (let i = 1; i <= n; i += 1) st.enemies.push({ ...e, x: Math.max(24, Math.min(W - 24, x + i * 36 * (x > W / 2 ? -1 : 1))), x0: x, y: -30 - i * 34, maxHp: 1, flash: 0, glow: false });
      }
    };
    const spawnBoss = () => {
      const hp = 50 + st.wave * 25;
      st.boss = { kind: 'boss', hp, maxHp: hp, r: 52, x: W / 2, y: -70, vy: 60, vx: 70 * D.speed, flash: 0, fire: 1.4, fire2: 3, boss: true };
      st.enemies.push(st.boss);
      sound.play('big');
    };
    const addPop = (x, y, text, color = '#fde68a') => st.pops.push({ x, y, text, life: 0.9, color });
    const kill = (e) => {
      e.dead = true;
      st.combo += 1; st.comboT = 1.6;
      const pts = PTS[e.kind] * mult();
      st.score += pts; st.kills += 1;
      addPop(e.x, e.y - 10, `+${pts}`, mult() > 1 ? '#f0abfc' : '#fde68a');
      if (e.boss) {
        boom(e.x, e.y, '#fca5a5', 80, 320); boom(e.x, e.y, '#fde047', 50, 220);
        sound.play('big');
        st.drops.push({ x: e.x - 30, y: e.y, k: BUFF_KEYS[Math.floor(rnd() * 4)], t: 0 });
        st.drops.push({ x: e.x + 30, y: e.y, k: BUFF_KEYS[Math.floor(rnd() * 4)], t: 0 });
        st.boss = null; st.wave += 1; st.waveKills = 0; st.banner = { text: st.wave, t: 1.6 };
        st.ebullets = [];
      } else {
        st.waveKills += 1;
        boom(e.x, e.y, e.kind === 'heavy' ? '#c084fc' : e.kind === 'fighter' ? '#f472b6' : '#fb923c', e.kind === 'heavy' ? 30 : 16);
        sound.play('boom');
        if (e.glow) st.drops.push({ x: e.x, y: e.y, k: BUFF_KEYS[Math.floor(rnd() * 4)], t: 0 });
        if (!st.boss && st.waveKills >= quota()) spawnBoss();
      }
      hud();
    };
    const hitPlayer = () => {
      if (st.inv > 0 || st.over) return;
      if (st.buffs.shield > 0) { st.inv = 0.35; boom(st.px, st.py, '#38bdf8', 10, 120); return; }
      st.lives -= 1; st.inv = 1.8; st.combo = 0;
      boom(st.px, st.py, '#f43f5e', 30, 260);
      sound.play('hit');
      if (navigator.vibrate) try { navigator.vibrate(70); } catch (_) { /* ignore */ }
      hud();
      if (st.lives <= 0) {
        st.over = true;
        boom(st.px, st.py, '#fde047', 60, 300);
        const end = () => cbs.current.onEnd({ score: st.score, stats: { kills: st.kills, wave: st.wave } });
        if (cbs.current.onDeath && !st.revived) {
          // «Продолжить?» — an ad brings the ship back right here (once per game)
          setTimeout(() => {
            st.waiting = true;
            cbs.current.onDeath({
              revive: () => {
                st.revived = true; st.waiting = false; st.over = false; st.lives = 1; st.inv = 2.5;
                st.ebullets = []; st.enemies = st.enemies.filter((e) => e.boss || e.y < H * 0.3); hud();
              },
              decline: () => { st.waiting = false; end(); },
            });
          }, 800);
        } else setTimeout(end, 900);
      }
    };
    const fire = () => {
      const shot = (x, y, ang, c = '#fff7d6') => st.bullets.push({ x, y, vx: Math.sin(ang) * 760, vy: -Math.cos(ang) * 760, c });
      if (st.buffs.triple > 0) { shot(st.px, st.py - 26, 0); shot(st.px - 8, st.py - 18, -0.16, '#fde047'); shot(st.px + 8, st.py - 18, 0.16, '#fde047'); } else shot(st.px, st.py - 26, 0);
      if (st.buffs.wings > 0) { shot(st.px - 44, st.py - 6, 0, '#86efac'); shot(st.px + 44, st.py - 6, 0, '#86efac'); }
      st.fireT = 0.21;
      sound.play('shoot');
    };

    const stop = loop((dt) => {
      const paused = pausedRef?.current || st.waiting;
      if (!paused) {
        st.t += dt;
        const k = slowK();
        st.scroll += dt * 26;
        st.planetY += dt * 6;
        if (st.planetY > H + 260) st.planetY = -260;
        if (!st.over) {
          if (keys.ArrowLeft) st.tx = Math.max(20, st.tx - 420 * dt);
          if (keys.ArrowRight) st.tx = Math.min(W - 20, st.tx + 420 * dt);
          if (keys.ArrowUp) st.ty = Math.max(H * 0.3, st.ty - 420 * dt);
          if (keys.ArrowDown) st.ty = Math.min(H - 34, st.ty + 420 * dt);
          st.px += (st.tx - st.px) * Math.min(1, dt * 16);
          st.py += (st.ty - st.py) * Math.min(1, dt * 16);
          st.fireT -= dt;
          if (st.fireT <= 0) fire();
          st.inv = Math.max(0, st.inv - dt);
          BUFF_KEYS.forEach((b) => { if (st.buffs[b] > 0) st.buffs[b] = Math.max(0, st.buffs[b] - dt); });
          if (st.comboT > 0) { st.comboT -= dt; if (st.comboT <= 0) st.combo = 0; }
          st.spawnT -= dt;
          if (st.spawnT <= 0) {
            if (!st.boss || rnd() < 0.25) spawn();
            st.spawnT = Math.max(0.32, 1.05 - st.wave * 0.07) * D.spawn * (0.7 + rnd() * 0.6) * (st.boss ? 2.2 : 1);
          }
        }
        if (st.banner) { st.banner.t -= dt; if (st.banner.t <= 0) st.banner = null; }
        st.bullets.forEach((b) => { b.x += b.vx * dt; b.y += b.vy * dt; });
        st.bullets = st.bullets.filter((b) => b.y > -30 && b.x > -30 && b.x < W + 30 && !b.dead);
        st.ebullets.forEach((b) => { b.x += b.vx * dt * k; b.y += b.vy * dt * k; });
        st.ebullets = st.ebullets.filter((b) => b.y < H + 20 && b.y > -60 && b.x > -20 && b.x < W + 20 && !b.dead);
        st.enemies.forEach((e) => {
          e.flash = Math.max(0, e.flash - dt);
          if (e.boss) {
            if (e.y < H * 0.2) e.y += e.vy * dt * k; else { e.x += e.vx * dt * k; if (e.x < e.r * 1.6 || e.x > W - e.r * 1.6) e.vx *= -1; }
          } else if (e.kind === 'heavy') {
            if (e.y < e.stopY) e.y += e.vy * dt * k; else { e.x += e.vx * dt * k; if (e.x < 30 || e.x > W - 30) e.vx *= -1; e.y += 6 * dt * k; }
          } else if (e.kind === 'fighter') {
            e.y += e.vy * dt * k; e.x = e.x0 + Math.sin(st.t * 2 + e.ph) * e.amp;
          } else {
            e.y += e.vy * dt * k;
            if (e.aim && e.y < st.py - 120) e.x += Math.sign(st.px - e.x) * 50 * dt * k;
          }
          if (e.fire !== undefined && e.y > 10 && !st.over) {
            e.fire -= dt * k;
            if (e.fire <= 0) {
              const ang = Math.atan2(st.py - e.y, st.px - e.x);
              const sp = 210 * D.speed;
              if (e.boss) {
                for (let i = 0; i < 7; i += 1) { const a = Math.PI / 2 + (i - 3) * 0.2; st.ebullets.push({ x: e.x, y: e.y + 20, vx: Math.cos(a) * sp * 0.85, vy: Math.sin(a) * sp * 0.85, r: 4.5, c: '#f9a8d4' }); }
                e.fire = 1.6 * D.fire;
              } else if (e.kind === 'heavy') {
                [-10, 10].forEach((ox) => st.ebullets.push({ x: e.x + ox, y: e.y + 18, vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp, r: 4, c: '#f0abfc' }));
                e.fire = 2.1 * D.fire;
              } else {
                st.ebullets.push({ x: e.x, y: e.y + 14, vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp, r: 3.5, c: '#fda4af' });
                e.fire = (1.7 + rnd() * 1.5) * D.fire;
              }
            }
            if (e.boss) {
              e.fire2 -= dt * k;
              if (e.fire2 <= 0) {                                      // aimed burst
                for (let i = 0; i < 3; i += 1) {
                  const ang = Math.atan2(st.py - e.y, st.px - e.x) + (i - 1) * 0.08;
                  st.ebullets.push({ x: e.x, y: e.y + 26, vx: Math.cos(ang) * 300 * D.speed, vy: Math.sin(ang) * 300 * D.speed, r: 3.5, c: '#fde047' });
                }
                e.fire2 = 2.6 * D.fire;
              }
            }
          }
        });
        st.bullets.forEach((b) => {
          for (const e of st.enemies) {
            if (e.dead) continue;
            const dx = b.x - e.x, dy = b.y - e.y;
            const rr = e.boss ? e.r * 1.2 : e.r + 3;
            if (dx * dx + dy * dy < rr * rr) {
              b.dead = true; e.hp -= 1; e.flash = 0.05;
              st.parts.push({ x: b.x, y: b.y, vx: 0, vy: -30, life: 0.15, c: '#fff', s: 3 });
              if (e.hp <= 0) kill(e); else if (e.boss && (hudT += 1) % 3 === 0) hud();
              break;
            }
          }
        });
        st.enemies = st.enemies.filter((e) => !e.dead && e.y < H + 70);
        if (!st.over) {
          const pr = 11 * S;
          st.ebullets.forEach((b) => {
            const dx = b.x - st.px, dy = b.y - st.py;
            const rr = (st.buffs.shield > 0 ? 34 * S : pr) + b.r;
            if (dx * dx + dy * dy < rr * rr) { b.dead = true; hitPlayer(); }
          });
          st.enemies.forEach((e) => {
            const dx = e.x - st.px, dy = e.y - st.py;
            const rr = (e.boss ? e.r : e.r * 0.8) + pr;
            if (dx * dx + dy * dy < rr * rr) {
              if (!e.boss) { e.hp = 0; kill(e); }
              hitPlayer();
            }
          });
          st.drops.forEach((d) => {
            d.y += 80 * dt; d.t += dt;
            const dx = d.x - st.px, dy = d.y - st.py;
            if (dx * dx + dy * dy < 38 * 38) {
              d.dead = true; st.buffs[d.k] = SHOOTER_BUFFS[d.k].dur;
              boom(d.x, d.y, SHOOTER_BUFFS[d.k].color, 14, 140);
              addPop(d.x, d.y - 16, (cbs.current.t ? cbs.current.t(SHOOTER_BUFFS[d.k].key) : d.k), SHOOTER_BUFFS[d.k].color);
              sound.play('pick'); hud();
            }
          });
        }
        st.drops = st.drops.filter((d) => !d.dead && d.y < H + 30);
        st.parts.forEach((p) => { p.x += p.vx * dt; p.y += p.vy * dt; p.vx *= 0.95; p.vy *= 0.95; p.life -= dt; });
        st.parts = st.parts.filter((p) => p.life > 0);
        st.pops.forEach((p) => { p.y -= 40 * dt; p.life -= dt; });
        st.pops = st.pops.filter((p) => p.life > 0);
        if (Math.floor(st.t * 5) !== Math.floor((st.t - dt) * 5)) hud();
      }

      /* draw */
      const off = (st.scroll % H);
      ctx.drawImage(backdrop, 0, off - H, W, H * 2);
      ctx.drawImage(backdrop, 0, off - H * 3, W, H * 2);
      drawPlanet(ctx, W * 0.78, st.planetY, Math.min(130, W * 0.3), st.t);
      // speed streaks
      ctx.fillStyle = 'rgba(220,225,255,0.35)';
      for (let i = 0; i < 26; i += 1) {
        const x = (i * 97.3) % W, y = ((i * 211.7 + st.t * (120 + (i % 5) * 50)) % (H + 40)) - 20;
        ctx.fillRect(x, y, 1.2, 6 + (i % 4) * 3);
      }
      st.drops.forEach((d) => {
        const b = SHOOTER_BUFFS[d.k];
        const y = d.y + Math.sin(d.t * 5) * 3;
        ctx.save();
        ctx.shadowColor = b.color; ctx.shadowBlur = 16;
        ctx.fillStyle = '#0b0f1e'; ctx.beginPath(); ctx.arc(d.x, y, 15, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = b.color; ctx.lineWidth = 2.5; ctx.stroke();
        ctx.shadowBlur = 0;
        ctx.fillStyle = b.color; ctx.font = 'bold 13px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(b.token, d.x, y + 1);
        ctx.restore();
      });
      st.bullets.forEach((b) => {
        ctx.strokeStyle = b.c; ctx.lineWidth = 3; ctx.lineCap = 'round';
        ctx.shadowColor = '#fde68a'; ctx.shadowBlur = 8;
        ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x - b.vx * 0.022, b.y - b.vy * 0.022); ctx.stroke();
      });
      ctx.shadowBlur = 0;
      st.enemies.forEach((e) => drawEnemy(ctx, e, st.t));
      st.ebullets.forEach((b) => {
        const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r * 2.2);
        g.addColorStop(0, '#fff'); g.addColorStop(0.35, b.c); g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(b.x, b.y, b.r * 2.2, 0, Math.PI * 2); ctx.fill();
      });
      if (!st.over && (st.inv <= 0 || Math.floor(st.t * 14) % 2 === 0)) {
        if (st.buffs.wings > 0) { drawPlayer(ctx, st.px - 44, st.py + 10, S * 0.5, st.t, '#34d399'); drawPlayer(ctx, st.px + 44, st.py + 10, S * 0.5, st.t, '#34d399'); }
        drawPlayer(ctx, st.px, st.py, S, st.t);
        if (st.buffs.shield > 0) {
          const a = 0.35 + Math.sin(st.t * 8) * 0.12;
          const blink = st.buffs.shield < 2 && Math.floor(st.t * 8) % 2 === 0;
          if (!blink) {
            const g = ctx.createRadialGradient(st.px, st.py, 10, st.px, st.py, 36 * S);
            g.addColorStop(0, 'rgba(56,189,248,0)'); g.addColorStop(0.75, `rgba(56,189,248,${a * 0.35})`); g.addColorStop(1, `rgba(125,211,252,${a + 0.3})`);
            ctx.fillStyle = g; ctx.beginPath(); ctx.arc(st.px, st.py, 36 * S, 0, Math.PI * 2); ctx.fill();
          }
        }
      }
      if (st.buffs.slow > 0) { ctx.fillStyle = 'rgba(167,139,250,0.07)'; ctx.fillRect(0, 0, W, H); }
      st.parts.forEach((p) => { ctx.globalAlpha = Math.max(0, Math.min(1, p.life * 1.8)); ctx.fillStyle = p.c; ctx.fillRect(p.x - p.s / 2, p.y - p.s / 2, p.s, p.s); });
      ctx.globalAlpha = 1;
      st.pops.forEach((p) => {
        ctx.globalAlpha = Math.min(1, p.life * 2);
        ctx.font = 'bold 15px system-ui'; ctx.textAlign = 'center'; ctx.lineWidth = 3; ctx.strokeStyle = '#0008';
        ctx.strokeText(p.text, p.x, p.y); ctx.fillStyle = p.color; ctx.fillText(p.text, p.x, p.y);
      });
      ctx.globalAlpha = 1;
      if (st.banner) {
        const a = Math.min(1, st.banner.t * 2);
        ctx.globalAlpha = a;
        ctx.fillStyle = '#fff'; ctx.font = '900 34px system-ui'; ctx.textAlign = 'center';
        const tt = cbs.current.t ? `${cbs.current.t('ar_wave')} ${st.banner.text}` : `W${st.banner.text}`;
        ctx.shadowColor = '#a78bfa'; ctx.shadowBlur = 20;
        ctx.fillText(tt, W / 2, H * 0.42);
        ctx.shadowBlur = 0; ctx.globalAlpha = 1;
      }
      return true;
    });

    return () => {
      stop();
      canvas.removeEventListener('pointerdown', down);
      canvas.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('keydown', kd);
      window.removeEventListener('keyup', ku);
      window.removeEventListener('resize', onResize);
    };
  }, [seed, difficulty]); // eslint-disable-line react-hooks/exhaustive-deps

  return <canvas ref={ref} className="w-full h-full touch-none select-none block" data-testid="arcade-canvas-shooter" />;
}
