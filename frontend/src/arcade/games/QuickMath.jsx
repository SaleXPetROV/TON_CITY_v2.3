/** «Быстрый счёт» — 60 s, 4 answer options. The questions come from the session seed (same generator as the
 *  server, which replays the answers): correct +10 (+2 per 3 in a row, max +10), mistake −5. */
import { useEffect, useMemo, useRef, useState } from 'react';
import { mathQuestions, mulberry32, sound } from '@/arcade/core';

export const MATH_SECONDS = 60;
const OPS = { '+': '+', '-': '−', '*': '×', '/': '÷' };

export default function QuickMath({ seed, difficulty, onHud, onEnd, pausedRef }) {
  const qs = useMemo(() => mathQuestions(seed || 1, difficulty, 400), [seed, difficulty]);
  const optRnd = useRef(mulberry32((seed || 1) ^ 0x5bd1e995)).current;
  const t0 = useRef(performance.now());
  const answers = useRef([]);
  const [i, setI] = useState(0);
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [flash, setFlash] = useState(null);
  const [left, setLeft] = useState(MATH_SECONDS);
  const done = useRef(false);
  const correct = useRef(0);
  const st = useRef({ score: 0 });
  st.current.score = score;

  const opts = useMemo(() => {
    const ans = qs[i].ans;
    const set = new Set([ans]);
    let guard = 0;
    while (set.size < 4 && guard < 50) {
      guard += 1;
      const d = Math.max(1, Math.round(Math.abs(ans) * 0.15)) + Math.floor(optRnd() * 6);
      const v = ans + (optRnd() < 0.5 ? -d : d);
      if (v >= 0) set.add(v);
    }
    return [...set].sort(() => optRnd() - 0.5);
  }, [i, qs, optRnd]);

  useEffect(() => {
    let last = performance.now();
    const id = setInterval(() => {
      const now = performance.now();
      if (pausedRef?.current) t0.current += now - last;          // the clock stops during the pause
      last = now;
      const l = Math.max(0, MATH_SECONDS - (now - t0.current) / 1000);
      setLeft(l);
      if (l <= 0 && !done.current) {
        done.current = true;
        clearInterval(id);
        onEnd({ score: st.current.score, stats: { answers: answers.current, correct: correct.current } });
      }
    }, 200);
    return () => clearInterval(id);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { onHud && onHud({ score, timeLeft: left, stats: { answers: answers.current, correct: correct.current } }); }, [score, Math.ceil(left)]); // eslint-disable-line react-hooks/exhaustive-deps

  const pick = (v) => {
    sound.unlock();
    if (done.current || pausedRef?.current) return;
    const t = Math.round(performance.now() - t0.current);
    const last = answers.current[answers.current.length - 1];
    if (last && t < last.t + 260) return;                      // the server ignores faster taps as impossible
    answers.current.push({ a: v, t });
    if (v === qs[i].ans) {
      const s = streak + 1;
      correct.current += 1;
      setStreak(s); setScore((x) => x + 10 + Math.min(5, Math.floor(s / 3)) * 2); setFlash('ok'); sound.play('ok');
    } else { setStreak(0); setScore((x) => Math.max(0, x - 5)); setFlash('bad'); sound.play('bad'); }
    setTimeout(() => setFlash(null), 180);
    setI((x) => x + 1);
  };

  const q = qs[i];
  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-5 p-4 select-none bg-gradient-to-b from-[#06281e] to-[#0b1020]" data-testid="arcade-math">
      <div className="w-full max-w-[360px] h-2 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-gradient-to-r from-lime-400 to-cyan-400 transition-[width] duration-200" style={{ width: `${(left / MATH_SECONDS) * 100}%` }} />
      </div>
      <div className={`w-full max-w-[360px] rounded-3xl border py-10 text-center transition-colors ${flash === 'ok' ? 'border-emerald-400 bg-emerald-500/15' : flash === 'bad' ? 'border-red-500 bg-red-500/15' : 'border-white/15 bg-white/5'}`}>
        <div className="text-5xl font-black text-white tracking-tight" data-testid="math-question">{q.a} {OPS[q.op]} {q.b}</div>
        {streak >= 3 && <div className="text-xs text-lime-300 mt-2 font-bold">🔥 ×{streak}</div>}
      </div>
      <div className="w-full max-w-[360px] grid grid-cols-2 gap-3">
        {opts.map((v) => (
          <button type="button" key={`${i}-${v}`} onClick={() => pick(v)} data-testid="math-option"
            className="h-16 rounded-2xl bg-white/10 border border-white/15 text-2xl font-bold text-white active:scale-95 active:bg-cyan-500/30 transition-all">{v}</button>
        ))}
      </div>
    </div>
  );
}
