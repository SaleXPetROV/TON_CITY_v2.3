/**
 * Админка → Поддержка → «Willy GRAM»: помощник поддержки на своей базе ответов (без внешних нейросетей).
 *   База ответов — формулировки вопросов, текст с переменными, проверки аккаунта, статья, кнопки, предпросмотр
 *                  «как увидит игрок» на любом из 9 языков. Всё пишется по-русски.
 *   Проверить вопрос — что Willy сделает с вопросом: правило, совпадения, решение.
 *   Пробелы — вопросы, на которые не нашлось уверенного ответа: добавить к ответу, создать ответ, скрыть.
 *   Статистика и Правила — пороги уверенности, когда сразу звать человека.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Bot, Search, Plus, Save, Trash2, RefreshCw, Eye, AlertTriangle, BarChart3, Settings2, FlaskConical } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const LANG_NAMES = { ru: 'Русский', en: 'English', es: 'Español', zh: '中文', fr: 'Français', de: 'Deutsch', ja: '日本語', ko: '한국어', id: 'Indonesia' };
const TOPICS = { start: 'Начало', land: 'Земля', business: 'Бизнес', warehouse: 'Склад', trade: 'Торговля', money: 'Деньги', rewards: 'Награды', community: 'Сообщество', rules: 'Правила и помощь' };
const RULE_HELP = {
  money: 'Пополнение, вывод, списание, заморозка, кредит — когда что-то не пришло, пропало, списалось. «Строго» — любой вопрос о деньгах.',
  human: '«Позовите человека», «оператор», «нужен агент»…',
  complaint: 'Жалоба, претензия, обман',
  bug: 'Ошибка в игре: вылетает, не грузится, баг',
  seizure: 'Изъятие бизнеса («забрали мой бизнес»)',
  hack: 'Взлом, кража, «это не я выводил»',
  dispute: 'Спор с другим игроком',
};
const empty = () => ({ title: '', topic: 'start', phrasings: [], text: '', wiki: '', route: '', checks: [], handoff: false, enabled: true, show: true, agent_only: false });

const box = 'bg-white/[0.03] border border-white/10 rounded-xl';
const inp = 'w-full bg-black/40 border border-white/15 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-400/60';
const btn = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition disabled:opacity-40';

export default function AdminWilly() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const h = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);
  const [tab, setTab] = useState('base');
  const [meta, setMeta] = useState(null); // vars, checks, articles
  useEffect(() => {
    axios.get(`${API}/admin/willy/vars`, h).then((r) => setMeta(r.data)).catch(() => toast.error('Не удалось загрузить данные Willy GRAM'));
  }, [h]);
  const tabs = [
    ['base', 'База ответов', Bot], ['test', 'Проверить вопрос', FlaskConical], ['gaps', 'Пробелы в базе', AlertTriangle],
    ['stats', 'Статистика', BarChart3], ['rules', 'Правила', Settings2],
  ];
  const [seedEditor, setSeedEditor] = useState(null);
  return (
    <div className="space-y-4" data-testid="admin-willy">
      <div className="flex flex-wrap items-center gap-1 bg-white/5 border border-white/10 rounded-xl p-1 w-fit">
        {tabs.map(([k, l, Icon]) => (
          <button key={k} onClick={() => setTab(k)} data-testid={`willy-tab-${k}`}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${tab === k ? 'bg-violet-500 text-white' : 'text-white/60 hover:text-white hover:bg-white/5'}`}>
            <Icon className="w-3.5 h-3.5" /> {l}
          </button>
        ))}
      </div>
      {tab === 'base' && <Base h={h} meta={meta} seed={seedEditor} clearSeed={() => setSeedEditor(null)} />}
      {tab === 'test' && <Tester h={h} />}
      {tab === 'gaps' && <Gaps h={h} onCreate={(q) => { setSeedEditor({ ...empty(), title: q.slice(0, 90), phrasings: [q] }); setTab('base'); }} />}
      {tab === 'stats' && <Stats h={h} />}
      {tab === 'rules' && <Rules h={h} />}
    </div>
  );
}

// ───────────────────────────── База ответов ─────────────────────────────
function Base({ h, meta, seed, clearSeed }) {
  const [list, setList] = useState(null);
  const [q, setQ] = useState('');
  const [topic, setTopic] = useState('');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(1);
  const [cur, setCur] = useState(null);
  const [busy, setBusy] = useState(false);
  const [pv, setPv] = useState(null);
  const [pvLang, setPvLang] = useState('en');
  const [pvUser, setPvUser] = useState('');

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/admin/willy/answers`, { ...h, params: { q, topic, status, page } });
      setList(r.data);
    } catch { toast.error('Не удалось загрузить базу ответов'); }
  }, [h, q, topic, status, page]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);
  useEffect(() => { if (seed) { setCur(seed); setPv(null); clearSeed(); } }, [seed, clearSeed]);

  const open = (a) => { setCur({ ...empty(), ...JSON.parse(JSON.stringify(a)), wiki: a.wiki || '', route: a.route || '' }); setPv(null); };
  const set = (k, v) => setCur((c) => ({ ...c, [k]: v }));
  const save = async () => {
    const body = { ...cur, wiki: cur.wiki || null, route: cur.route || null, phrasings: (cur.phrasings || []).filter((x) => x.trim()) };
    if (!body.title.trim() || !body.text.trim()) { toast.error('Нужны заголовок и текст ответа'); return; }
    setBusy(true);
    try {
      const r = cur.id ? await axios.put(`${API}/admin/willy/answers/${cur.id}`, body, h) : await axios.post(`${API}/admin/willy/answers`, body, h);
      toast.success('Сохранено — Willy уже отвечает по-новому');
      open(r.data); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Ошибка сохранения'); }
    setBusy(false);
  };
  const del = async () => {
    if (!cur?.id || !window.confirm('Удалить ответ? Ответ из поставки будет выключен.')) return;
    try { await axios.delete(`${API}/admin/willy/answers/${cur.id}`, h); toast.success('Удалено'); setCur(null); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const preview = async () => {
    try {
      const r = await axios.post(`${API}/admin/willy/preview`, { answer_id: cur.id || null, text: cur.text, lang: pvLang, user_id: pvUser.trim() || null }, h);
      setPv(r.data);
    } catch (e) { toast.error(e.response?.data?.detail || 'Ошибка предпросмотра'); }
  };
  const insertVar = (v) => set('text', `${cur.text || ''}{${v}}`);
  const c = list?.counts || {};

  return (
    <div className="grid lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-4">
      <div className={`${box} p-3 flex flex-col min-h-[520px]`}>
        <div className="flex flex-wrap gap-2 text-[11px] text-white/60 mb-2">
          <span>Ответов: <b className="text-white">{c.all ?? '…'}</b></span>
          <span>включено: <b className="text-emerald-300">{c.ok ?? '…'}</b></span>
          <span>на проверке: <b className="text-amber-300">{c.review ?? 0}</b></span>
          <span>формулировок: <b className="text-white">{c.phrasings ?? '…'}</b></span>
        </div>
        <div className="flex gap-2 mb-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-white/35" />
            <input className={`${inp} pl-8`} placeholder="Поиск по ответам и формулировкам" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} data-testid="willy-search" />
          </div>
          <button className={`${btn} bg-violet-500 hover:bg-violet-400 text-white`} onClick={() => { setCur(empty()); setPv(null); }} data-testid="willy-new"><Plus className="w-3.5 h-3.5" /> Новый</button>
        </div>
        <div className="flex gap-2 mb-2">
          <select className={inp} value={topic} onChange={(e) => { setTopic(e.target.value); setPage(1); }}>
            <option value="">Все разделы</option>
            {Object.entries(TOPICS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          <select className={inp} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} data-testid="willy-status-filter">
            <option value="all">Все</option><option value="ok">Включены</option><option value="off">Выключены</option><option value="review">На проверке</option>
          </select>
        </div>
        <div className="flex-1 overflow-y-auto space-y-1 pr-1 max-h-[560px]">
          {(list?.items || []).map((a) => (
            <button key={a.id} onClick={() => open(a)} data-testid={`willy-row-${a.key || a.id}`}
              className={`w-full text-left px-2.5 py-2 rounded-lg border transition ${cur?.id === a.id ? 'border-violet-400/60 bg-violet-500/15' : 'border-white/5 bg-white/[0.02] hover:bg-white/5'}`}>
              <div className="flex items-center justify-between gap-2">
                <span className={`text-[13px] ${a.enabled ? 'text-white' : 'text-white/40 line-through'}`}>{a.title}</span>
                <span className="text-[10px] text-white/35 shrink-0">{(a.phrasings || []).length} форм.</span>
              </div>
              <div className="flex gap-2 text-[10px] text-white/40 mt-0.5">
                <span>{TOPICS[a.topic] || a.topic || '—'}</span>
                {a.status === 'review' && <span className="text-amber-300">на проверке · от {a.created_by || 'агента'}</span>}
                {a.agent_only && <span className="text-violet-300">для оператора</span>}
                {a.origin === 'admin' && <span className="text-cyan-300">изменён</span>}
                <span className="ml-auto">показан {a.stats?.shown || 0} · 👍 {a.stats?.helped || 0} · 👎 {a.stats?.not_helped || 0}</span>
              </div>
            </button>
          ))}
          {list && !list.items.length && <div className="text-center text-white/35 text-sm py-8">Ничего не найдено</div>}
        </div>
        {list && list.pages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-2 text-xs text-white/60">
            <button className={`${btn} bg-white/5`} disabled={page <= 1} onClick={() => setPage(page - 1)}>‹</button>
            {page} / {list.pages}
            <button className={`${btn} bg-white/5`} disabled={page >= list.pages} onClick={() => setPage(page + 1)}>›</button>
          </div>
        )}
      </div>

      <div className={`${box} p-4`}>
        {!cur ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-white/40 text-sm gap-2 py-16">
            <Bot className="w-10 h-10 text-violet-300/60" />
            Выберите ответ слева или создайте новый.<br />
            Всё пишется по-русски: вопрос игрока переводится на русский, ответ — на язык игрока.
          </div>
        ) : (
          <div className="space-y-3" data-testid="willy-editor">
            <div className="grid sm:grid-cols-[1fr_180px] gap-2">
              <label className="text-[11px] text-white/50">Заголовок (виден в кнопках «О чём вопрос?»)
                <input className={inp} value={cur.title} onChange={(e) => set('title', e.target.value)} data-testid="willy-title" />
              </label>
              <label className="text-[11px] text-white/50">Раздел
                <select className={inp} value={cur.topic || ''} onChange={(e) => set('topic', e.target.value)}>
                  {Object.entries(TOPICS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                </select>
              </label>
            </div>
            <label className="block text-[11px] text-white/50">Как спрашивают игроки — по одной формулировке в строке ({(cur.phrasings || []).length})
              <textarea className={`${inp} h-28 font-mono text-[12px]`} value={(cur.phrasings || []).join('\n')}
                onChange={(e) => set('phrasings', e.target.value.split('\n'))} data-testid="willy-phrasings" />
            </label>
            {(cur.suggested || []).length > 0 && (
              <div className="text-[11px] text-white/50">Игроки выбрали этот ответ после вопроса — добавить формулировку:
                <div className="flex flex-wrap gap-1 mt-1">
                  {cur.suggested.map((s) => (
                    <button key={s} className="px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-400/30 text-amber-100 text-[11px]"
                      onClick={() => setCur((x) => ({ ...x, phrasings: [...(x.phrasings || []), s], suggested: x.suggested.filter((y) => y !== s) }))}>+ {s}</button>
                  ))}
                </div>
              </div>
            )}
            <label className="block text-[11px] text-white/50">Текст ответа (до ~350 знаков: суть, цифры игрока, ссылка на статью)
              <textarea className={`${inp} h-28`} value={cur.text} onChange={(e) => set('text', e.target.value)} data-testid="willy-text" />
            </label>
            {meta && (
              <details className="text-[11px] text-white/50">
                <summary className="cursor-pointer select-none">Переменные — нажмите, чтобы вставить</summary>
                <div className="mt-1.5 text-white/40">Данные игрока:</div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(meta.player).map(([k, l]) => (
                    <button key={k} title={l} onClick={() => insertVar(k)} className="px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-400/20 text-cyan-100 font-mono">{`{${k}}`}</button>
                  ))}
                </div>
                <div className="mt-1.5 text-white/40">Цифры игры (из настроек):</div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(meta.game).map(([k, v]) => (
                    <button key={k} title={`сейчас: ${v}`} onClick={() => insertVar(k)} className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-white/70 font-mono">{`{${k}}`}</button>
                  ))}
                </div>
              </details>
            )}
            <div className="grid sm:grid-cols-2 gap-2">
              <label className="text-[11px] text-white/50">Статья Справочника (кнопка под ответом)
                <select className={inp} value={cur.wiki || ''} onChange={(e) => set('wiki', e.target.value)} data-testid="willy-wiki">
                  <option value="">— без статьи —</option>
                  {(meta?.articles || []).map((a) => <option key={a.slug} value={a.slug}>{a.icon} {a.title}</option>)}
                </select>
              </label>
              <label className="text-[11px] text-white/50">Кнопка «Открыть экран» (путь в игре)
                <input className={inp} placeholder="/trading?tab=my" value={cur.route || ''} onChange={(e) => set('route', e.target.value)} />
              </label>
            </div>
            {meta && (
              <div className="text-[11px] text-white/50">Проверки аккаунта под ответом (✅/❌ на языке игрока):
                <div className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(meta.checks).map(([k, l]) => {
                    const on = (cur.checks || []).includes(k);
                    return (
                      <button key={k} onClick={() => set('checks', on ? cur.checks.filter((x) => x !== k) : [...(cur.checks || []), k])}
                        className={`px-2 py-0.5 rounded-full border text-[11px] ${on ? 'bg-emerald-500/20 border-emerald-400/40 text-emerald-100' : 'bg-white/5 border-white/10 text-white/55'}`}>{l}</button>
                    );
                  })}
                </div>
              </div>
            )}
            <div className="flex flex-wrap gap-4 text-[12px] text-white/75">
              <label className="flex items-center gap-1.5"><input type="checkbox" checked={!!cur.enabled} onChange={(e) => set('enabled', e.target.checked)} data-testid="willy-enabled" /> Включён</label>
              <label className="flex items-center gap-1.5"><input type="checkbox" checked={cur.show !== false} onChange={(e) => set('show', e.target.checked)} /> Кнопка «Показать на деле»</label>
              <label className="flex items-center gap-1.5" title="Игрок его не получит: только черновик для оператора"><input type="checkbox" checked={!!cur.agent_only} onChange={(e) => set('agent_only', e.target.checked)} /> Только для оператора</label>
              <label className="flex items-center gap-1.5" title="После ответа чат сразу уходит людям"><input type="checkbox" checked={!!cur.handoff} onChange={(e) => set('handoff', e.target.checked)} /> Ответить и позвать человека</label>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className={`${btn} bg-violet-500 hover:bg-violet-400 text-white`} onClick={save} disabled={busy} data-testid="willy-save"><Save className="w-3.5 h-3.5" /> Сохранить</button>
              {cur.id && <button className={`${btn} bg-red-500/20 hover:bg-red-500/30 text-red-200`} onClick={del}><Trash2 className="w-3.5 h-3.5" /> Удалить</button>}
              {cur.origin === 'seed' && <span className="text-[10px] text-white/35 self-center">Ответ из поставки. После правки новая поставка его не перезапишет.</span>}
            </div>

            <div className="border-t border-white/10 pt-3">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="text-[12px] font-semibold text-white/80 flex items-center gap-1"><Eye className="w-3.5 h-3.5" /> Как увидит игрок</span>
                <select className="bg-black/40 border border-white/15 rounded-lg px-2 py-1 text-xs" value={pvLang} onChange={(e) => setPvLang(e.target.value)} data-testid="willy-pv-lang">
                  {Object.entries(LANG_NAMES).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                </select>
                <input className="bg-black/40 border border-white/15 rounded-lg px-2 py-1 text-xs w-56" placeholder="ID игрока (иначе — пример)" value={pvUser} onChange={(e) => setPvUser(e.target.value)} />
                <button className={`${btn} bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-100`} onClick={preview} data-testid="willy-preview">Показать</button>
              </div>
              {pv && (
                <div className="rounded-xl border border-cyan-400/20 bg-cyan-500/[0.06] p-3" data-testid="willy-preview-out">
                  <div className="text-[11px] font-semibold text-cyan-300 mb-1">🤖 Willy GRAM</div>
                  <div className="text-sm whitespace-pre-wrap">{pv.text}</div>
                  {(pv.checks || []).map((x, i) => <div key={i} className="text-[12px] mt-1">{x.state === 'ok' ? '✅' : x.state === 'fail' ? '❌' : 'ℹ️'} {x.text}</div>)}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {(pv.buttons || []).map((b, i) => <span key={i} className="text-[11px] px-2 py-0.5 rounded-full border border-cyan-400/30 text-cyan-100">{b.kind === 'wiki' ? `${b.icon} ${b.title}` : b.kind === 'show' ? '👆 Показать на деле' : `↗ ${b.path}`}</span>)}
                  </div>
                  {!pv.translated && pv.lang !== 'ru' && <div className="text-[11px] text-amber-300 mt-2">LibreTranslate не ответил — игрок получил бы русский текст.</div>}
                  {(pv.unknown_vars || []).length > 0 && <div className="text-[11px] text-red-300 mt-1">Неизвестные переменные: {pv.unknown_vars.join(', ')}</div>}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ───────────────────────────── Проверить вопрос ─────────────────────────────
function Tester({ h }) {
  const [q, setQ] = useState('');
  const [r, setR] = useState(null);
  const run = async () => {
    if (!q.trim()) return;
    try { const x = await axios.post(`${API}/admin/willy/test`, { q }, h); setR(x.data); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  return (
    <div className={`${box} p-4 max-w-3xl space-y-3`}>
      <div className="text-[12px] text-white/55">Напишите вопрос так, как написал бы игрок — на любом языке. Willy покажет, что он сделает.</div>
      <div className="flex gap-2">
        <input className={inp} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && run()} placeholder="почему пропал товар со склада?" data-testid="willy-test-q" />
        <button className={`${btn} bg-violet-500 text-white`} onClick={run} data-testid="willy-test-run">Проверить</button>
      </div>
      {r && (
        <div className="space-y-2 text-sm" data-testid="willy-test-out">
          {r.q_ru !== q && <div className="text-white/60">По-русски: <span className="text-white">{r.q_ru}</span></div>}
          <div>Решение: <b className={r.rule ? 'text-amber-300' : 'text-emerald-300'}>{r.decision}</b> <span className="text-white/40 text-xs">(поиск: {r.engine === 'sem' ? 'по смыслу' : 'по словам'}; ответ от {Math.round(r.high * 100)}%, уточнение от {Math.round(r.low * 100)}%)</span></div>
          <div className="space-y-1">
            {r.top.map((t) => (
              <div key={t.id} className="flex items-center gap-2 text-[13px]">
                <div className="w-28 h-1.5 rounded bg-white/10 overflow-hidden"><div className="h-full bg-violet-400" style={{ width: `${Math.round(t.conf * 100)}%` }} /></div>
                <span className="w-10 text-right text-white/60">{Math.round(t.conf * 100)}%</span>
                <span>{t.title}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ───────────────────────────── Пробелы ─────────────────────────────
function Gaps({ h, onCreate }) {
  const [st, setSt] = useState('open');
  const [items, setItems] = useState(null);
  const [attach, setAttach] = useState({}); // gap id → search text
  const [found, setFound] = useState({});
  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/willy/gaps`, { ...h, params: { status: st } }); setItems(r.data.items); }
    catch { toast.error('Не удалось загрузить пробелы'); }
  }, [h, st]);
  useEffect(() => { load(); }, [load]);
  const act = async (g, action, answer_id) => {
    try { await axios.post(`${API}/admin/willy/gaps/${g.id}`, { action, answer_id }, h); toast.success(action === 'attach' ? 'Формулировка добавлена к ответу' : 'Готово'); load(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
  };
  const findAns = async (gid, text) => {
    setAttach((a) => ({ ...a, [gid]: text }));
    if (text.trim().length < 2) { setFound((f) => ({ ...f, [gid]: [] })); return; }
    const r = await axios.get(`${API}/admin/willy/answers`, { ...h, params: { q: text } });
    setFound((f) => ({ ...f, [gid]: r.data.items.slice(0, 6) }));
  };
  const why = { low: 'нет похожего ответа', medium: 'спросил «О чём вопрос?»', not_helped: '«Не помогло»' };
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <select className="bg-black/40 border border-white/15 rounded-lg px-2 py-1.5 text-xs" value={st} onChange={(e) => setSt(e.target.value)}>
          <option value="open">Открытые</option><option value="resolved">Добавлены к ответам</option><option value="dismissed">Скрытые</option><option value="all">Все</option>
        </select>
        <span className="text-[12px] text-white/45">Вопросы игроков, на которые Willy не нашёл уверенного ответа. Добавьте формулировку к ответу — и он начнёт отвечать.</span>
      </div>
      {(items || []).map((g) => (
        <div key={g.id} className={`${box} p-3`} data-testid={`willy-gap-${g.id}`}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <div className="text-sm text-white">{g.q_ru}</div>
              <div className="text-[11px] text-white/40 mt-0.5">×{g.count} · {why[g.why] || g.why} · {String(g.last_at || '').slice(0, 16).replace('T', ' ')}
                {g.best?.title && <> · ближе всего: «{g.best.title}» ({Math.round((g.best.conf || 0) * 100)}%)</>}</div>
              {(g.examples || []).length > 0 && <div className="text-[11px] text-white/35 mt-1">{g.examples.slice(0, 3).join(' · ')}</div>}
            </div>
            <div className="flex gap-1.5">
              {g.best?.answer_id && st === 'open' && <button className={`${btn} bg-emerald-500/20 text-emerald-100`} onClick={() => act(g, 'attach', g.best.answer_id)}>К «{(g.best.title || '').slice(0, 24)}»</button>}
              <button className={`${btn} bg-violet-500/25 text-violet-100`} onClick={() => onCreate(g.q_ru)}>Создать ответ</button>
              {st === 'open' ? <button className={`${btn} bg-white/5 text-white/60`} onClick={() => act(g, 'dismiss')}>Скрыть</button>
                : <button className={`${btn} bg-white/5 text-white/60`} onClick={() => act(g, 'reopen')}>Вернуть</button>}
            </div>
          </div>
          {st === 'open' && (
            <div className="mt-2">
              <input className={`${inp} text-xs py-1.5`} placeholder="Добавить к другому ответу — найдите его" value={attach[g.id] || ''} onChange={(e) => findAns(g.id, e.target.value)} />
              <div className="flex flex-wrap gap-1 mt-1">
                {(found[g.id] || []).map((a) => <button key={a.id} className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[11px] text-white/80 hover:bg-white/10" onClick={() => act(g, 'attach', a.id)}>+ {a.title}</button>)}
              </div>
            </div>
          )}
        </div>
      ))}
      {items && !items.length && <div className="text-center text-white/35 text-sm py-10">Пробелов нет</div>}
    </div>
  );
}

// ───────────────────────────── Статистика ─────────────────────────────
function Stats({ h }) {
  const [days, setDays] = useState(7);
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/willy/stats`, { ...h, params: { days } }); setS(r.data); }
    catch { toast.error('Не удалось загрузить статистику'); }
  }, [h, days]);
  useEffect(() => { load(); }, [load]);
  const reindex = async () => {
    setBusy(true);
    try { const r = await axios.post(`${API}/admin/willy/reindex`, {}, h); toast.success(`Индекс собран: ${r.data.answers} ответов, ${r.data.keyword_phrasings} формулировок${r.data.service ? ' · поиск по смыслу обновлён' : ''}`); }
    catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
    setBusy(false);
  };
  const tile = (l, v, cls = 'text-white') => (
    <div className={`${box} px-3 py-2`}><div className={`text-xl font-bold ${cls}`}>{v ?? '…'}</div><div className="text-[11px] text-white/45">{l}</div></div>
  );
  const pct = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : '—');
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <select className="bg-black/40 border border-white/15 rounded-lg px-2 py-1.5 text-xs" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[1, 7, 30, 90].map((d) => <option key={d} value={d}>за {d} дн.</option>)}
        </select>
        <button className={`${btn} bg-white/5 text-white/70`} onClick={load}><RefreshCw className="w-3.5 h-3.5" /> Обновить</button>
        <button className={`${btn} bg-violet-500/25 text-violet-100`} onClick={reindex} disabled={busy}>Пересобрать индекс</button>
      </div>
      {s && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {tile('вопросов', s.questions)}
            {tile('ответил сам', `${s.answers} · ${pct(s.answers, s.questions)}`, 'text-emerald-300')}
            {tile('уточнил «О чём вопрос?»', s.clarify, 'text-cyan-300')}
            {tile('передал людям', `${s.handoff} · ${pct(s.handoff, s.questions)}`, 'text-amber-300')}
            {tile('«Помогло»', s.helped, 'text-emerald-300')}
            {tile('«Не помогло»', s.not_helped, 'text-red-300')}
            {tile('чатов без человека', `${s.chats_without_human} из ${s.chats}`)}
            {tile('открытых пробелов', s.open_gaps, 'text-amber-200')}
          </div>
          <div className="grid md:grid-cols-3 gap-3">
            <div className={`${box} p-3`}>
              <div className="text-[12px] font-semibold text-white/80 mb-2">Почему передал людям</div>
              {s.reasons.length ? s.reasons.map((r) => <div key={r.reason} className="flex justify-between text-[13px] py-0.5"><span>{r.label}</span><b>{r.n}</b></div>) : <div className="text-white/35 text-xs">—</div>}
            </div>
            <div className={`${box} p-3`}>
              <div className="text-[12px] font-semibold text-white/80 mb-2">Частые ответы</div>
              {s.top.length ? s.top.map((t) => <div key={t.id} className="flex justify-between gap-2 text-[13px] py-0.5"><span className="truncate">{t.title}</span><b>{t.n}</b></div>) : <div className="text-white/35 text-xs">—</div>}
            </div>
            <div className={`${box} p-3`}>
              <div className="text-[12px] font-semibold text-white/80 mb-2">Языки и поиск</div>
              {Object.entries(s.langs || {}).map(([k, v]) => <div key={k} className="flex justify-between text-[13px] py-0.5"><span>{LANG_NAMES[k] || k}</span><b>{v}</b></div>)}
              <div className="text-[11px] text-white/45 mt-2">
                Поиск по смыслу: {!s.service?.configured ? 'не подключён (работает поиск по словам)' : s.service.ok ? `работает · ${s.service.phrasings || 0} формулировок` : 'не отвечает — работает поиск по словам'}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ───────────────────────────── Правила и пороги ─────────────────────────────
function Rules({ h }) {
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { axios.get(`${API}/admin/willy/settings`, h).then((r) => setS(r.data)).catch(() => toast.error('Ошибка загрузки')); }, [h]);
  if (!s) return <div className="text-white/40 text-sm">Загрузка…</div>;
  const setRule = (k, patch) => setS((x) => ({ ...x, rules: { ...x.rules, [k]: { ...x.rules[k], ...patch } } }));
  const save = async () => {
    setBusy(true);
    try {
      const r = await axios.put(`${API}/admin/willy/settings`, {
        enabled: s.enabled, high: s.high, low: s.low, sem_high: s.sem_high, sem_low: s.sem_low, handoff_on_low: s.handoff_on_low, rules: s.rules,
      }, h);
      setS((x) => ({ ...x, ...r.data })); toast.success('Сохранено');
    } catch (e) { toast.error(e.response?.data?.detail || 'Ошибка'); }
    setBusy(false);
  };
  const num = (k) => (
    <input type="number" step="0.01" min="0.05" max="0.99" className="w-20 bg-black/40 border border-white/15 rounded-lg px-2 py-1 text-sm" value={s[k]} onChange={(e) => setS((x) => ({ ...x, [k]: e.target.value }))} />
  );
  return (
    <div className="space-y-3 max-w-4xl">
      <div className={`${box} p-4 space-y-3`}>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!s.enabled} onChange={(e) => setS((x) => ({ ...x, enabled: e.target.checked }))} data-testid="willy-enabled-global" />
          Willy GRAM отвечает первым (выключено — все чаты сразу уходят агентам, как раньше)</label>
        <div className="grid md:grid-cols-2 gap-3 text-[13px] text-white/75">
          <div className="space-y-1.5">
            <div className="font-semibold text-white/85">Поиск по словам</div>
            <div className="flex items-center gap-2">Ответ, если совпадение от {num('high')}</div>
            <div className="flex items-center gap-2">«О чём вопрос?», если от {num('low')}</div>
          </div>
          <div className="space-y-1.5">
            <div className="font-semibold text-white/85">Поиск по смыслу (сервис willy)</div>
            <div className="flex items-center gap-2">Ответ, если близость от {num('sem_high')}</div>
            <div className="flex items-center gap-2">«О чём вопрос?», если от {num('sem_low')}</div>
          </div>
        </div>
        <label className="flex items-center gap-2 text-[13px] text-white/75"><input type="checkbox" checked={!!s.handoff_on_low} onChange={(e) => setS((x) => ({ ...x, handoff_on_low: e.target.checked }))} />
          Ниже порога — сразу человек («Нет в базе»). Выключено — всё равно предлагать темы.</label>
        <div className="text-[11px] text-white/40">«Не помогло» два раза подряд — всегда человек. Проверяйте пороги во вкладке «Проверить вопрос».</div>
      </div>
      <div className={`${box} p-4 space-y-3`}>
        <div className="text-[13px] font-semibold text-white/85">Когда сразу звать человека</div>
        {Object.keys(RULE_HELP).map((k) => {
          const r = s.rules?.[k] || {};
          return (
            <div key={k} className="border-t border-white/5 pt-2" data-testid={`willy-rule-${k}`}>
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2 text-sm min-w-[180px]"><input type="checkbox" checked={r.enabled !== false} onChange={(e) => setRule(k, { enabled: e.target.checked })} /> {s.reasons?.[k] || k}</label>
                <span className="text-[11px] text-white/45 flex-1">{RULE_HELP[k]}</span>
                {k === 'money' && <label className="flex items-center gap-1.5 text-[12px] text-amber-200"><input type="checkbox" checked={!!r.strict} onChange={(e) => setRule(k, { strict: e.target.checked })} /> Строго</label>}
              </div>
              <input className={`${inp} mt-1.5 text-xs py-1.5`} placeholder="Свои слова через запятую (по-русски)" defaultValue={(r.words || []).join(', ')}
                onBlur={(e) => setRule(k, { words: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) })} />
            </div>
          );
        })}
      </div>
      <button className={`${btn} bg-violet-500 hover:bg-violet-400 text-white`} onClick={save} disabled={busy} data-testid="willy-rules-save"><Save className="w-3.5 h-3.5" /> Сохранить</button>
    </div>
  );
}
