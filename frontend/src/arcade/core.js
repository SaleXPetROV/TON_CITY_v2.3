/** Arcade — shared helpers: the seeded generator (same as backend/arcade.py), «Быстрый счёт» questions,
 *  API calls, canvas setup, and the score formulas the server also uses (memory / tower / snake / tic-tac-toe). */

export const GAMES = ['shooter', 'racer', 'basket', 'snake', 'tower', 'g2048', 'memory', 'math', 'tictac'];
export const DIFFS = ['easy', 'normal', 'hard'];
export const GAME_ICON = { shooter: '🚀', racer: '🏎️', basket: '🏀', snake: '🐍', tower: '🏙️', g2048: '🔢', memory: '🃏', math: '➗', tictac: '⭕' };
export const GAME_GRAD = {
  shooter: 'from-indigo-600 via-blue-700 to-cyan-500',
  racer: 'from-fuchsia-600 via-purple-700 to-indigo-700',
  basket: 'from-orange-500 via-amber-600 to-red-600',
  snake: 'from-emerald-500 via-green-600 to-teal-700',
  tower: 'from-sky-500 via-cyan-600 to-blue-700',
  g2048: 'from-amber-400 via-yellow-500 to-orange-500',
  memory: 'from-pink-500 via-rose-600 to-fuchsia-700',
  math: 'from-lime-500 via-emerald-600 to-cyan-700',
  tictac: 'from-violet-500 via-purple-600 to-pink-600',
};

/** mulberry32 — identical to arcade.mulberry32 on the server. */
export function mulberry32(seed) {
  let a = seed | 0;
  return function next() {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** «Быстрый счёт» questions — identical to arcade.math_questions (the server replays the answers). */
export function mathQuestions(seed, difficulty, n) {
  const r = mulberry32(seed);
  const ops = { easy: ['+', '-'], normal: ['+', '-', '*'], hard: ['+', '-', '*', '/'] }[difficulty] || ['+', '-', '*'];
  const top = { easy: 20, normal: 50, hard: 99 }[difficulty] || 50;
  const out = [];
  for (let i = 0; i < n; i += 1) {
    const op = ops[Math.floor(r() * ops.length)];
    let a = 1 + Math.floor(r() * top);
    let b = 1 + Math.floor(r() * top);
    let ans;
    if (op === '*') {
      a = 2 + Math.floor(r() * 11);
      b = 2 + Math.floor(r() * (difficulty === 'normal' ? 9 : 14));
      ans = a * b;
    } else if (op === '/') {
      b = 2 + Math.floor(r() * 11);
      ans = 2 + Math.floor(r() * 11);
      a = ans * b;
    } else if (op === '-') {
      if (b > a) [a, b] = [b, a];
      ans = a - b;
    } else ans = a + b;
    out.push({ a, b, op, ans });
  }
  return out;
}

export const MEMORY_PAIRS = { easy: 6, normal: 8, hard: 10 };       // pairs on one board (a cleared board is dealt again)
export const MEMORY_SECONDS = { easy: 90, normal: 75, hard: 60 };     // «Память»: the limit is the time, not the score
/** «Память» score — the same formula on the server: pair 50 · cleared board 100 · combo bonus (≤ 50 a pair) */
export const memoryPoints = (pairs, boards, comboBonus) => pairs * 50 + boards * 100 + comboBonus;
export const TICTAC_SECONDS = 120;                                    // «Крестики-нолики»: rounds until 3 losses or the time
export const TICTAC_LIVES = 3;
/** «Крестики-нолики» points of a round: win 100 + 25 per win in a row (up to +100), draw 30, loss 0 */
export const tictacPoints = (res, winStreak) => (res === 'win' ? 100 + 25 * Math.min(4, Math.max(0, winStreak - 1)) : res === 'draw' ? 30 : 0);

// ───────── API ─────────
const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const tok = () => localStorage.getItem('token') || localStorage.getItem('ton_city_token');

export async function arcadeCall(path, opts = {}) {
  const r = await fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tok()}`, ...(opts.headers || {}) },
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(d.detail || `http_${r.status}`); e.status = r.status; e.detail = d.detail; throw e; }
  return d;
}

// ───────── canvas ─────────
/** Size the canvas to its box (crisp on retina). Returns {ctx, W, H} in CSS pixels. */
export function fitCanvas(canvas) {
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const r = canvas.getBoundingClientRect();
  const W = Math.max(200, r.width), H = Math.max(240, r.height);
  canvas.width = Math.round(W * dpr);
  canvas.height = Math.round(H * dpr);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, W, H };
}

/** requestAnimationFrame loop with dt (s, capped). `step(dt, t)` returns false to stop. */
export function loop(step) {
  let last = performance.now(), id = 0, alive = true;
  const f = (now) => {
    if (!alive) return;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (step(dt, now) === false) { alive = false; return; }
    id = requestAnimationFrame(f);
  };
  id = requestAnimationFrame(f);
  return () => { alive = false; cancelAnimationFrame(id); };
}

/** Swipe detector on an element: calls cb('left'|'right'|'up'|'down'). Returns an unsubscribe function. */
export function onSwipe(el, cb, min = 24) {
  let sx = 0, sy = 0, on = false;
  const down = (e) => { on = true; sx = e.clientX; sy = e.clientY; };
  const up = (e) => {
    if (!on) return;
    on = false;
    const dx = e.clientX - sx, dy = e.clientY - sy;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < min) return;
    cb(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up'));
  };
  el.addEventListener('pointerdown', down);
  window.addEventListener('pointerup', up);
  return () => { el.removeEventListener('pointerdown', down); window.removeEventListener('pointerup', up); };
}

/** Arrow keys / WASD → direction (desktop). */
export function onKeys(cb) {
  const map = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down', a: 'left', d: 'right', w: 'up', s: 'down' };
  const h = (e) => { const d = map[e.key]; if (d) { e.preventDefault(); cb(d); } };
  window.addEventListener('keydown', h);
  return () => window.removeEventListener('keydown', h);
}

export function roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

// ───────── difficulty presets shown on the game page (lives / pace) ─────────
/** lives per difficulty for games that have lives (null = the game has no lives) */
export const LIVES = {
  shooter: { easy: 5, normal: 3, hard: 2 },
  racer: { easy: 5, normal: 3, hard: 2 },
};
/** what the difficulty changes, as translation keys */
export const DIFF_NOTE = {
  shooter: { easy: 'ar_dn_slow', normal: '', hard: 'ar_dn_fast' },
  racer: { easy: 'ar_dn_slow', normal: '', hard: 'ar_dn_fast' },
  basket: { easy: 'ar_dn_wide', normal: 'ar_dn_moving_late', hard: 'ar_dn_narrow' },
  snake: { easy: 'ar_dn_wrap', normal: '', hard: 'ar_dn_rocks' },
  tower: { easy: 'ar_dn_tower_e', normal: '', hard: 'ar_dn_tower_h' },
  g2048: { easy: 'ar_dn_fewer4', normal: '', hard: 'ar_dn_more4' },
  memory: { easy: 'ar_dn_peek6', normal: 'ar_dn_peek8', hard: 'ar_dn_pairs10' },
  math: { easy: 'ar_dn_math_e', normal: 'ar_dn_math_n', hard: 'ar_dn_math_h' },
  tictac: { easy: 'ar_dn_ai_e', normal: 'ar_dn_ai_n', hard: 'ar_dn_ai_h' },
};
/** the hint on the countdown screen */
export const START_HINT = {
  shooter: 'ar_h_drag', racer: 'ar_h_lanes', basket: 'ar_h_swipe_up', snake: 'ar_h_swipe', tower: 'ar_h_tap',
  g2048: 'ar_h_swipe', memory: 'ar_h_pairs', math: 'ar_h_pick', tictac: 'ar_h_tic',
};

// ───────── sound (WebAudio, synthesized — no files) ─────────
const SND_KEY = 'arcade_sound_v1';
let actx = null;
let muted = (() => { try { return localStorage.getItem(SND_KEY) === '0'; } catch (_) { return false; } })();
const lastAt = {};
export const sound = {
  get on() { return !muted; },
  toggle() { muted = !muted; try { localStorage.setItem(SND_KEY, muted ? '0' : '1'); } catch (_) { /* ignore */ } return !muted; },
  unlock() {
    try {
      if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
      if (actx.state === 'suspended') actx.resume();
    } catch (_) { actx = null; }
  },
  /** kind: shoot | boom | big | pick | hit | coin | tick | ok | bad | win | lose | drop */
  play(kind) {
    if (muted || !actx) return;
    const now = actx.currentTime;
    const gap = { shoot: 0.07, tick: 0.05 }[kind] || 0.02;
    if (lastAt[kind] && now - lastAt[kind] < gap) return;
    lastAt[kind] = now;
    try {
      const g = actx.createGain();
      g.connect(actx.destination);
      const tone = (type, f0, f1, dur, vol, delay = 0) => {
        const o = actx.createOscillator();
        const gg = actx.createGain();
        o.type = type;
        o.frequency.setValueAtTime(f0, now + delay);
        o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), now + delay + dur);
        gg.gain.setValueAtTime(vol, now + delay);
        gg.gain.exponentialRampToValueAtTime(0.0001, now + delay + dur);
        o.connect(gg); gg.connect(g);
        o.start(now + delay); o.stop(now + delay + dur + 0.02);
      };
      const noise = (dur, vol, lp = 1200) => {
        const len = Math.floor(actx.sampleRate * dur);
        const buf = actx.createBuffer(1, len, actx.sampleRate);
        const d = buf.getChannelData(0);
        for (let i = 0; i < len; i += 1) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
        const src = actx.createBufferSource();
        src.buffer = buf;
        const f = actx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = lp;
        const gg = actx.createGain(); gg.gain.value = vol;
        src.connect(f); f.connect(gg); gg.connect(g);
        src.start(now);
      };
      if (kind === 'shoot') tone('square', 900, 420, 0.06, 0.025);
      else if (kind === 'boom') noise(0.25, 0.22, 900);
      else if (kind === 'big') { noise(0.7, 0.35, 600); tone('sine', 120, 40, 0.6, 0.2); }
      else if (kind === 'pick') { tone('triangle', 660, 660, 0.08, 0.1); tone('triangle', 990, 990, 0.1, 0.1, 0.08); tone('triangle', 1320, 1320, 0.12, 0.08, 0.16); }
      else if (kind === 'hit') { tone('sawtooth', 220, 60, 0.3, 0.12); noise(0.2, 0.15, 500); }
      else if (kind === 'coin') { tone('square', 988, 988, 0.06, 0.05); tone('square', 1319, 1319, 0.12, 0.05, 0.06); }
      else if (kind === 'tick') tone('sine', 880, 880, 0.05, 0.05);
      else if (kind === 'ok') { tone('sine', 660, 990, 0.12, 0.08); }
      else if (kind === 'bad') tone('sawtooth', 200, 120, 0.18, 0.07);
      else if (kind === 'drop') tone('triangle', 300, 520, 0.08, 0.08);
      else if (kind === 'win') [523, 659, 784, 1047].forEach((f, i) => tone('triangle', f, f, 0.14, 0.08, i * 0.1));
      else if (kind === 'lose') [392, 330, 262].forEach((f, i) => tone('triangle', f, f * 0.98, 0.18, 0.08, i * 0.14));
    } catch (_) { /* never break a game because of sound */ }
  },
};
