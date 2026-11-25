/**
 * Админка → Задания: «Ежедневные и недельные цели» (backend/quests.py).
 * Что считается (купить / продать / смена / ремонт …), сколько нужно, награда, сложность, кому выдаётся
 * (только с бизнесом или всем), вкл/выкл, тексты RU/EN (остальные языки — LibreTranslate), новые цели,
 * сколько целей каждой сложности игрок получает в день.
 */
import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Loader2, Plus, Trash2, Save, Target, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent } from '@/components/ui/card';
import { formatErrorDetail } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const hdr = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token') || localStorage.getItem('ton_city_token')}` } });
const DIFF = { easy: 'Лёгкая', medium: 'Средняя', good: 'Сложная' };
const err = (e, d) => formatErrorDetail(e?.response?.data?.detail) || d;

const sel = 'bg-black/40 border border-white/10 rounded-md h-9 px-2 text-sm text-white';

function Field({ label, children, className = '' }) {
  return (
    <label className={`flex flex-col ${className}`}>
      <span className="text-[10px] text-text-muted mb-1">{label}</span>
      {children}
    </label>
  );
}

function GoalRow({ t, events, onSaved, onDeleted }) {
  const [d, setD] = useState(() => ({
    event: t.event, target: t.target, reward_city: t.reward_city, reward_xp: t.reward_xp, difficulty: t.difficulty || 'easy',
    requires_business: !!t.requires_business, active: t.active !== false,
    title_ru: t.title?.ru || '', title_en: t.title?.en || '', desc_ru: t.description?.ru || '', desc_en: t.description?.en || '',
  }));
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const set = (k) => (v) => setD((x) => ({ ...x, [k]: v }));
  const dirty = useMemo(() => (
    d.event !== t.event || +d.target !== +t.target || +d.reward_city !== +t.reward_city || +d.reward_xp !== +t.reward_xp
    || (t.kind === 'daily' && d.difficulty !== (t.difficulty || 'easy')) || d.requires_business !== !!t.requires_business
    || d.active !== (t.active !== false) || d.title_ru !== (t.title?.ru || '') || d.title_en !== (t.title?.en || '')
    || d.desc_ru !== (t.description?.ru || '') || d.desc_en !== (t.description?.en || '')
  ), [d, t]);

  const save = async () => {
    setBusy(true);
    try {
      const body = {};
      if (d.event !== t.event) body.event = d.event;
      ['target', 'reward_city', 'reward_xp'].forEach((k) => { if (+d[k] !== +t[k]) body[k] = Math.max(0, parseInt(d[k], 10) || 0); });
      if (t.kind === 'daily' && d.difficulty !== (t.difficulty || 'easy')) body.difficulty = d.difficulty;
      if (d.requires_business !== !!t.requires_business) body.requires_business = d.requires_business;
      if (d.active !== (t.active !== false)) body.active = d.active;
      const title = {}; const description = {};
      if (d.title_ru.trim() && d.title_ru !== (t.title?.ru || '')) title.ru = d.title_ru.trim();
      if (d.title_en.trim() && d.title_en !== (t.title?.en || '')) title.en = d.title_en.trim();
      if (d.desc_ru.trim() && d.desc_ru !== (t.description?.ru || '')) description.ru = d.desc_ru.trim();
      if (d.desc_en.trim() && d.desc_en !== (t.description?.en || '')) description.en = d.desc_en.trim();
      if (Object.keys(title).length) body.title = title;
      if (Object.keys(description).length) body.description = description;
      await axios.put(`${API}/admin/quests/templates/${t.id}`, body, hdr());
      toast.success('Цель сохранена');
      onSaved();
    } catch (e) {
      toast.error(err(e, 'Не удалось сохранить'));
    } finally { setBusy(false); }
  };

  const del = async () => {
    if (!window.confirm(`Удалить цель «${t.title?.ru || t.title?.en || t.id}»?`)) return;
    try { await axios.delete(`${API}/admin/quests/templates/${t.id}`, hdr()); toast.success('Цель удалена'); onDeleted(); } catch (e) { toast.error(err(e, 'Не удалось удалить')); }
  };

  return (
    <div className={`rounded-xl border p-3 space-y-2 ${d.active ? 'border-white/10 bg-white/[0.02]' : 'border-white/5 bg-black/20 opacity-70'}`} data-testid={`quest-tpl-${t.id}`}>
      <div className="flex items-start gap-2">
        <Switch checked={d.active} onCheckedChange={set('active')} data-testid={`quest-tpl-active-${t.id}`} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-white truncate">{d.title_ru || d.title_en || t.id}</div>
          <div className="text-[10px] text-text-muted">{t.id}{t.custom ? ' · своя' : ' · встроенная'}{d.active ? '' : ' · выключена'}</div>
        </div>
        <button type="button" onClick={() => setOpen((v) => !v)} className="text-[11px] text-cyber-cyan flex items-center gap-0.5 shrink-0">
          Тексты {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>
      <div className="flex flex-wrap gap-2 items-end">
        <Field label="Что нужно сделать">
          <select value={d.event} onChange={(e) => set('event')(e.target.value)} className={`${sel} min-w-[220px]`}>
            {Object.entries(events).map(([k, v]) => <option key={k} value={k}>{v.ru}</option>)}
          </select>
        </Field>
        <Field label="Сколько"><Input type="number" min="1" value={d.target} onChange={(e) => set('target')(e.target.value)} className="w-20 bg-black/40 border-white/10 h-9" data-testid={`quest-tpl-target-${t.id}`} /></Field>
        <Field label="Награда $CITY"><Input type="number" min="0" value={d.reward_city} onChange={(e) => set('reward_city')(e.target.value)} className="w-24 bg-black/40 border-white/10 h-9" /></Field>
        <Field label="XP"><Input type="number" min="0" value={d.reward_xp} onChange={(e) => set('reward_xp')(e.target.value)} className="w-20 bg-black/40 border-white/10 h-9" /></Field>
        {t.kind === 'daily' && (
          <Field label="Сложность">
            <select value={d.difficulty} onChange={(e) => set('difficulty')(e.target.value)} className={sel}>
              {Object.entries(DIFF).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
        )}
        <label className="flex items-center gap-2 h-9 text-[11px] text-white/80">
          <Switch checked={d.requires_business} onCheckedChange={set('requires_business')} />
          Только игрокам с бизнесом
        </label>
      </div>
      {open && (
        <div className="grid md:grid-cols-2 gap-2">
          <Field label="Название (RU)"><Input value={d.title_ru} onChange={(e) => set('title_ru')(e.target.value)} className="bg-black/40 border-white/10 h-9" /></Field>
          <Field label="Название (EN) — из него переводятся остальные языки"><Input value={d.title_en} onChange={(e) => set('title_en')(e.target.value)} className="bg-black/40 border-white/10 h-9" /></Field>
          <Field label="Описание (RU)"><Input value={d.desc_ru} onChange={(e) => set('desc_ru')(e.target.value)} className="bg-black/40 border-white/10 h-9" /></Field>
          <Field label="Описание (EN)"><Input value={d.desc_en} onChange={(e) => set('desc_en')(e.target.value)} className="bg-black/40 border-white/10 h-9" /></Field>
        </div>
      )}
      <div className="flex items-center gap-2">
        <Button size="sm" disabled={!dirty || busy} onClick={save} className="h-8 bg-yellow-500 text-black hover:bg-yellow-400" data-testid={`quest-tpl-save-${t.id}`}>
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Save className="w-3.5 h-3.5 mr-1" />Сохранить</>}
        </Button>
        {t.custom && (
          <Button size="sm" variant="outline" onClick={del} className="h-8 border-red-500/40 text-red-300"><Trash2 className="w-3.5 h-3.5 mr-1" />Удалить</Button>
        )}
        {+d.target !== +t.target && <span className="text-[10px] text-text-muted">Число в названии и описании поменяется само.</span>}
      </div>
    </div>
  );
}

function NewGoal({ events, kind, onCreated }) {
  const [d, setD] = useState({ event: 'market_buy', target: 10, reward_city: 5, reward_xp: 10, difficulty: 'easy', title_ru: '', title_en: '', desc_ru: '' });
  const [busy, setBusy] = useState(false);
  const set = (k) => (v) => setD((x) => ({ ...x, [k]: v }));
  const create = async () => {
    if (!d.title_ru.trim() && !d.title_en.trim()) { toast.error('Введите название'); return; }
    setBusy(true);
    try {
      await axios.post(`${API}/admin/quests/templates`, {
        kind, difficulty: d.difficulty, event: d.event, target: parseInt(d.target, 10) || 1,
        reward_city: parseInt(d.reward_city, 10) || 0, reward_xp: parseInt(d.reward_xp, 10) || 0,
        requires_business: events[d.event]?.business,
        title: { ru: d.title_ru.trim(), en: d.title_en.trim() }, description: d.desc_ru.trim() ? { ru: d.desc_ru.trim() } : undefined,
      }, hdr());
      toast.success('Цель добавлена — другие языки переведутся автоматически');
      setD((x) => ({ ...x, title_ru: '', title_en: '', desc_ru: '' }));
      onCreated();
    } catch (e) {
      toast.error(err(e, 'Не удалось добавить'));
    } finally { setBusy(false); }
  };
  return (
    <div className="rounded-xl border border-dashed border-yellow-500/40 p-3 space-y-2" data-testid={`quest-new-${kind}`}>
      <div className="text-xs font-bold text-yellow-300">Новая {kind === 'daily' ? 'ежедневная' : 'недельная'} цель</div>
      <div className="flex flex-wrap gap-2 items-end">
        <Field label="Что нужно сделать">
          <select value={d.event} onChange={(e) => set('event')(e.target.value)} className={`${sel} min-w-[220px]`}>
            {Object.entries(events).map(([k, v]) => <option key={k} value={k}>{v.ru}{v.business ? ' — нужен бизнес' : ''}</option>)}
          </select>
        </Field>
        <Field label="Сколько"><Input type="number" min="1" value={d.target} onChange={(e) => set('target')(e.target.value)} className="w-20 bg-black/40 border-white/10 h-9" /></Field>
        <Field label="Награда $CITY"><Input type="number" min="0" value={d.reward_city} onChange={(e) => set('reward_city')(e.target.value)} className="w-24 bg-black/40 border-white/10 h-9" /></Field>
        <Field label="XP"><Input type="number" min="0" value={d.reward_xp} onChange={(e) => set('reward_xp')(e.target.value)} className="w-20 bg-black/40 border-white/10 h-9" /></Field>
        {kind === 'daily' && (
          <Field label="Сложность">
            <select value={d.difficulty} onChange={(e) => set('difficulty')(e.target.value)} className={sel}>
              {Object.entries(DIFF).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
        )}
      </div>
      <div className="grid md:grid-cols-3 gap-2">
        <Field label="Название (RU)"><Input value={d.title_ru} onChange={(e) => set('title_ru')(e.target.value)} placeholder={`Например: Купите ${d.target} единиц`} className="bg-black/40 border-white/10 h-9" data-testid={`quest-new-title-${kind}`} /></Field>
        <Field label="Название (EN), можно пусто"><Input value={d.title_en} onChange={(e) => set('title_en')(e.target.value)} className="bg-black/40 border-white/10 h-9" /></Field>
        <Field label="Описание (RU), можно пусто"><Input value={d.desc_ru} onChange={(e) => set('desc_ru')(e.target.value)} className="bg-black/40 border-white/10 h-9" /></Field>
      </div>
      <Button size="sm" disabled={busy} onClick={create} className="h-8 bg-yellow-500 text-black hover:bg-yellow-400" data-testid={`quest-new-add-${kind}`}>
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Plus className="w-3.5 h-3.5 mr-1" />Добавить цель</>}
      </Button>
    </div>
  );
}

export default function AdminDailyQuestsCard() {
  const [tpls, setTpls] = useState(null);
  const [meta, setMeta] = useState(null);
  const [counts, setCounts] = useState({ easy: 1, medium: 1, good: 1 });
  const [cap, setCap] = useState(0);
  const [savingCfg, setSavingCfg] = useState(false);
  const [tab, setTab] = useState('daily');

  const load = async () => {
    try {
      const [t, m] = await Promise.all([axios.get(`${API}/admin/quests/templates`, hdr()), axios.get(`${API}/admin/quests/meta`, hdr())]);
      setTpls(t.data.templates || []);
      setMeta(m.data);
      setCounts(m.data.daily_per_difficulty || { easy: 1, medium: 1, good: 1 });
      setCap(m.data.daily_bonus_cap_city || 0);
    } catch (e) { toast.error(err(e, 'Не удалось загрузить цели')); }
  };
  useEffect(() => { load(); }, []);

  const saveCfg = async () => {
    setSavingCfg(true);
    try {
      await axios.put(`${API}/admin/quests/settings`, {
        daily_per_difficulty: Object.fromEntries(Object.entries(counts).map(([k, v]) => [k, parseInt(v, 10) || 0])),
        daily_bonus_cap_city: parseInt(cap, 10) || 0,
      }, hdr());
      toast.success('Сохранено. Новое количество целей — с завтрашнего дня (00:00 МСК)');
    } catch (e) { toast.error(err(e, 'Не удалось сохранить')); } finally { setSavingCfg(false); }
  };

  if (!tpls || !meta) return null;
  const list = tpls.filter((t) => t.kind === tab).sort((a, b) => (DIFF[a.difficulty] ? Object.keys(DIFF).indexOf(a.difficulty) : 9)
    - (DIFF[b.difficulty] ? Object.keys(DIFF).indexOf(b.difficulty) : 9) || String(a.id).localeCompare(String(b.id)));
  const activeDaily = tpls.filter((t) => t.kind === 'daily' && t.active !== false);

  return (
    <Card className="glass-panel border-yellow-500/30" data-testid="admin-daily-quests-card">
      <CardContent className="p-4 space-y-4">
        <h3 className="font-bold text-white text-sm uppercase tracking-wide flex items-center gap-2"><Target className="w-4 h-4 text-yellow-400" />Ежедневные и недельные цели</h3>
        <p className="text-xs text-text-muted">
          Блок «Сегодня» / «Неделя» на странице «Задания». Каждый день игрок получает случайные цели из включённых: столько каждой сложности, сколько указано ниже.
          Цели «только игрокам с бизнесом» получают только владельцы бизнеса. Изменения выдачи действуют с ближайших 00:00 МСК; «сколько» и награда — сразу.
        </p>

        <div className="rounded-xl border border-white/10 p-3 flex flex-wrap gap-3 items-end" data-testid="quest-daily-counts">
          {Object.entries(DIFF).map(([k, v]) => (
            <Field key={k} label={`${v}: целей в день (вкл.: ${activeDaily.filter((t) => t.difficulty === k).length})`}>
              <Input type="number" min="0" max="5" value={counts[k]} onChange={(e) => setCounts((c) => ({ ...c, [k]: e.target.value }))} className="w-24 bg-black/40 border-white/10 h-9" />
            </Field>
          ))}
          <Field label="Максимум наград за цели в день на игрока, $CITY">
            <Input type="number" min="0" value={cap} onChange={(e) => setCap(e.target.value)} className="w-28 bg-black/40 border-white/10 h-9" />
          </Field>
          <Button size="sm" disabled={savingCfg} onClick={saveCfg} className="h-9 bg-yellow-500 text-black hover:bg-yellow-400" data-testid="quest-daily-counts-save">
            {savingCfg ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Сохранить'}
          </Button>
        </div>

        <div className="flex gap-2">
          {[['daily', 'Ежедневные'], ['weekly', 'Недельные']].map(([k, v]) => (
            <button key={k} type="button" onClick={() => setTab(k)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-bold ${tab === k ? 'bg-yellow-500/20 border-yellow-400/60 text-white' : 'border-white/10 text-white/60'}`}>
              {v} · {tpls.filter((t) => t.kind === k).length}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          {list.map((t) => <GoalRow key={`${t.id}:${t.target}:${t.reward_city}:${t.active}:${t.title?.ru}`} t={t} events={meta.events} onSaved={load} onDeleted={load} />)}
        </div>
        <NewGoal events={meta.events} kind={tab} onCreated={load} />
      </CardContent>
    </Card>
  );
}
