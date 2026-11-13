/**
 * Админка → «Справочник»: статьи, разделы, порядок, проверки «Что нужно», «Показать на деле».
 * Пишем по-русски; «Перевести» заполняет 8 языков черновиком LibreTranslate — их правят и сохраняют.
 * Каждое сохранение хранит прошлую версию («История версий» — вернуть в форму).
 * Цифры пишутся как {{tax_t1}} и т. п. — подставляются при показе из настроек игры (список ниже).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const LANG_NAMES = { ru: 'Русский', en: 'English', es: 'Español', zh: '中文', fr: 'Français', de: 'Deutsch', ja: '日本語', ko: '한국어', id: 'Indonesia' };
const SCREENS = ['map', 'maps', 'resources', 'trading', 'community', 'chat', 'tasks', 'city-pass', 'credit', 'history', 'settings', 'security', 'marketplace', 'leaderboard', 'analytics'];
const SCREEN_RU = { map: 'Карта', maps: 'Карты', resources: 'Склад', trading: 'Торговля', community: 'Общение', chat: 'Чат', tasks: 'Задания', 'city-pass': 'City Pass', credit: 'Кредит', history: 'История', settings: 'Настройки', security: 'Безопасность', marketplace: 'Маркетплейс', leaderboard: 'Рейтинг', analytics: 'Аналитика' };
const HELP = 'Разметка: строка «- …» — пункт, «1. …» — шаг, «> …» — заметка, «# …» — подзаголовок, «= Слово | значение» — словарик, [[table:taxes]] — живая таблица (taxes, weights, durability, repair, credit). Внутри строки: **жирный**, [[slug|текст]] — ссылка на статью, {{tax_t1}} — живое число.';

const empty = () => ({ slug: '', section: 'start', icon: '📄', screens: [], needs: [], related: [], show: null, published: true, i18n: { ru: { t: '', s: '', b: '', show: [] } } });

export default function AdminWiki({ token }) {
  const h = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);
  const [all, setAll] = useState(null);
  const [cur, setCur] = useState(null);
  const [isNew, setIsNew] = useState(false);
  const [lg, setLg] = useState('ru');
  const [busy, setBusy] = useState(false);
  const [versions, setVersions] = useState(null);
  const [q, setQ] = useState('');
  const [showJson, setShowJson] = useState('');

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/wiki`, h); setAll(r.data); }
    catch { toast.error('Не удалось загрузить Справочник'); }
  }, [h]);
  useEffect(() => { load(); }, [load]);

  const open = (a) => {
    const c = JSON.parse(JSON.stringify(a));
    c.i18n = c.i18n || {};
    setCur(c); setIsNew(false); setLg('ru'); setVersions(null);
    setShowJson(c.show ? JSON.stringify(c.show, null, 1) : '');
  };
  const create = () => { setCur(empty()); setIsNew(true); setLg('ru'); setVersions(null); setShowJson(''); };
  const tx = (k) => cur?.i18n?.[lg]?.[k] ?? (k === 'show' ? [] : '');
  const setTx = (k, v) => setCur((c) => ({ ...c, i18n: { ...c.i18n, [lg]: { ...(c.i18n[lg] || {}), [k]: v } } }));
  const toggle = (k, v) => setCur((c) => ({ ...c, [k]: c[k].includes(v) ? c[k].filter((x) => x !== v) : [...c[k], v] }));

  const save = async () => {
    let show = null;
    if (showJson.trim()) {
      try { show = JSON.parse(showJson); } catch { toast.error('«Показать на деле»: неверный JSON'); return; }
    }
    const body = { ...cur, show };
    setBusy(true);
    try {
      if (isNew) { await axios.post(`${API}/admin/wiki`, body, h); setIsNew(false); }
      else await axios.put(`${API}/admin/wiki/${cur.slug}`, body, h);
      toast.success('Сохранено'); await load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Ошибка сохранения'); }
    setBusy(false);
  };
  const hide = async () => {
    if (!window.confirm(`Скрыть статью «${cur.i18n?.ru?.t || cur.slug}»? Её можно вернуть: «Опубликована» → Сохранить.`)) return;
    try { await axios.delete(`${API}/admin/wiki/${cur.slug}`, h); toast.success('Статья скрыта'); setCur(null); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || 'Ошибка'); }
  };
  const translate = async () => {
    const ru = cur.i18n.ru || {};
    if (!ru.t) { toast.error('Сначала напишите русский текст'); return; }
    setBusy(true);
    try {
      const r = await axios.post(`${API}/admin/wiki/translate`, { t: ru.t || '', s: ru.s || '', b: ru.b || '', show: ru.show || [] }, h);
      setCur((c) => ({ ...c, i18n: { ...c.i18n, ...r.data.drafts } }));
      const errs = Object.keys(r.data.errors || {});
      toast.success(`Черновики: ${Object.keys(r.data.drafts || {}).length} языков${errs.length ? ` · не вышло: ${errs.join(', ')}` : ''}. Проверьте и сохраните.`);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Перевод не удался'); }
    setBusy(false);
  };
  const loadVersions = async () => {
    try { const r = await axios.get(`${API}/admin/wiki/${cur.slug}/versions`, h); setVersions(r.data.items || []); }
    catch { toast.error('Не удалось загрузить версии'); }
  };

  if (!all) return <div className="text-sm text-text-muted">Загрузка…</div>;
  const items = all.items.filter((a) => !q || (a.slug + (a.i18n?.ru?.t || '')).toLowerCase().includes(q.toLowerCase()));
  const missing = (a) => all.langs.filter((l) => !(a.i18n?.[l]?.t && a.i18n?.[l]?.b));

  return (
    <div className="grid lg:grid-cols-[320px_1fr] gap-4" data-testid="admin-wiki">
      <Card className="glass-panel border-white/10">
        <CardHeader className="pb-2"><CardTitle className="text-base text-white flex items-center justify-between">Статьи · {all.items.length}
          <Button size="sm" onClick={create} data-testid="admin-wiki-new">+ Статья</Button></CardTitle></CardHeader>
        <CardContent className="space-y-2">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск по названию" className="bg-black/40 border-white/10 h-9" />
          <div className="max-h-[70vh] overflow-y-auto space-y-3 pr-1">
            {all.sections.map((s) => (
              <div key={s.id}>
                <div className="text-[11px] uppercase tracking-wider text-text-muted mb-1">{s.icon} {s.title}</div>
                {items.filter((a) => a.section === s.id).map((a) => (
                  <button key={a.slug} type="button" onClick={() => open(a)} data-testid={`admin-wiki-item-${a.slug}`}
                    className={`w-full text-left px-2 py-1.5 rounded-lg text-sm flex items-center gap-2 ${cur?.slug === a.slug ? 'bg-cyan-500/15 text-white' : 'text-white/80 hover:bg-white/5'} ${a.published === false ? 'opacity-50' : ''}`}>
                    <span>{a.icon}</span><span className="flex-1 truncate">{a.i18n?.ru?.t || a.slug}</span>
                    {missing(a).length > 0 && <span className="text-[10px] text-amber-300" title={`Нет перевода: ${missing(a).join(', ')}`}>−{missing(a).length}</span>}
                    {a.origin === 'admin' && <span className="text-[10px] text-cyan-300" title="Правилась в админке">✎</span>}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {!cur ? (
        <Card className="glass-panel border-white/10"><CardContent className="p-6 text-sm text-text-muted space-y-2">
          <p>Выберите статью слева или создайте новую.</p>
          <p>Статья одна для игры, сайта (/wiki), .md и ответов Willy GRAM. Цифры — живые: пишите {'{{переменная}}'}.</p>
          <p className="text-xs">Отзывы игроков: 👍 / 👎 видны у каждой статьи.</p>
        </CardContent></Card>
      ) : (
        <Card className="glass-panel border-white/10">
          <CardHeader className="pb-2"><CardTitle className="text-base text-white">{isNew ? 'Новая статья' : `${cur.icon} ${cur.i18n?.ru?.t || cur.slug}`}
            {!isNew && <span className="ml-2 text-xs text-text-muted font-normal">👍 {cur.fb_yes || 0} · 👎 {cur.fb_no || 0} · <a className="text-cyan-300" href={`/wiki/${cur.slug}`} target="_blank" rel="noreferrer">открыть</a></span>}
          </CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid sm:grid-cols-4 gap-2">
              <label className="text-xs text-text-muted space-y-1"><span>Адрес (латиницей)</span>
                <Input value={cur.slug} disabled={!isNew} onChange={(e) => setCur((c) => ({ ...c, slug: e.target.value }))} className="bg-black/40 border-white/10 h-9" data-testid="admin-wiki-slug" /></label>
              <label className="text-xs text-text-muted space-y-1"><span>Раздел</span>
                <select value={cur.section} onChange={(e) => setCur((c) => ({ ...c, section: e.target.value }))} className="w-full h-9 rounded-md bg-black/40 border border-white/10 text-white text-sm px-2">
                  {all.sections.map((s) => <option key={s.id} value={s.id}>{s.icon} {s.title}</option>)}
                </select></label>
              <label className="text-xs text-text-muted space-y-1"><span>Значок</span>
                <Input value={cur.icon} onChange={(e) => setCur((c) => ({ ...c, icon: e.target.value }))} className="bg-black/40 border-white/10 h-9" /></label>
              <label className="text-xs text-text-muted space-y-1"><span>Порядок</span>
                <Input type="number" value={cur.order ?? 0} onChange={(e) => setCur((c) => ({ ...c, order: Number(e.target.value) }))} className="bg-black/40 border-white/10 h-9" /></label>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {all.langs.map((l) => (
                <button key={l} type="button" onClick={() => setLg(l)} data-testid={`admin-wiki-lang-${l}`}
                  className={`px-2.5 py-1 rounded-lg text-xs border ${lg === l ? 'border-cyan-400 bg-cyan-500/15 text-white' : 'border-white/10 text-white/70'} ${cur.i18n?.[l]?.t ? '' : 'italic opacity-70'}`}>{LANG_NAMES[l]}</button>
              ))}
              <Button size="sm" variant="outline" className="ml-auto border-white/15" disabled={busy} onClick={translate} data-testid="admin-wiki-translate">Перевести с русского</Button>
            </div>

            <div className="space-y-2">
              <Input value={tx('t')} onChange={(e) => setTx('t', e.target.value)} placeholder="Заголовок" className="bg-black/40 border-white/10" data-testid="admin-wiki-title" />
              <Input value={tx('s')} onChange={(e) => setTx('s', e.target.value)} placeholder="Коротко (одна строка в списке)" className="bg-black/40 border-white/10" />
              <textarea value={tx('b')} onChange={(e) => setTx('b', e.target.value)} rows={14} placeholder="Текст статьи"
                className="w-full rounded-md bg-black/40 border border-white/10 text-white text-sm p-3 font-mono leading-relaxed" data-testid="admin-wiki-body" />
              <p className="text-[11px] text-text-muted">{HELP}</p>
              {cur.show && (
                <textarea value={(tx('show') || []).join('\n')} onChange={(e) => setTx('show', e.target.value.split('\n'))} rows={3}
                  placeholder="Тексты шагов «Показать на деле» — по строке на шаг"
                  className="w-full rounded-md bg-black/40 border border-white/10 text-white text-sm p-2" />
              )}
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-text-muted mb-1">Кнопка «?» на экранах</div>
                <div className="flex flex-wrap gap-1.5">{SCREENS.map((s) => (
                  <button key={s} type="button" onClick={() => toggle('screens', s)} className={`px-2 py-1 rounded-md text-xs border ${cur.screens.includes(s) ? 'border-cyan-400 text-white bg-cyan-500/10' : 'border-white/10 text-white/60'}`}>{SCREEN_RU[s]}</button>
                ))}</div>
              </div>
              <div>
                <div className="text-xs text-text-muted mb-1">«Что нужно» — проверки аккаунта</div>
                <div className="flex flex-wrap gap-1.5">{all.checks.map((c) => (
                  <button key={c.id} type="button" onClick={() => toggle('needs', c.id)} className={`px-2 py-1 rounded-md text-xs border ${cur.needs.includes(c.id) ? 'border-cyan-400 text-white bg-cyan-500/10' : 'border-white/10 text-white/60'}`}>{c.title}</button>
                ))}</div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <label className="text-xs text-text-muted space-y-1 block"><span>Читайте также (адреса через запятую)</span>
                <Input value={(cur.related || []).join(', ')} onChange={(e) => setCur((c) => ({ ...c, related: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) }))} className="bg-black/40 border-white/10 h-9" /></label>
              <label className="text-xs text-text-muted space-y-1 block"><span>«Показать на деле» (JSON: route + steps с селекторами кнопок)</span>
                <textarea value={showJson} onChange={(e) => { setShowJson(e.target.value); setCur((c) => ({ ...c, show: e.target.value.trim() ? (c.show || {}) : null })); }} rows={3}
                  placeholder={'{"route": "/trading", "steps": [{"sel": ["[data-testid=...]"], "tap": true}]}'}
                  className="w-full rounded-md bg-black/40 border border-white/10 text-white text-xs p-2 font-mono" /></label>
            </div>

            <label className="flex items-center gap-2 text-sm text-white/80"><input type="checkbox" checked={cur.published !== false} onChange={(e) => setCur((c) => ({ ...c, published: e.target.checked }))} /> Опубликована</label>
            <label className="flex items-center gap-2 text-sm text-white/80"><input type="checkbox" checked={!!cur.mark_new} onChange={(e) => setCur((c) => ({ ...c, mark_new: e.target.checked }))} /> Пометить «новое» на 14 дней</label>

            <div className="flex flex-wrap gap-2">
              <Button disabled={busy} onClick={save} data-testid="admin-wiki-save">Сохранить</Button>
              {!isNew && <Button variant="outline" className="border-white/15" onClick={loadVersions}>История версий</Button>}
              {!isNew && <Button variant="outline" className="border-red-500/40 text-red-300 ml-auto" onClick={hide}>Скрыть статью</Button>}
            </div>
            {versions && (
              <div className="space-y-1 text-xs">
                {versions.length === 0 && <div className="text-text-muted">Прошлых версий нет.</div>}
                {versions.map((v) => (
                  <div key={v.at} className="flex items-center justify-between gap-2 border-t border-white/5 py-1">
                    <span className="text-text-muted">{new Date(v.at).toLocaleString('ru-RU')}</span>
                    <Button size="sm" variant="outline" className="h-7 border-white/15" onClick={() => { open({ ...v.doc }); toast('Версия загружена в форму — сохраните, чтобы вернуть'); }}>В форму</Button>
                  </div>
                ))}
              </div>
            )}
            <details className="text-xs text-text-muted"><summary className="cursor-pointer">Живые числа ({Object.keys(all.vars).length})</summary>
              <div className="grid sm:grid-cols-2 gap-x-4 mt-1">{Object.entries(all.vars).map(([k, v]) => <code key={k}>{`{{${k}}}`} = {String(v)}</code>)}</div>
            </details>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
