/** Illustrations of the games for their pages (SVG, no image files). Light idle animation via CSS. */
const W = 400, H = 220;

function Stars({ n = 26, seed = 1, color = '#fff' }) {
  let s = seed;
  const r = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  return Array.from({ length: n }, (_, i) => <circle key={i} cx={r() * W} cy={r() * H} r={r() < 0.15 ? 1.6 : 0.9} fill={color} opacity={0.3 + r() * 0.6} />);
}

const ART = {
  shooter: () => (
    <>
      <defs>
        <linearGradient id="sh-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#2a1650" /><stop offset="1" stopColor="#120a2a" /></linearGradient>
        <radialGradient id="sh-pl" cx="0.35" cy="0.3"><stop offset="0" stopColor="#fb923c" /><stop offset="1" stopColor="#9a3412" /></radialGradient>
        <linearGradient id="sh-ship" x1="0" x2="1"><stop offset="0" stopColor="#d1d5db" /><stop offset="0.5" stopColor="#fff" /><stop offset="1" stopColor="#9ca3af" /></linearGradient>
      </defs>
      <rect width={W} height={H} fill="url(#sh-bg)" />
      <circle cx="120" cy="110" r="90" fill="#7c3aed" opacity="0.18" />
      <Stars n={30} seed={3} />
      <circle cx="40" cy="250" r="110" fill="url(#sh-pl)" />
      <ellipse cx="60" cy="210" rx="150" ry="22" fill="none" stroke="#fbbf24" strokeOpacity="0.6" strokeWidth="5" transform="rotate(-8 60 210)" />
      <g className="arc-float"><path d="M128 12 l14 26 l-14 -7 l-14 7z" fill="#ec4899" /><circle cx="128" cy="26" r="4" fill="#fde68a" /></g>
      <g className="arc-float2"><path d="M300 8 l16 30 l-16 -8 l-16 8z" fill="#ec4899" /><circle cx="300" cy="24" r="4.5" fill="#fde68a" /></g>
      <g className="arc-float"><path d="M220 52 l26 50 l-26 -14 l-26 14z" fill="#7c3aed" /><circle cx="220" cy="80" r="7" fill="#fff" /></g>
      <rect x="164" y="16" width="5" height="22" rx="2.5" fill="#fbbf24" opacity="0.7" /><rect x="268" y="66" width="5" height="26" rx="2.5" fill="#fbbf24" />
      <g><circle cx="205" cy="128" r="20" fill="#1c1300" stroke="#fbbf24" strokeWidth="3" /><text x="205" y="134" textAnchor="middle" fontSize="16" fontWeight="900" fill="#fbbf24">3x</text></g>
      <g transform="translate(300 150)"><g className="arc-bob">
        <path d="M-6 52 q6 18 12 0z" fill="#fb923c" />
        <path d="M0 -40 q14 22 14 60 l18 22 l-16 4 l-2 -6 l-28 0 l-2 6 l-16 -4 l18 -22 q0 -38 14 -60z" fill="url(#sh-ship)" />
        <ellipse cx="0" cy="-4" rx="6" ry="13" fill="#f97316" />
        <rect x="-35" y="42" width="5" height="12" rx="2" fill="#f59e0b" /><rect x="30" y="42" width="5" height="12" rx="2" fill="#f59e0b" />
      </g></g>
    </>
  ),
  racer: () => (
    <>
      <defs><linearGradient id="rc-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#3b0764" /><stop offset="1" stopColor="#12002a" /></linearGradient></defs>
      <rect width={W} height={H} fill="url(#rc-bg)" />
      <Stars n={18} seed={7} color="#f0abfc" />
      <path d="M150 0 L250 0 L360 220 L40 220z" fill="#1a1530" />
      <path d="M150 0 L40 220 M250 0 L360 220" stroke="#e879f9" strokeWidth="4" />
      <g className="arc-road">{[0, 1, 2, 3, 4].map((i) => <rect key={i} x="197" y={i * 50 - 20} width="6" height="26" fill="#ffffff66" />)}</g>
      <g transform="translate(140 60)"><rect x="-16" y="-26" width="32" height="52" rx="9" fill="#f43f5e" /><rect x="-12" y="-14" width="24" height="10" rx="3" fill="#0b1020" /></g>
      <g transform="translate(262 110)"><rect x="-18" y="-30" width="36" height="58" rx="10" fill="#f59e0b" /><rect x="-13" y="-17" width="26" height="11" rx="3" fill="#0b1020" /></g>
      <circle cx="245" cy="30" r="10" fill="#facc15" /><circle cx="160" cy="138" r="10" fill="#facc15" className="arc-float" />
      <g transform="translate(195 178)"><g className="arc-bob"><rect x="-22" y="-36" width="44" height="70" rx="12" fill="#22d3ee" /><rect x="-16" y="-22" width="32" height="13" rx="4" fill="#0b1020" /><rect x="-17" y="-36" width="9" height="3" fill="#fef9c3" /><rect x="8" y="-36" width="9" height="3" fill="#fef9c3" /></g></g>
    </>
  ),
  basket: () => (
    <>
      <defs><linearGradient id="bk-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1f1235" /><stop offset="0.65" stopColor="#3b1d4a" /><stop offset="1" stopColor="#7c2d12" /></linearGradient></defs>
      <rect width={W} height={H} fill="url(#bk-bg)" />
      <rect x="0" y="190" width={W} height="30" fill="#9a3412" />
      <rect x="150" y="20" width="100" height="66" fill="#f8fafc" opacity="0.92" /><rect x="180" y="40" width="40" height="30" fill="none" stroke="#ef4444" strokeWidth="4" />
      <ellipse cx="200" cy="86" rx="34" ry="6" fill="none" stroke="#f97316" strokeWidth="5" />
      {[0, 1, 2, 3, 4, 5].map((i) => <line key={i} x1={168 + i * 13} y1="88" x2={180 + i * 8} y2="122" stroke="#e2e8f0" strokeOpacity="0.7" strokeWidth="1.5" />)}
      <path d="M90 190 Q140 -10 200 70" fill="none" stroke="#fde68a" strokeDasharray="4 8" strokeWidth="2.5" opacity="0.6" />
      <g transform="translate(116 120)"><g className="arc-bob"><circle r="20" fill="#ea580c" /><path d="M-20 0 H20 M0 -20 V20" stroke="#431407" strokeWidth="2" /><path d="M-14 -14 Q0 0 -14 14 M14 -14 Q0 0 14 14" stroke="#431407" strokeWidth="2" fill="none" /></g></g>
      <text x="290" y="70" fontSize="30" fontWeight="900" fill="#fde047">+3</text>
    </>
  ),
  snake: () => (
    <>
      <rect width={W} height={H} fill="#04150f" />
      {Array.from({ length: 11 }, (_, y) => Array.from({ length: 20 }, (__, x) => <rect key={`${x}-${y}`} x={x * 20} y={y * 20} width="20" height="20" fill={(x + y) % 2 ? '#0a2a1e' : '#0c3324'} />))}
      <g className="arc-bob">
        {[[5, 6], [6, 6], [7, 6], [8, 6], [8, 5], [8, 4], [9, 4], [10, 4], [11, 4], [12, 4], [12, 5], [12, 6], [13, 6]].map(([x, y], i, a) => (
          <rect key={i} x={x * 20 + 2} y={y * 20 + 2} width="16" height="16" rx="6" fill={`hsl(${150 - (a.length - i) * 3},80%,${40 + i * 2}%)`} />
        ))}
        <circle cx="275" cy="128" r="2.5" fill="#04150f" /><circle cx="275" cy="136" r="2.5" fill="#04150f" />
      </g>
      <text x="330" y="138" fontSize="22" className="arc-float">🍎</text>
      <text x="90" y="58" fontSize="20">🍎</text>
    </>
  ),
  tower: () => (
    <>
      <defs><linearGradient id="tw-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#0c1a3a" /><stop offset="1" stopColor="#1e3a8a" /></linearGradient></defs>
      <rect width={W} height={H} fill="url(#tw-bg)" />
      <Stars n={20} seed={11} />
      <rect x="0" y="206" width={W} height="14" fill="#0f172a" />
      {[0, 1, 2, 3, 4, 5].map((i) => {
        const w = 150 - i * 10, x = 125 + i * 3;
        return <g key={i}><rect x={x} y={180 - i * 26} width={w} height="24" fill={`hsl(${195 + i * 14},70%,52%)`} /><rect x={x} y={180 - i * 26} width={w} height="4" fill={`hsl(${195 + i * 14},80%,72%)`} />
          {Array.from({ length: Math.floor(w / 16) }, (_, k) => <rect key={k} x={x + 6 + k * 16} y={189 - i * 26} width="8" height="9" fill="#0b102099" />)}</g>;
      })}
      <g className="arc-slide"><rect x="150" y="14" width="96" height="24" fill="hsl(300,70%,55%)" /><rect x="150" y="14" width="96" height="4" fill="hsl(300,80%,75%)" /></g>
      <text x="290" y="70" fontSize="16" fontWeight="900" fill="#fde047">PERFECT</text>
    </>
  ),
  g2048: () => (
    <>
      <rect width={W} height={H} fill="#1a1206" />
      <g transform="translate(110 14)">
        <rect width="192" height="192" rx="14" fill="#2b2113" />
        {[[2, 4, 8, 16], [0, 32, 64, 0], [128, 256, 0, 2], [0, 512, 2048, 4]].map((row, y) => row.map((v, x) => {
          const c = { 2: '#1e293b', 4: '#334155', 8: '#f59e0b', 16: '#f97316', 32: '#ef4444', 64: '#dc2626', 128: '#06b6d4', 256: '#0ea5e9', 512: '#6366f1', 2048: '#facc15' }[v] || '#3b2f1d';
          return <g key={`${x}${y}`}><rect x={8 + x * 46} y={8 + y * 46} width="40" height="40" rx="8" fill={c} />{v ? <text x={28 + x * 46} y={34 + y * 46} textAnchor="middle" fontSize={v >= 1000 ? 12 : 16} fontWeight="900" fill={v === 2048 ? '#0b1020' : '#fff'}>{v}</text> : null}</g>;
        }))}
      </g>
      <text x="330" y="60" fontSize="28" className="arc-float">✨</text>
    </>
  ),
  memory: () => (
    <>
      <defs><linearGradient id="mm-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#4a0d35" /><stop offset="1" stopColor="#1a0614" /></linearGradient></defs>
      <rect width={W} height={H} fill="url(#mm-bg)" />
      {Array.from({ length: 8 }, (_, i) => {
        const x = 60 + (i % 4) * 74, y = 22 + Math.floor(i / 4) * 92;
        const open = [1, 6].includes(i) ? '💎' : i === 3 ? '🚀' : null;
        return <g key={i} className={i === 1 || i === 6 ? 'arc-float' : ''}><rect x={x} y={y} width="62" height="82" rx="10" fill={open ? '#ffffff22' : '#db2777'} stroke={open ? '#34d399' : '#f9a8d4'} strokeOpacity="0.6" />
          {open ? <text x={x + 31} y={y + 52} textAnchor="middle" fontSize="30">{open}</text> : <text x={x + 31} y={y + 50} textAnchor="middle" fontSize="22" fontWeight="900" fill="#ffffff55">G</text>}</g>;
      })}
    </>
  ),
  math: () => (
    <>
      <defs><linearGradient id="mt-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#064e3b" /><stop offset="1" stopColor="#06201a" /></linearGradient></defs>
      <rect width={W} height={H} fill="url(#mt-bg)" />
      <rect x="90" y="22" width="220" height="70" rx="18" fill="#ffffff14" stroke="#ffffff33" />
      <text x="200" y="70" textAnchor="middle" fontSize="36" fontWeight="900" fill="#fff">12 × 7</text>
      {[[84, 118], [87, 206], [74, 118], [94, 206]].map(([v, x], i) => <g key={i}><rect x={x} y={110 + (i > 1 ? 50 : 0)} width="80" height="40" rx="12" fill={v === 84 ? '#10b98155' : '#ffffff18'} stroke={v === 84 ? '#34d399' : '#ffffff30'} /><text x={x + 40} y={137 + (i > 1 ? 50 : 0)} textAnchor="middle" fontSize="20" fontWeight="800" fill="#fff">{v}</text></g>)}
      <text x="40" y="60" fontSize="28" fill="#a3e635" className="arc-float">÷</text><text x="340" y="150" fontSize="30" fill="#67e8f9" className="arc-float2">+</text>
    </>
  ),
  tictac: () => (
    <>
      <defs><linearGradient id="tt-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#2e1065" /><stop offset="1" stopColor="#12062a" /></linearGradient></defs>
      <rect width={W} height={H} fill="url(#tt-bg)" />
      <g transform="translate(125 14)">
        {[0, 1, 2].map((y) => [0, 1, 2].map((x) => <rect key={`${x}${y}`} x={x * 52} y={y * 64} width="48" height="60" rx="10" fill="#ffffff10" stroke="#ffffff22" />))}
        {[[0, 0, 'x'], [1, 1, 'x'], [2, 0, 'o'], [0, 2, 'o'], [2, 2, 'x']].map(([x, y, v], i) => v === 'x'
          ? <text key={i} x={x * 52 + 24} y={y * 64 + 44} textAnchor="middle" fontSize="34" fontWeight="900" fill="#67e8f9">✕</text>
          : <circle key={i} cx={x * 52 + 24} cy={y * 64 + 30} r="13" fill="none" stroke="#f472b6" strokeWidth="5" />)}
        <line x1="10" y1="12" x2="140" y2="178" stroke="#c4b5fd" strokeWidth="5" strokeLinecap="round" opacity="0.8" className="arc-draw" />
      </g>
    </>
  ),
};

export default function GameArt({ game, className = '' }) {
  const A = ART[game] || ART.shooter;
  return (
    <div className={`relative overflow-hidden rounded-3xl border border-white/10 shadow-xl ${className}`}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto block" preserveAspectRatio="xMidYMid slice"><A /></svg>
      <style>{`
        @keyframes arcFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(5px)}}
        @keyframes arcBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
        @keyframes arcSlide{0%,100%{transform:translateX(-40px)}50%{transform:translateX(40px)}}
        @keyframes arcRoad{from{transform:translateY(0)}to{transform:translateY(50px)}}
        .arc-float{animation:arcFloat 3s ease-in-out infinite}.arc-float2{animation:arcFloat 3.6s ease-in-out infinite reverse}
        .arc-bob{animation:arcBob 2.4s ease-in-out infinite;transform-box:fill-box}
        .arc-slide{animation:arcSlide 2.2s ease-in-out infinite}.arc-road{animation:arcRoad .6s linear infinite}
      `}</style>
    </div>
  );
}
