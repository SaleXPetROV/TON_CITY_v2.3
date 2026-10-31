/** Admin «Игры (Аркада)» → rating of the week (prizes per game), «Сортировщик», chests, rewards, NFT, puzzles, players,
 *  statistics, anomalies (the sections are chosen in ArcadePanel). No promotion any more. Only Russian. */
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { useApi, Card, Field, Modal, Stat, inp, inpS, err, fmt, dt, ANOMALY, MG_GAMES, mgGameName, DEFAULT_ARCADE_PRIZES } from './minigames/mgAdminKit';
import { RewardsTab, ContainersTab, BoostersTab, NftTab, PuzzlesTab, PlayersTab } from './minigames/CatalogTabs';

const PRIZE_KINDS = { city: '$CITY на бонусный баланс', nft: 'NFT со склада', container: 'Сундук', booster: 'Усилитель', reward: 'Награда' };

/** Rows «места с–по → приз» (the Sorter's list of leaders and every Arcade game's own list) */
function PrizeRows({ prizes, onChange, refs }) {
  const setPrize = (i, k, v) => onChange(prizes.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  return (
    <>
      {prizes.map((p, i) => (
        <div key={i} className="flex flex-wrap items-center gap-2 text-xs" data-testid="mg-prize-row">
          <span className="text-text-muted">места</span>
          <input type="number" className={`${inpS} w-16`} value={p.from} onChange={(e) => setPrize(i, 'from', e.target.value)} />
          <span className="text-text-muted">—</span>
          <input type="number" className={`${inpS} w-16`} value={p.to} onChange={(e) => setPrize(i, 'to', e.target.value)} />
          <select className={`${inpS} w-48`} value={p.kind || 'city'} onChange={(e) => setPrize(i, 'kind', e.target.value)}>{Object.entries(PRIZE_KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          {(p.kind || 'city') === 'city'
            ? (<><input type="number" className={`${inpS} w-28`} value={p.city ?? 0} onChange={(e) => setPrize(i, 'city', e.target.value)} /><span className="text-text-muted">$CITY</span></>)
            : (<select className={`${inpS} w-52`} value={p.ref_id || ''} onChange={(e) => setPrize(i, 'ref_id', e.target.value)}><option value="">—</option>
                {(refs[p.kind] || []).map((x) => <option key={x.id} value={x.id}>{x.name}{p.kind === 'nft' ? ` · тираж ${x.supply_total}` : ''}</option>)}</select>)}
          <Button size="sm" variant="outline" className="h-7 px-2" onClick={() => onChange(prizes.filter((_, j) => j !== i))}>✕</Button>
        </div>
      ))}
      <Button size="sm" variant="outline" onClick={() => onChange([...prizes, { from: (prizes[prizes.length - 1]?.to || 0) + 1, to: (prizes[prizes.length - 1]?.to || 0) + 1, kind: 'city', city: 0 }])}>+ Строка призов</Button>
    </>
  );
}

function CampaignTab({ api }) {
  const [arcGame, setArcGame] = useState('shooter');
  const [cfg, setCfg] = useState(null);
  const [st, setSt] = useState(null);
  const [refs, setRefs] = useState({ container: [], booster: [], nft: [], reward: [] });
  const [preview, setPreview] = useState(null);
  const load = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([api.get('/admin/minigames/event'), api.get('/admin/minigames/stats')]);
      setCfg(c); setSt(s);
    } catch (e) { err(e); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    load();
    Promise.all([api.get('/admin/minigames/containers'), api.get('/admin/minigames/boosters'), api.get('/admin/minigames/nfts'), api.get('/admin/minigames/rewards')])
      .then(([c, b, n, r]) => setRefs({ container: c.containers, booster: b, nft: n.nfts, reward: r })).catch(() => {});
  }, [load]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async () => {
    try {
      const body = { ...cfg };
      ['prizes', 'finalized', 'starts_at', 'ends_at', 'event_id', 'enabled', 'title'].forEach((k) => delete body[k]);
      setCfg(await api.put('/admin/minigames/event', body)); toast.success('Сохранено'); load();
    } catch (e) { err(e); }
  };

  if (!cfg || !st) return <div className="text-sm text-text-muted">Загрузка…</div>;
  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }));
  const prizes = cfg.leaderboard_prizes || [];
  const arcPrizes = (cfg.arcade_prizes || {})[arcGame] || DEFAULT_ARCADE_PRIZES;
  const arcChest = cfg.arcade_chest_score || {};
  const fmtDate = (iso) => { try { return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (_) { return iso; } };
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Stat label="«Сортировщик»: партий за неделю" value={st.plays} /><Stat label="Игроков за неделю" value={st.players} /><Stat label="Отклонено (подозрительно)" value={st.rejected} />
        <Stat label="★★★" value={st.stars['3']} /><Stat label="Лучшая партия" value={st.best_game ? `${fmt(st.best_game.points)} · @${st.best_game.username || '—'}` : '—'} />
      </div>
      <Card title="Рейтинг недели">
        <div className="text-[12px] text-text-muted leading-relaxed">
          Акций нет — игры работают всегда, пока включён главный переключатель «Игры» (раздел «🎮 Игры и XP»). У каждой игры свой рейтинг недели:
          очки каждой партии идут в рейтинг этой игры. Неделя — с понедельника 00:00 по воскресенье 23:59 МСК. В понедельник в 00:00 МСК призы
          раздаются автоматически по местам (один раз), и новая неделя начинается с нуля. Рекорды игроков не обнуляются.
        </div>
        <Button size="sm" variant="outline" onClick={async () => { try { setPreview(await api.get('/admin/minigames/campaign/preview')); } catch (e) { err(e); } }} data-testid="mg-week-preview">Кто получит призы, если неделя закончится сейчас</Button>
      </Card>
      <Card title="📦 «Сортировщик»">
        <label className="flex items-center gap-2 text-sm text-white"><input type="checkbox" checked={cfg.sorter_enabled !== false} onChange={(e) => set('sorter_enabled', e.target.checked)} data-testid="mg-sorter-enabled" /> «Сортировщик» есть в «Играх»</label>
        <div className="grid md:grid-cols-3 gap-3">
          <Field label="Лимит партий в сутки (0 = без лимита)"><input type="number" min={0} max={50} className={inp} value={cfg.attempts_per_day} onChange={(e) => set('attempts_per_day', e.target.value)} /></Field>
          <Field label="Античит: потолок партий в сутки"><input type="number" min={1} className={inp} value={cfg.daily_cap} onChange={(e) => set('daily_cap', e.target.value)} /></Field>
          <div />
          {[0, 1, 2].map((k) => (
            <Field key={`sp${k}`} label={`Очки для ${'★'.repeat(k + 1)}`}><input type="number" min={0} className={inp} value={(cfg.star_points || [300, 1000, 2000])[k]} onChange={(e) => set('star_points', (cfg.star_points || [300, 1000, 2000]).map((x, j) => (j === k ? e.target.value : x)))} /></Field>
          ))}
          {['1', '2', '3'].map((k) => (
            <Field key={k} label={`XP City Pass за ${'★'.repeat(Number(k))}`}><input type="number" min={0} className={inp} value={(cfg.xp_by_stars || {})[k] ?? 0} onChange={(e) => set('xp_by_stars', { ...(cfg.xp_by_stars || {}), [k]: e.target.value })} /></Field>
          ))}
        </div>
        <div className="rounded-lg border border-white/10 p-3 space-y-2">
          <div className="text-sm text-white font-bold">🏆 Призы рейтинга недели «Сортировщика»</div>
          <PrizeRows prizes={prizes} onChange={(v) => set('leaderboard_prizes', v)} refs={refs} />
        </div>
      </Card>
      <Card title="🎁 Сундук за партию (все игры)">
        <div className="grid md:grid-cols-3 gap-3">
          <Field label="Какой сундук"><select className={inp} value={cfg.chest_container_id || ''} onChange={(e) => set('chest_container_id', e.target.value)} data-testid="mg-chest-container">
            <option value="">— не выдавать —</option>{refs.container.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <Field label="«Сортировщик»: минимум звёзд"><select className={inp} value={cfg.chest_min_stars} onChange={(e) => set('chest_min_stars', e.target.value)}>{[1, 2, 3].map((n) => <option key={n} value={n}>{'★'.repeat(n)}</option>)}</select></Field>
          <Field label="Сундуков в сутки на игрока (на все игры, МСК)"><input type="number" min={0} max={50} className={inp} value={cfg.chests_per_day} onChange={(e) => set('chests_per_day', e.target.value)} data-testid="mg-chests-per-day" /></Field>
        </div>
        <div className="text-[11px] text-text-muted">Игры Аркады: сундук за партию от заданного числа очков (0 — столько же, сколько «очков для максимума XP» в «🎮 Игры и XP»). После лимита игрок играет дальше: очки и XP засчитываются, сундуков до следующих суток нет.</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {MG_GAMES.filter(([g]) => g !== 'sorter').map(([g, name]) => (
            <Field key={g} label={`${name}: очков для сундука`}>
              <input type="number" min={0} className={inp} value={arcChest[g] ?? 0} onChange={(e) => set('arcade_chest_score', { ...arcChest, [g]: e.target.value })} data-testid={`mg-arc-chest-${g}`} />
            </Field>
          ))}
        </div>
      </Card>
      <Card title="🏆 Призы рейтинга недели игр Аркады">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-text-muted">Игра</span>
          <select className={`${inpS} w-56`} value={arcGame} onChange={(e) => setArcGame(e.target.value)} data-testid="mg-arc-prize-game">
            {MG_GAMES.filter(([g]) => g !== 'sorter').map(([g, name]) => <option key={g} value={g}>{name}</option>)}
          </select>
        </div>
        <PrizeRows prizes={arcPrizes} onChange={(v) => set('arcade_prizes', { ...(cfg.arcade_prizes || {}), [arcGame]: v })} refs={refs} />
      </Card>
      <div className="flex gap-2"><Button size="sm" onClick={save} data-testid="mg-save">Сохранить</Button></div>
      <Card title="Рейтинг недели «Сортировщика» (топ-50)">
        {(st.top || []).map((r) => <div key={r.user_id} className="flex justify-between text-sm py-1 border-t border-white/5 text-white/80"><span>{r.place}. @{r.username}</span><b className="text-amber-200">{fmt(r.points)}</b></div>)}
        {(st.top || []).length === 0 && <div className="text-xs text-text-muted">На этой неделе ещё никто не играл</div>}
      </Card>
      {preview && (
        <Modal title="Призы, если неделя закончится сейчас" onClose={() => setPreview(null)}>
          <div className="text-xs text-text-muted">Неделя заканчивается {fmtDate(preview.ends_at)} (МСК) — тогда призы выдаются автоматически.</div>
          {preview.winners.length === 0 && <div className="text-sm text-white/70">Пока призёров нет</div>}
          {preview.winners.map((w) => (
            <div key={`${w.game}-${w.user_id}`} className="flex justify-between text-xs py-1 border-t border-white/5 text-white/85">
              <span>{mgGameName(w.game)} · {w.place}. @{w.username} · {fmt(w.points)}</span>
              <span>{w.prize.kind === 'city' ? `${fmt(w.prize.city)} $CITY` : `${PRIZE_KINDS[w.prize.kind]}: ${w.prize.name || ''}`}</span>
            </div>
          ))}
          {preview.linked.length > 0 && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-2 text-xs text-red-200">
              ⚠️ Связанные аккаунты (одно устройство) среди призёров: {preview.linked.map((l) => `${(preview.winners.find((w) => w.user_id === l.user_id) || {}).username || l.user_id} (аккаунтов на устройстве: ${l.accounts.length})`).join(', ')}.
            </div>
          )}
          <div className="flex justify-end"><Button size="sm" variant="outline" onClick={() => setPreview(null)}>Закрыть</Button></div>
        </Modal>
      )}
    </div>
  );
}

function StatsTab({ api }) {
  const [s, setS] = useState(null);
  useEffect(() => { api.get('/admin/minigames/reward-stats').then(setS).catch(err); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!s) return <div className="text-sm text-text-muted">Загрузка…</div>;
  const resList = (o) => Object.entries(o || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}: ${fmt(v)}`).join(' · ') || '—';
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Сундуков выдано" value={fmt(s.containers.given)} /><Stat label="Сундуков открыто" value={fmt(s.containers.opened)} />
        <Stat label="Сундуков за партии сегодня" value={fmt(s.containers.game_chests_today)} /><Stat label="Кусочков пазлов выпало" value={fmt(s.puzzle_pieces)} />
        <Stat label="Усилителей активно" value={fmt(s.boosters_active)} />
        {Object.entries(s.rewards_by_type).map(([k, v]) => <Stat key={k} label={`Наград: ${k}`} value={fmt(v)} />)}
      </div>
      <Card title="NFT">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs text-white/80">{Object.entries(s.nft).map(([k, v]) => <div key={k}>{k}: <b>{v}</b></div>)}</div>
      </Card>
      <Card title="Ресурсы, введённые через сундуки">
        <div className="text-xs text-white/80">С начала учёта: {resList(s.resources_campaign)}</div>
        <div className="text-xs text-white/80">Всего: {resList(s.resources_total)}</div>
      </Card>
      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Топ-10 «Сортировщика» за неделю">{s.top_points.map((r) => <div key={r.user_id} className="flex justify-between text-xs py-1 border-t border-white/5 text-white/80"><span>{r.place}. @{r.username}</span><b>{fmt(r.points)}</b></div>)}</Card>
        <Card title="Топ-10 по рекорду">{s.top_best.map((r, i) => <div key={r.id} className="flex justify-between text-xs py-1 border-t border-white/5 text-white/80"><span>{i + 1}. @{r.username}</span><b>{fmt(r.mg_best_score)}</b></div>)}</Card>
      </div>
    </div>
  );
}

function AnomaliesTab({ api }) {
  const [rows, setRows] = useState(null);
  const [f, setF] = useState({ user: '', reason: '' });
  const load = useCallback(() => api.get(`/admin/minigames/anomalies?user=${encodeURIComponent(f.user)}&reason=${f.reason}`).then(setRows).catch(err), [f]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);
  return (
    <Card title="Журнал аномалий">
      <div className="flex flex-wrap gap-2">
        <input className={`${inpS} w-48`} placeholder="ID игрока" value={f.user} onChange={(e) => setF({ ...f, user: e.target.value })} />
        <select className={`${inpS} w-64`} value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })}><option value="">Все причины</option>{Object.entries(ANOMALY).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
      </div>
      {(rows || []).length === 0 && <div className="text-xs text-text-muted">Пусто</div>}
      {(rows || []).map((a) => (
        <div key={a.id} className="flex gap-2 text-[11px] py-1.5 border-t border-white/5 text-white/80">
          <span className="w-28 shrink-0">{dt(a.created_at)}</span><span className="w-28 truncate">@{a.username || a.user_id}</span>
          <span className="w-56 shrink-0 text-amber-200">{ANOMALY[a.reason] || a.reason}</span><span className="truncate text-text-muted">{JSON.stringify(a.details)}</span>
        </div>
      ))}
    </Card>
  );
}

const TABS = [['campaign', 'Акция'], ['rewards', 'Награды'], ['containers', 'Сундуки'], ['boosters', 'Усилители'], ['nft', 'NFT'], ['puzzles', 'Пазлы'], ['players', 'Игроки'], ['stats', 'Статистика'], ['anomalies', 'Аномалии']];

export default function MinigamesPanel({ token, tab: tabProp, hideNav = false }) {
  const api = useApi(token);
  const [tabState, setTab] = useState('campaign');
  const tab = tabProp || tabState;                       // inside «Аркада» the section is chosen there
  return (
    <div className="space-y-4" data-testid="admin-minigames">
      <div className={`flex flex-wrap gap-1.5 ${hideNav ? 'hidden' : ''}`}>
        {TABS.map(([id, label]) => (
          <button key={id} type="button" onClick={() => setTab(id)} data-testid={`mg-admin-tab-${id}`}
            className={`px-3 py-1.5 rounded-lg text-sm border ${tab === id ? 'border-cyan-400/60 bg-cyan-400/15 text-cyan-200' : 'border-white/10 bg-white/5 text-white/70'}`}>{label}</button>
        ))}
      </div>
      {tab === 'campaign' && <CampaignTab api={api} />}
      {tab === 'rewards' && <RewardsTab api={api} />}
      {tab === 'containers' && <ContainersTab api={api} />}
      {tab === 'boosters' && <BoostersTab api={api} />}
      {tab === 'nft' && <NftTab api={api} />}
      {tab === 'puzzles' && <PuzzlesTab api={api} />}
      {tab === 'players' && <PlayersTab api={api} />}
      {tab === 'stats' && <StatsTab api={api} />}
      {tab === 'anomalies' && <AnomaliesTab api={api} />}
    </div>
  );
}
