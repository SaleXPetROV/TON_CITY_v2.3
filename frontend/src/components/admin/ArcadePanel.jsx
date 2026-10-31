/**
 * ArcadePanel — admin «Аркада» (backend/arcade.py).
 * Left: on/off (players see it), XP limit per day, how the reward is split between the ads, XP by difficulty,
 * per game: on/off, attempts per day, max XP per game, score for the maximum; today's numbers.
 * Right: a phone frame with the real player screens in preview mode — the admin can play every game:
 * no attempts are used and no XP is credited; the ads of the reward can be watched for real or simulated.
 */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Gamepad2, RefreshCw, Smartphone } from 'lucide-react';
import ArcadeApp from '@/arcade/ArcadeApp';
import MinigamesPanel from '@/components/admin/MinigamesPanel';
import { GAME_ICON } from '@/arcade/core';
import XpStatsPanel from '@/components/admin/arcade/XpStatsPanel';
import GameNftsPanel from '@/components/admin/arcade/GameNftsPanel';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/admin`;
const NAMES = {
  shooter: 'Небесный патруль (шутер, 4 баффа)', racer: 'Ночная трасса (гонка)', basket: 'Уличный баскетбол', snake: 'Змейка',
  tower: 'Небоскрёб (башня)', g2048: '2048', memory: 'Память (пары)', math: 'Быстрый счёт', tictac: 'Крестики-нолики',
};
const DIFF_RU = { easy: 'Легко', normal: 'Нормально', hard: 'Сложно' };
// what the built-in difficulty changes in every game (on top of the admin's speed / lives)
const DIFF_HINT = {
  shooter: 'Легко: 5 жизней, враги медленнее, реже стреляют. Сложно: 2 жизни, быстрые волны, плотный ответный огонь. Каждая волна заканчивается Флагманом.',
  racer: 'Легко: 5 жизней, медленный старт и разгон, больше места между машинами. Сложно: 2 жизни, быстрый старт, плотный трафик.',
  basket: 'Легко: широкое кольцо стоит на месте. Нормально: кольцо начинает двигаться с 15-й секунды. Сложно: узкое кольцо всё время быстро движется.',
  snake: 'Легко: медленно, змейка проходит сквозь стены. Нормально: стены убивают. Сложно: быстро, стены + камни на поле.',
  tower: 'Легко: этаж едет медленно, «идеально» засчитывается с допуском 7 px. Сложно: быстро, допуск 4 px, ускорение с каждым этажом сильнее.',
  g2048: 'Легко: новые плитки «4» в 5% случаев. Нормально: 10%. Сложно: 30% — поле забивается быстрее.',
  memory: 'Без лимита очков, ограничение — время. Легко: 6 пар, 90 с, каждое новое поле показано 2 с. Нормально: 8 пар, 75 с, показ 1 с. Сложно: 10 пар, 60 с, без подсказки. Собранное поле сразу раздаётся заново.',
  math: 'Легко: + и − до 20. Нормально: + − × до 50. Сложно: + − × ÷ до 99. Всегда 60 секунд.',
  tictac: 'Раунды без ограничения, пока игрок не проиграет 3 раза или не выйдут 120 с. Легко: компьютер часто ходит случайно. Нормально: выигрывает и блокирует. Сложно: играет идеально (минимакс) — возможна только ничья.',
};

function Kpi({ label, value }) {
  return (
    <div className="rounded-xl bg-white/5 border border-white/10 p-3">
      <div className="text-[11px] uppercase tracking-wide text-text-muted">{label}</div>
      <div className="text-xl font-bold mt-1 text-white">{value}</div>
    </div>
  );
}

// ONE admin section for all games: the Arcade + «Сортировщик» + the mini-games rewards (no promotion)
const SECTIONS = [
  ['games', '🎮 Игры и XP'], ['xp', '📈 XP игроков'], ['game_nfts', '💎 NFT по играм'], ['campaign', '🏆 Рейтинг недели, призы, сундук'], ['rewards', '🎁 Награды'], ['containers', '📦 Сундуки'],
  ['boosters', '⚡ Усилители'], ['nft', '💎 NFT'], ['puzzles', '🧩 Пазлы'], ['players', '👤 Игроки'], ['stats', '📊 Статистика'], ['anomalies', '⚠️ Аномалии'],
];

export default function ArcadePanel({ token }) {
  const [section, setSection] = useState('games');
  return (
    <div className="space-y-4" data-testid="arcade-admin-root">
      <div className="flex flex-wrap gap-1.5" data-testid="arcade-admin-sections">
        {SECTIONS.map(([id, label]) => (
          <button key={id} type="button" onClick={() => setSection(id)} data-testid={`arcade-admin-sec-${id}`}
            className={`px-3 py-1.5 rounded-lg text-sm border ${section === id ? 'border-fuchsia-400/60 bg-fuchsia-500/15 text-fuchsia-100' : 'border-white/10 bg-white/5 text-white/70'}`}>{label}</button>
        ))}
      </div>
      {section === 'games' ? <ArcadeGames token={token} />
        : section === 'xp' ? <XpStatsPanel token={token} />
          : section === 'game_nfts' ? <GameNftsPanel token={token} />
            : <MinigamesPanel token={token} tab={section} hideNav />}
    </div>
  );
}

function ArcadeGames({ token }) {
  const [cfg, setCfg] = useState(null);
  const [f, setF] = useState(null);
  const [ads, setAds] = useState(null);
  const [busy, setBusy] = useState(false);
  const [frameKey, setFrameKey] = useState(0);
  const headers = { headers: { Authorization: `Bearer ${token}` } };

  const load = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([axios.get(`${API}/arcade`, headers), axios.get(`${API}/ads`, headers).catch(() => ({ data: null }))]);
      setCfg(a.data);
      setF((x) => x || JSON.parse(JSON.stringify(a.data)));
      setAds(b.data);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Не удалось загрузить Аркаду'); }
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true);
    try {
      const body = {
        enabled: !!f.enabled, daily_xp_cap: Number(f.daily_xp_cap), ads_per_reward: Number(f.ads_per_reward),
        ad_shares_pct: f.ad_shares_pct.slice(0, Number(f.ads_per_reward)).map(Number), reward_ttl_hours: Number(f.reward_ttl_hours), one_ad_max_xp: Number(f.one_ad_max_xp),
        games: Object.fromEntries(Object.entries(f.games).map(([g, v]) => [g, {
          enabled: !!v.enabled, free_play: !!v.free_play, attempts_max: Number(v.attempts_max), regen_minutes: Number(v.regen_minutes),
          target_score: Number(v.target_score),
          diffs: Object.fromEntries(Object.entries(v.diffs).map(([d, x]) => [d, { xp: Number(x.xp), speed: Number(x.speed), ...(x.lives !== undefined ? { lives: Number(x.lives) } : {}) }])),
        }])),
      };
      const r = await axios.put(`${API}/arcade`, body, headers);
      setCfg(r.data); setF(JSON.parse(JSON.stringify(r.data)));
      setFrameKey((k) => k + 1);
      toast.success('Игры сохранены');
    } catch (e) { toast.error(e?.response?.data?.detail || 'Ошибка сохранения'); } finally { setBusy(false); }
  };

  if (!cfg || !f) return <div className="text-sm text-text-muted">Загрузка…</div>;
  const setG = (g, patch) => setF((s) => ({ ...s, games: { ...s.games, [g]: { ...s.games[g], ...patch } } }));
  const n = Math.max(1, Math.min(5, Number(f.ads_per_reward) || 1));
  const shares = Array.from({ length: n }, (_, i) => f.ad_shares_pct[i] ?? 0);
  const sum = shares.reduce((a, b) => a + Number(b || 0), 0);
  const adsOn = ads ? !!(ads.enabled && ads.monetag_zone_id) : null;
  const sel = 'h-8 rounded bg-black/40 border border-white/10 text-xs text-white px-1';

  return (
    <div className="space-y-4" data-testid="arcade-admin-panel">
      <div className="flex flex-wrap items-center gap-3">
        <Gamepad2 className="w-5 h-5 text-fuchsia-300" />
        <span className="font-bold text-white">Игры</span>
        <label className="flex items-center gap-2 text-sm" data-testid="games-main-switch"><Switch checked={!!f.enabled} onCheckedChange={(v) => setF((s) => ({ ...s, enabled: v }))} />
          {f.enabled ? 'Включены — игроки видят кнопку «Игры» на «Бизнесах» и все игры' : 'Выключены — кнопки «Игры» нет, игроки игр не видят (админ — превью)'}</label>
        <div className="flex gap-1 ml-auto">
          <Button size="sm" variant="outline" onClick={() => { setF(null); load(); setFrameKey((k) => k + 1); }}><RefreshCw className="w-4 h-4" /></Button>
          <Button size="sm" onClick={save} disabled={busy} className="bg-fuchsia-500 text-white hover:bg-fuchsia-400">Сохранить</Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Kpi label="Наград сегодня" value={cfg.today.rewards} />
        <Kpi label="XP заработано / зачислено" value={`${cfg.today.xp_total} / ${cfg.today.xp_credited}`} />
        <Kpi label="Подтверждённых реклам" value={cfg.today.ads} />
        <Kpi label="Показов рекламы (отчёт приложения)" value={cfg.today.ad_views} />
      </div>

      <div className="grid xl:grid-cols-[1fr_420px] gap-4 items-start">
        <div className="space-y-4 min-w-0">
          <Card className="bg-white/[0.03] border-white/10">
            <CardHeader className="pb-2"><CardTitle className="text-sm text-white">Награда и реклама</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className={`rounded-lg p-2.5 border ${adsOn === false ? 'border-amber-500/40 bg-amber-500/10 text-amber-100' : 'border-white/10 bg-white/5 text-white/80'}`}>
                {adsOn === false
                  ? 'Реклама Monetag сейчас выключена («Данные» → «Monetag») — XP за игру зачисляется сразу целиком. Включите рекламу, чтобы награда открывалась просмотрами.'
                  : 'После каждой игры XP не начисляется сразу: игрок смотрит рекламу (если XP за игру мало — одну рекламу на всё, если много — цепочку). Пока реклама за прошлую игру не просмотрена, новую игру начать нельзя. Каждая подтверждённая реклама открывает свою часть XP, она сразу уходит в City Pass. Подтверждение — как у ежедневного бонуса: по постбеку Monetag (если включено «проверять постбек») или по отчёту приложения.'}
              </div>
              <div className="grid sm:grid-cols-4 gap-3">
                <label className="block">Реклам на одну награду (если XP много)
                  <select value={n} onChange={(e) => setF((s) => ({ ...s, ads_per_reward: Number(e.target.value) }))} className={`${sel} w-full mt-1`}>
                    {[1, 2, 3, 4, 5].map((x) => <option key={x} value={x}>{x}</option>)}
                  </select>
                </label>
                <label className="block">Лимит XP Аркады в сутки на игрока (0 — без лимита)
                  <Input type="number" min="0" value={f.daily_xp_cap} onChange={(e) => setF((s) => ({ ...s, daily_xp_cap: e.target.value }))} className="h-8 mt-1 bg-black/40 border-white/10 text-xs" />
                </label>
                <label className="block">Мало XP — одна реклама: до скольких XP (0 — всегда цепочка)
                  <Input type="number" min="0" value={f.one_ad_max_xp} onChange={(e) => setF((s) => ({ ...s, one_ad_max_xp: e.target.value }))} className="h-8 mt-1 bg-black/40 border-white/10 text-xs" />
                </label>
                <label className="block">Незабранный остаток хранится, часов
                  <Input type="number" min="1" max="168" value={f.reward_ttl_hours} onChange={(e) => setF((s) => ({ ...s, reward_ttl_hours: e.target.value }))} className="h-8 mt-1 bg-black/40 border-white/10 text-xs" />
                </label>
              </div>
              <div>
                <div className="mb-1">Доля XP за каждую рекламу, % (в сумме 100; по умолчанию 50 / 25 / 25 = 2/4 + 1/4 + 1/4)</div>
                <div className="flex flex-wrap items-center gap-2">
                  {shares.map((v, i) => (
                    <label key={i} className="flex items-center gap-1">{i + 1}-я
                      <Input type="number" min="0" max="100" value={v} onChange={(e) => setF((s) => { const a = [...s.ad_shares_pct]; a[i] = e.target.value; return { ...s, ad_shares_pct: a }; })} className="h-8 w-20 bg-black/40 border-white/10 text-xs" />
                    </label>
                  ))}
                  <span className={sum === 100 ? 'text-emerald-300' : 'text-amber-300'}>= {sum}%{sum !== 100 ? ' (при сохранении приведётся к 100%)' : ''}</span>
                </div>
                <div className="text-[11px] text-text-muted mt-1">Пример для игры на 20 XP: {shares.map((p, i) => `${i + 1}-я реклама → ${Math.floor(20 * shares.slice(0, i + 1).reduce((a, b) => a + Number(b || 0), 0) / Math.max(1, sum))} XP`).join(' · ')}.</div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/[0.03] border-white/10">
            <CardHeader className="pb-2"><CardTitle className="text-sm text-white">Игры — настройки каждой игры</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="text-[11px] text-text-muted space-y-1">
                <div><b className="text-white/80">Попытки с наградой</b> — максимум; тратится одна при старте игры, затем восстанавливается по одной через «восстановление, мин» (0 — все сразу в 00:00 МСК). Founder Pass может давать «+ попыток» и «+XP %».</div>
                <div><b className="text-white/80">Игра без награды</b> — когда попытки с наградой закончились, игрок может играть «просто так»: XP нет, рекорд идёт в топ-5.</div>
                <div><b className="text-white/80">По сложностям</b>: XP — максимум XP за игру; он даётся при счёте «очков для максимума XP» (меньше счёт — меньше XP, больше — всё равно максимум). Сами игровые очки без предела: шутер, гонка, змейка, небоскрёб и 2048 бесконечные, «Память» ограничена временем (поле раздаётся заново), «Крестики-нолики» — тремя поражениями и 120 секундами. Скорость, % — темп игры поверх встроенной сложности (100 — как задумано); жизни — для шутера и гонки.</div>
              </div>
              <div className="grid md:grid-cols-2 gap-3">
                {cfg.games_list.map((g) => {
                  const v = f.games[g];
                  const st = cfg.stats[g] || {};
                  const setD = (d, patch) => setG(g, { diffs: { ...v.diffs, [d]: { ...v.diffs[d], ...patch } } });
                  return (
                    <div key={g} className={`rounded-xl border p-3 text-xs space-y-2 ${v.enabled ? 'border-fuchsia-400/30 bg-fuchsia-500/[0.04]' : 'border-white/10 bg-white/[0.02] opacity-70'}`} data-testid={`arcade-admin-row-${g}`}>
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{GAME_ICON[g]}</span>
                        <span className="font-bold text-white flex-1">{NAMES[g]}</span>
                        <label className="flex items-center gap-1.5">{v.enabled ? 'вкл.' : 'выкл.'}<Switch checked={!!v.enabled} onCheckedChange={(x) => setG(g, { enabled: x })} /></label>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <label className="block">Попыток с наградой
                          <Input type="number" min="0" value={v.attempts_max} onChange={(e) => setG(g, { attempts_max: e.target.value })} className="h-8 mt-0.5 bg-black/40 border-white/10 text-xs" />
                        </label>
                        <label className="block">Восстановление, мин
                          <Input type="number" min="0" value={v.regen_minutes} onChange={(e) => setG(g, { regen_minutes: e.target.value })} className="h-8 mt-0.5 bg-black/40 border-white/10 text-xs" />
                        </label>
                        <label className="block">Очков для максимума XP
                          <Input type="number" min="1" value={v.target_score} onChange={(e) => setG(g, { target_score: e.target.value })} className="h-8 mt-0.5 bg-black/40 border-white/10 text-xs" />
                        </label>
                      </div>
                      <label className="flex items-center justify-between gap-2"><span>Игра без награды после попыток (рекорды)</span><Switch checked={!!v.free_play} onCheckedChange={(x) => setG(g, { free_play: x })} /></label>
                      <table className="w-full">
                        <thead className="text-text-muted"><tr className="text-left"><th className="py-0.5">Сложность</th><th>Макс. XP</th><th>Скорость, %</th>{v.diffs.easy.lives !== undefined && <th>Жизни</th>}</tr></thead>
                        <tbody>
                          {Object.keys(DIFF_RU).map((d) => (
                            <tr key={d}>
                              <td className="py-0.5 text-white/80">{DIFF_RU[d]}</td>
                              <td><Input type="number" min="0" value={v.diffs[d].xp} onChange={(e) => setD(d, { xp: e.target.value })} className="h-7 w-16 bg-black/40 border-white/10 text-xs" /></td>
                              <td><Input type="number" min="50" max="200" value={v.diffs[d].speed} onChange={(e) => setD(d, { speed: e.target.value })} className="h-7 w-16 bg-black/40 border-white/10 text-xs" /></td>
                              {v.diffs[d].lives !== undefined && <td><Input type="number" min="1" max="9" value={v.diffs[d].lives} onChange={(e) => setD(d, { lives: e.target.value })} className="h-7 w-14 bg-black/40 border-white/10 text-xs" /></td>}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="text-[11px] text-text-muted">{DIFF_HINT[g]}</div>
                      <div className="text-[11px] text-white/70">Сегодня: игр {st.games || 0} · игроков {st.players || 0} · отклонено <span className={st.rejected ? 'text-rose-300' : ''}>{st.rejected || 0}</span></div>
                    </div>
                  );
                })}
              </div>
              <div className="text-[11px] text-text-muted">Защита от накруток: счёт сверяется со временем игры по часам сервера и с максимальной скоростью набора очков (с учётом «скорости»); «Быстрый счёт» и «Крестики-нолики» сервер переигрывает сам, «Память», «Змейка», «Небоскрёб» считаются сервером по статистике. «Отклонено» — результаты, не прошедшие проверку.</div>
            </CardContent>
          </Card>
        </div>

        <div className="xl:sticky xl:top-4">
          <div className="flex items-center gap-2 text-sm text-white mb-2"><Smartphone className="w-4 h-4 text-cyan-300" />Как увидит игрок — можно играть</div>
          <div className="mx-auto w-[390px] max-w-full h-[780px] rounded-[42px] border-[10px] border-[#1c1f2b] bg-[#05060A] shadow-2xl shadow-black/60 overflow-hidden relative" data-testid="arcade-phone-frame">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-28 h-5 bg-[#1c1f2b] rounded-b-2xl z-[5]" />
            <div className="absolute inset-0 overflow-y-auto pt-7 px-3" style={{ contain: 'layout paint' }}>
              <ArcadeApp key={frameKey} preview embedded />
            </div>
          </div>
          <div className="text-[11px] text-text-muted mt-2 text-center">Превью показывает сохранённые настройки. Попытки не тратятся, XP не начисляются; рекламу можно посмотреть по-настоящему или имитировать.</div>
        </div>
      </div>
    </div>
  );
}
