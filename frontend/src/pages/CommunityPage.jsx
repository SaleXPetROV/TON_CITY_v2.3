/**
 * CommunityPage («Общение») — weekly leagues (backend/leagues.py) + a way to the chat.
 *
 * League view: division, time left in the week, three ratings inside the
 * player's group (activity points / units sold / TON sold — the admin can
 * switch each off), promotion and relegation zones, how points are earned,
 * rewards per place, and the last weeks' results.
 * Labels: translationsExtra (en/ru by hand, other languages via LibreTranslate).
 */
import { onProgress } from '@/lib/progressBus';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { MessagesSquare, Trophy, Clock, ArrowUp, ArrowDown, Shield, MessageCircle, ChevronLeft, ChevronRight, Search, Users } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import PageHeader from '@/components/PageHeader';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslation } from '@/lib/translations';
import AllianceView from '@/components/alliances/AllianceView';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;
const getToken = () => localStorage.getItem('token') || localStorage.getItem('ton_city_token');
const auth = () => ({ headers: { Authorization: `Bearer ${getToken()}` } });

const DIV_STYLE = [
  { key: 'leagueDivBronze', color: 'text-amber-600', ring: 'border-amber-600/50', emoji: '🥉' },
  { key: 'leagueDivSilver', color: 'text-slate-300', ring: 'border-slate-300/50', emoji: '🥈' },
  { key: 'leagueDivGold', color: 'text-yellow-400', ring: 'border-yellow-400/50', emoji: '🥇' },
  { key: 'leagueDivPlatinum', color: 'text-cyan-300', ring: 'border-cyan-300/50', emoji: '💠' },
  { key: 'leagueDivDiamond', color: 'text-fuchsia-300', ring: 'border-fuchsia-300/50', emoji: '💎' },
];
const BOARD_LABEL = { points: 'leagueBoardPoints', units_sold: 'leagueBoardUnits', ton_sold: 'leagueBoardTon' };
const ACTION_LABEL = {
  daily_goal: 'leagueActDailyGoal', weekly_goal: 'leagueActWeeklyGoal', shift_start: 'leagueActShift',
  repair: 'leagueActRepair', sale_per_0_01_ton: 'leagueActSale', streak_day: 'leagueActStreak',
};

function useCountdown(iso, t) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(id); }, []);
  if (!iso) return '';
  const ms = Math.max(0, new Date(iso).getTime() - now);
  const d = Math.floor(ms / 86400000), h = Math.floor((ms % 86400000) / 3600000), m = Math.floor((ms % 3600000) / 60000);
  const [ud, uh, um] = [t('unitDay') || 'd', t('unitHour') || 'h', t('unitMin') || 'm'];
  return d > 0 ? `${d}${ud} ${h}${uh}` : `${h}${uh} ${m}${um}`;
}

// Browsing the whole league: other divisions, every player of a division, search, friends (GET /leagues/division/{n}).
const LG = {
  en: { pg: 'Players: {p} · groups: {g}', myGroup: 'My group', wholeLeague: 'Whole division', search: 'Find a player', more: 'Show more', players: 'players', groups: 'groups', toRise: 'To be promoted: top {n} of your group — now about {p} points', youAre: 'You are in', back: 'Back to my division', friends: 'Friends in the leagues', friendsNone: 'Invite friends with your referral link — they will appear here.', empty: 'Nobody here yet this week.', notFound: 'No player with this name in this division.', friend: 'friend' },
  ru: { pg: 'Игроков: {p} · групп: {g}', myGroup: 'Моя группа', wholeLeague: 'Весь дивизион', search: 'Найти игрока', more: 'Показать ещё', players: 'игроков', groups: 'групп', toRise: 'Чтобы подняться: топ-{n} своей группы — сейчас это примерно {p} очков', youAre: 'Вы в', back: 'К моему дивизиону', friends: 'Друзья в лигах', friendsNone: 'Пригласите друзей по реферальной ссылке — они появятся здесь.', empty: 'На этой неделе здесь пока никого нет.', notFound: 'В этом дивизионе нет игрока с таким именем.', friend: 'друг' },
  es: { pg: 'Jugadores: {p} · grupos: {g}', myGroup: 'Mi grupo', wholeLeague: 'Toda la división', search: 'Buscar jugador', more: 'Mostrar más', players: 'jugadores', groups: 'grupos', toRise: 'Para ascender: top {n} de tu grupo — ahora unos {p} puntos', youAre: 'Estás en', back: 'Volver a mi división', friends: 'Amigos en las ligas', friendsNone: 'Invita amigos con tu enlace de referido: aparecerán aquí.', empty: 'Aún no hay nadie esta semana.', notFound: 'No hay ningún jugador con ese nombre en esta división.', friend: 'amigo' },
  zh: { pg: '玩家：{p} · 小组：{g}', myGroup: '我的小组', wholeLeague: '整个段位', search: '查找玩家', more: '显示更多', players: '名玩家', groups: '个小组', toRise: '晋级条件：小组前 {n} 名——目前约需 {p} 分', youAre: '你在', back: '回到我的段位', friends: '联赛中的好友', friendsNone: '用推荐链接邀请好友——他们会显示在这里。', empty: '本周这里还没有人。', notFound: '此段位中没有该名字的玩家。', friend: '好友' },
  fr: { pg: 'Joueurs : {p} · groupes : {g}', myGroup: 'Mon groupe', wholeLeague: 'Toute la division', search: 'Trouver un joueur', more: 'Afficher plus', players: 'joueurs', groups: 'groupes', toRise: 'Pour monter : top {n} de votre groupe — actuellement environ {p} points', youAre: 'Vous êtes en', back: 'Retour à ma division', friends: 'Amis dans les ligues', friendsNone: 'Invitez des amis avec votre lien de parrainage — ils apparaîtront ici.', empty: 'Personne ici cette semaine.', notFound: 'Aucun joueur de ce nom dans cette division.', friend: 'ami' },
  de: { pg: 'Spieler: {p} · Gruppen: {g}', myGroup: 'Meine Gruppe', wholeLeague: 'Ganze Division', search: 'Spieler finden', more: 'Mehr anzeigen', players: 'Spieler', groups: 'Gruppen', toRise: 'Zum Aufstieg: Top {n} deiner Gruppe – derzeit etwa {p} Punkte', youAre: 'Du bist in', back: 'Zu meiner Division', friends: 'Freunde in den Ligen', friendsNone: 'Lade Freunde mit deinem Empfehlungslink ein – sie erscheinen hier.', empty: 'Diese Woche ist hier noch niemand.', notFound: 'Kein Spieler mit diesem Namen in dieser Division.', friend: 'Freund' },
  ja: { pg: 'プレイヤー：{p} · グループ：{g}', myGroup: '自分のグループ', wholeLeague: 'ディビジョン全体', search: 'プレイヤーを検索', more: 'さらに表示', players: '人', groups: 'グループ', toRise: '昇格条件：グループ上位{n}位 — 現在おおよそ{p}ポイント', youAre: '現在', back: '自分のディビジョンへ', friends: 'リーグの友達', friendsNone: '紹介リンクで友達を招待すると、ここに表示されます。', empty: '今週はまだ誰もいません。', notFound: 'このディビジョンにその名前のプレイヤーはいません。', friend: '友達' },
  ko: { pg: '플레이어: {p} · 그룹: {g}', myGroup: '내 그룹', wholeLeague: '디비전 전체', search: '플레이어 찾기', more: '더 보기', players: '명', groups: '개 그룹', toRise: '승급하려면: 그룹 상위 {n}위 — 지금은 약 {p}점', youAre: '현재', back: '내 디비전으로', friends: '리그의 친구', friendsNone: '추천 링크로 친구를 초대하면 여기에 표시됩니다.', empty: '이번 주에는 아직 아무도 없습니다.', notFound: '이 디비전에 그 이름의 플레이어가 없습니다.', friend: '친구' },
  id: { pg: 'Pemain: {p} · grup: {g}', myGroup: 'Grup saya', wholeLeague: 'Seluruh divisi', search: 'Cari pemain', more: 'Tampilkan lagi', players: 'pemain', groups: 'grup', toRise: 'Untuk naik: top {n} grup Anda — sekarang sekitar {p} poin', youAre: 'Anda di', back: 'Kembali ke divisi saya', friends: 'Teman di liga', friendsNone: 'Undang teman dengan tautan referral — mereka akan muncul di sini.', empty: 'Belum ada siapa pun minggu ini.', notFound: 'Tidak ada pemain dengan nama ini di divisi ini.', friend: 'teman' },
};

const fmtValue = (board, v) => (board === 'ton_sold' ? `${Number(v).toFixed(3)} GRAM` : Math.round(v).toLocaleString());

export default function CommunityPage({ user, refreshBalance, initialTab }) {
  const navigate = useNavigate();
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const [tab, setTab] = useState(() => initialTab || (new URLSearchParams(window.location.search).get('tab') === 'alliance' ? 'alliance' : 'leagues'));
  const [data, setData] = useState(null);
  const [board, setBoard] = useState('points');
  const [busy, setBusy] = useState(false);
  const lg = LG[lang] || LG.en;
  const [viewDiv, setViewDiv] = useState(null);         // null = my division; 0..4 = browsing
  const [mode, setMode] = useState('group');            // my division: 'group' (my group) | 'all' (whole division)
  const [q, setQ] = useState('');
  const [dv, setDv] = useState(null);                   // GET /leagues/division/{n}
  const [dvBusy, setDvBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/leagues/me`, auth());
      setData(r.data);
      setBoard((b) => (r.data.boards && r.data.boards[b] ? b : Object.keys(r.data.boards || {})[0] || 'points'));
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error');
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => onProgress(() => load()), [load]);   // league points refresh right after an action

  const join = async () => {
    setBusy(true);
    try { const r = await axios.post(`${API}/leagues/join`, {}, auth()); setData(r.data); }
    catch (e) { toast.error(e?.response?.data?.detail || 'Error'); }
    finally { setBusy(false); }
  };

  const left = useCountdown(data?.ends_at, t);
  const myDiv = data?.division || 0;
  const shownDiv = viewDiv == null ? myDiv : viewDiv;
  const browsing = shownDiv !== myDiv || (mode === 'all' && !!data?.joined);
  const div = DIV_STYLE[shownDiv];
  const loadDivision = useCallback(async (n, query, offset = 0) => {
    setDvBusy(true);
    try {
      const r = await axios.get(`${API}/leagues/division/${n}`, { ...auth(), params: { q: query || '', limit: 50, offset } });
      setDv((prev) => (offset > 0 && prev ? { ...r.data, rows: [...prev.rows, ...r.data.rows] } : r.data));
    } catch (e) { /* keep the last view */ } finally { setDvBusy(false); }
  }, []);
  useEffect(() => {
    if (!data?.enabled) return undefined;
    const id = setTimeout(() => loadDivision(shownDiv, q, 0), q ? 300 : 0);   // debounce typing
    return () => clearTimeout(id);
  }, [data?.enabled, shownDiv, q, loadDivision]);
  const stepDiv = (d) => { setQ(''); setViewDiv(Math.max(0, Math.min(4, shownDiv + d))); };
  const rows = (data?.standings || {})[board] || [];
  const isPromoBoard = board === data?.promotion_board;
  const rewards = ((data?.boards || {})[board] || {}).rewards_city || [];
  const zone = useMemo(() => (i, n) => {
    if (!isPromoBoard || !data) return '';
    if (i < data.promote_count && data.division < 4) return 'up';
    if (i >= n - data.relegate_count && n > data.promote_count && data.division > 0) return 'down';
    return '';
  }, [isPromoBoard, data]);

  return (
    <div className="flex h-screen bg-void">
      <Sidebar user={user} refreshBalance={refreshBalance} />
      <div className="flex-1 overflow-hidden lg:ml-16">
        <ScrollArea className="h-full">
          <div className="p-4 lg:px-6 lg:pt-2 lg:pb-24 pt-0 pb-28 space-y-4 max-w-3xl mx-auto w-full min-w-0">
            <PageHeader help="community" icon={<MessagesSquare className="w-6 h-6 text-cyber-cyan" />} title={t('communityTitle')} subtitle={t('communitySubtitle')} />

            {/* the chat moved to the «Чат» button on the «Бизнесы» page */}
            <div className="grid grid-cols-2 gap-2" role="tablist">
              <button type="button" role="tab" aria-selected={tab === 'leagues'} onClick={() => setTab('leagues')}
                className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-3 text-sm font-bold uppercase tracking-wide ${tab === 'leagues' ? 'border-yellow-400/60 bg-yellow-400/15 text-yellow-300' : 'border-white/10 text-white/60'}`} data-testid="community-tab-leagues">
                <Trophy className="w-4 h-4" />{t('communityTabLeagues')}
              </button>
              <button type="button" role="tab" aria-selected={tab === 'alliance'} onClick={() => setTab('alliance')}
                className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-3 text-sm font-bold uppercase tracking-wide ${tab === 'alliance' ? 'border-fuchsia-400/60 bg-fuchsia-400/15 text-fuchsia-200' : 'border-white/10 text-white/60'}`} data-testid="community-tab-alliance">
                <Shield className="w-4 h-4" />{t('al_tab')}
              </button>
            </div>

            {tab === 'alliance' ? <AllianceView user={user} lang={lang} t={t} refreshUser={refreshBalance} /> : !data ? <div className="text-center text-text-muted py-10">…</div> : !data.enabled ? (
              <div className="text-center text-text-muted py-10" data-testid="league-disabled">{t('leagueDisabled')}</div>
            ) : (
              <>
                {/* division + countdown */}
                <Card className={`glass-panel border ${div.ring}`} data-testid="league-header">
                  <CardContent className="p-3 sm:p-4 flex items-center gap-2 sm:gap-3">
                    <button type="button" onClick={() => stepDiv(-1)} disabled={shownDiv === 0} aria-label="‹"
                      className="w-9 h-9 shrink-0 rounded-full border border-white/15 bg-white/5 flex items-center justify-center text-white disabled:opacity-25" data-testid="league-div-prev">
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <div className="text-4xl">{div.emoji}</div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[11px] uppercase tracking-wide text-text-muted">{t('leagueDivision')}</div>
                      <div className={`text-xl font-bold ${div.color}`} data-testid="league-div-name">{t(div.key)}</div>
                      {shownDiv === myDiv ? (
                        <div className="text-[11px] text-text-muted flex items-center gap-1 mt-0.5"><Clock className="w-3 h-3" />{t('leagueEndsIn')} {left}</div>
                      ) : (
                        <button type="button" onClick={() => { setViewDiv(null); setQ(''); }} className="text-[11px] text-cyber-cyan underline-offset-2 hover:underline mt-0.5 text-left" data-testid="league-div-back">
                          {lg.youAre}: {t(DIV_STYLE[myDiv].key)} · {lg.back}
                        </button>
                      )}
                    </div>
                    {shownDiv === myDiv && data.me && mode === 'group' && (
                      <div className="text-right">
                        <div className="text-[11px] text-text-muted">{t(BOARD_LABEL[data.promotion_board])}</div>
                        <div className="text-2xl font-bold text-white">#{data.me.ranks[data.promotion_board]}</div>
                      </div>
                    )}
                    <button type="button" onClick={() => stepDiv(1)} disabled={shownDiv === 4} aria-label="›"
                      className="w-9 h-9 shrink-0 rounded-full border border-white/15 bg-white/5 flex items-center justify-center text-white disabled:opacity-25" data-testid="league-div-next">
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </CardContent>
                </Card>

                {/* my group / the whole division */}
                {shownDiv === myDiv && data.joined && (
                  <div className="grid grid-cols-2 gap-1.5" data-testid="league-mode">
                    {[['group', lg.myGroup], ['all', lg.wholeLeague]].map(([m, label]) => (
                      <button key={m} type="button" onClick={() => setMode(m)} data-testid={`league-mode-${m}`}
                        className={`rounded-lg border px-3 py-2 text-xs font-semibold ${mode === m ? 'border-yellow-400/60 bg-yellow-400/15 text-yellow-200' : 'border-white/10 bg-white/5 text-white/70'}`}>
                        {label}
                      </button>
                    ))}
                  </div>
                )}

                {browsing && (
                  <Card className="glass-panel border-white/10" data-testid="league-division-view">
                    <CardContent className="p-2 sm:p-3 space-y-2">
                      {dv && (
                        <div className="px-1 text-[11px] text-text-muted space-y-0.5">
                          <div>{lg.pg.replace('{p}', dv.players).replace('{g}', dv.groups)}</div>
                          {shownDiv < 4 && dv.players > 0 && (
                            <div className="text-emerald-300/90 flex items-center gap-1"><ArrowUp className="w-3 h-3 shrink-0" />{lg.toRise.replace('{n}', dv.promote_count).replace('{p}', Math.round(dv.promote_line))}</div>
                          )}
                        </div>
                      )}
                      <label className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/30 px-2.5 py-1.5">
                        <Search className="w-4 h-4 text-white/40 shrink-0" />
                        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={lg.search} maxLength={40}
                          className="flex-1 min-w-0 bg-transparent text-sm text-white placeholder:text-white/35 outline-none" data-testid="league-search" />
                      </label>
                      <div className="divide-y divide-white/5" data-testid="league-division-table">
                        {(dv?.rows || []).map((r) => (
                          <div key={`${r.rank}-${r.name}`} className={`flex items-center gap-2 px-2 py-2 text-sm ${r.me ? 'bg-yellow-400/10 rounded-lg' : r.friend ? 'bg-cyan-400/5 rounded-lg' : ''}`}>
                            <span className="w-9 text-center font-bold text-white/60">{r.rank}</span>
                            <span className={`flex-1 truncate ${r.me ? 'text-yellow-300 font-semibold' : 'text-white'}`}>
                              {r.name}{r.me ? ` (${t('leagueYou')})` : ''}
                            </span>
                            {r.friend && <span className="text-[10px] rounded-full border border-cyan-400/40 text-cyan-200 px-1.5 py-0.5 flex items-center gap-0.5"><Users className="w-3 h-3" />{lg.friend}</span>}
                            <span className="w-16 text-right font-mono text-white/90">{Math.round(r[dv.board] ?? r.points)}</span>
                          </div>
                        ))}
                        {dv && dv.rows.length === 0 && <div className="text-center text-xs text-text-muted py-4">{q ? lg.notFound : lg.empty}</div>}
                      </div>
                      {dv && dv.rows.length < dv.total && (
                        <Button variant="outline" size="sm" className="w-full" disabled={dvBusy} onClick={() => loadDivision(shownDiv, q, dv.rows.length)} data-testid="league-more">{lg.more}</Button>
                      )}
                    </CardContent>
                  </Card>
                )}


                {browsing ? null : !data.joined ? (
                  <Card className="glass-panel border-white/10">
                    <CardContent className="p-4 text-center space-y-3">
                      <p className="text-sm text-text-muted">{t('leagueJoinHint')}</p>
                      <Button onClick={join} disabled={busy} data-testid="league-join">{t('leagueJoin')}</Button>
                    </CardContent>
                  </Card>
                ) : (
                  <>
                    {/* ratings */}
                    <div className="flex gap-1.5 overflow-x-auto" data-testid="league-boards">
                      {Object.keys(data.boards).map((b) => (
                        <button key={b} type="button" onClick={() => setBoard(b)} data-testid={`league-board-${b}`}
                          className={`flex-1 whitespace-nowrap rounded-lg border px-3 py-2 text-xs font-semibold ${board === b ? 'border-cyber-cyan/60 bg-cyber-cyan/15 text-cyber-cyan' : 'border-white/10 bg-white/5 text-white/70'}`}>
                          {t(BOARD_LABEL[b])}{data.me ? ` · #${data.me.ranks[b]}` : ''}
                        </button>
                      ))}
                    </div>

                    <Card className="glass-panel border-white/10">
                      <CardContent className="p-2 sm:p-3">
                        {isPromoBoard && (
                          <div className="flex gap-3 text-[11px] text-text-muted px-1 pb-2">
                            <span className="flex items-center gap-1 text-emerald-400"><ArrowUp className="w-3 h-3" />{t('leaguePromoZone')}</span>
                            <span className="flex items-center gap-1 text-red-400"><ArrowDown className="w-3 h-3" />{t('leagueRelegZone')}</span>
                          </div>
                        )}
                        <div className="divide-y divide-white/5" data-testid="league-table">
                          {rows.map((r, i) => {
                            const z = zone(i, rows.length);
                            const reward = rewards[i];
                            return (
                              <div key={r.user_id} className={`flex items-center gap-2 px-2 py-2 text-sm ${r.me ? 'bg-yellow-400/10 rounded-lg' : ''}`} data-testid={r.me ? 'league-row-me' : undefined}>
                                <span className={`w-7 text-center font-bold ${z === 'up' ? 'text-emerald-400' : z === 'down' ? 'text-red-400' : 'text-white/60'}`}>{r.rank}</span>
                                <span className={`flex-1 truncate ${r.me ? 'text-yellow-300 font-semibold' : 'text-white'}`}>{r.name}{r.me ? ` (${t('leagueYou')})` : ''}</span>
                                {reward > 0 && <span className="text-[10px] text-yellow-300/80">+{reward}</span>}
                                <span className="w-24 text-right font-mono text-white/90">{fmtValue(board, r.value)}</span>
                              </div>
                            );
                          })}
                        </div>
                      </CardContent>
                    </Card>
                  </>
                )}

                {/* friends in every division */}
                {dv && (
                  <Card className="glass-panel border-cyan-500/15" data-testid="league-friends">
                    <CardContent className="p-3 space-y-1.5">
                      <div className="text-sm font-bold text-white flex items-center gap-1.5"><Users className="w-4 h-4 text-cyan-300" />{lg.friends}</div>
                      {dv.friends.length === 0 ? <p className="text-[11px] text-text-muted">{lg.friendsNone}</p> : dv.friends.map((f) => (
                        <button key={f.name} type="button" onClick={() => { setViewDiv(f.division); setMode('all'); setQ(f.name); }}
                          className="w-full flex items-center justify-between rounded-lg bg-white/5 px-2.5 py-1.5 text-xs text-left hover:bg-white/10">
                          <span className="text-white truncate">{DIV_STYLE[f.division].emoji} {f.name}</span>
                          <span className="text-white/70 font-mono">{Math.round(f.points)}</span>
                        </button>
                      ))}
                    </CardContent>
                  </Card>
                )}

                {/* how points are earned */}
                <Card className="glass-panel border-white/10">
                  <CardContent className="p-4 space-y-2">
                    <div className="text-sm font-bold text-white">{t('leagueHowPoints')}</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
                      {Object.entries(data.points_table).map(([k, v]) => v > 0 && (
                        <div key={k} className="flex justify-between rounded-lg bg-white/5 px-2.5 py-1.5">
                          <span className="text-white/80">{t(ACTION_LABEL[k])}</span>
                          <span className="text-cyber-cyan font-semibold">+{v}</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-[11px] text-text-muted">{t('leagueDailyCap').replace('{n}', data.daily_points_cap)} {t('leagueSalesNote')}</p>
                    {data.shield_top_n > 0 && <p className="text-[11px] text-text-muted flex items-center gap-1"><Shield className="w-3 h-3" />{t('leagueShieldNote').replace('{n}', data.shield_top_n)}</p>}
                  </CardContent>
                </Card>

                {data.history?.length > 0 && (
                  <Card className="glass-panel border-white/10">
                    <CardContent className="p-4 space-y-1.5" data-testid="league-history">
                      <div className="text-sm font-bold text-white">{t('leagueHistory')}</div>
                      {data.history.map((h) => (
                        <div key={h.week} className="flex justify-between text-xs text-white/80">
                          <span>{h.week} · {t(DIV_STYLE[h.division].key)}</span>
                          <span>
                            {h.move === 'up' ? '⬆️' : h.move === 'down' ? '⬇️' : '•'} #{(h.ranks || {})[data.promotion_board] ?? '—'}
                            {h.reward_city > 0 ? ` · +${h.reward_city} $CITY` : ''}
                          </span>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
