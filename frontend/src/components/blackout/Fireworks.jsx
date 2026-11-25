/** A short burst of fireworks over one tower of the skyline (index of `of`), ~3.5 s, then it stops drawing. */
import { useEffect, useRef } from 'react';

const COLORS = ['#ffd84d', '#ffb02e', '#fff3b0', '#00f0ff', '#ff6bd6'];

export default function Fireworks({ index = 0, of = 4 }) {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current; if (!cv) return undefined;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = cv.clientWidth, H = cv.clientHeight;
    cv.width = W * dpr; cv.height = H * dpr;
    const g = cv.getContext('2d'); g.scale(dpr, dpr);
    const cx = ((index + 0.5) / of) * W;
    const parts = [];
    const burst = (x, y) => {
      const c = COLORS[Math.floor(Math.random() * COLORS.length)];
      for (let i = 0; i < 46; i++) {
        const a = (Math.PI * 2 * i) / 46, v = 1.4 + Math.random() * 2.2;
        parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: 1, c });
      }
    };
    const shots = [0, 350, 700, 1150, 1600].map((t, i) => setTimeout(() => burst(cx + (i % 2 ? 1 : -1) * (12 + i * 9), H * (0.18 + (i % 3) * 0.08)), t));
    let raf = 0; const t0 = performance.now();
    const step = (t) => {
      g.clearRect(0, 0, W, H);
      g.globalCompositeOperation = 'lighter';
      for (const p of parts) {
        if (p.life <= 0) continue;
        p.x += p.vx; p.y += p.vy; p.vy += 0.035; p.vx *= 0.985; p.vy *= 0.985; p.life -= 0.012;
        g.globalAlpha = Math.max(0, p.life);
        g.fillStyle = p.c; g.beginPath(); g.arc(p.x, p.y, 1.8, 0, 7); g.fill();
      }
      g.globalAlpha = 1;
      if (t - t0 < 3600) raf = requestAnimationFrame(step); else g.clearRect(0, 0, W, H);
    };
    raf = requestAnimationFrame(step);
    return () => { cancelAnimationFrame(raf); shots.forEach(clearTimeout); };
  }, [index, of]);
  return <canvas ref={ref} className="bo-fireworks" aria-hidden="true" />;
}
