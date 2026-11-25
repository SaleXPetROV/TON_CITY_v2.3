/**
 * «Показать на деле» — after a press in an article the player is taken to the right screen and the real buttons
 * are framed one by one. Unlike the guide nothing is blocked: the screen works as usual, the frame only shows
 * where to look («Показ», dashed) or what to press («Действие», solid — the step moves on after that press).
 *
 * startWikiShow({slug, title, route, steps:[{sel:[...], tap, text}]}, vars) — from the article page.
 * The run survives a page change (sessionStorage), so a step can open another screen.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLanguage } from '@/context/LanguageContext';
import { wt, fill } from './wikiI18n';
import './wiki.css';

const KEY = 'gc_wiki_show';
const EVT = 'gc:wiki-show';

const tpl = (s, v) => String(s || '').replace(/\{(\w+)\}/g, (m, k) => (v && v[k] != null && v[k] !== '' ? v[k] : m));

export function startWikiShow(show, vars) {
  const run = { ...show, vars: vars || {}, i: 0 };
  try { sessionStorage.setItem(KEY, JSON.stringify(run)); } catch { /* private mode */ }
  window.dispatchEvent(new Event(EVT));
}

function load() {
  try { return JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch { return null; }
}
function save(run) {
  try { if (run) sessionStorage.setItem(KEY, JSON.stringify(run)); else sessionStorage.removeItem(KEY); } catch { /* */ }
}

function visible(el) {
  if (!el) return false;
  const r = el.getBoundingClientRect();
  if (r.width < 2 || r.height < 2) return false;
  const cs = getComputedStyle(el);
  return cs.visibility !== 'hidden' && cs.display !== 'none' && Number(cs.opacity) > 0.05;
}

export function findTarget(sels, vars) {
  for (const s of sels || []) {
    const q = tpl(s, vars);
    if (/\{\w+\}/.test(q)) continue; // a value we do not know (no business yet)
    let els = [];
    try { els = Array.from(document.querySelectorAll(q)); } catch { els = []; }
    const el = els.find(visible);
    if (el) return el;
  }
  return null;
}

export default function WikiShow() {
  const { lang } = useLanguage();
  const T = wt(lang);
  const navigate = useNavigate();
  const loc = useLocation();
  const [run, setRun] = useState(load);
  const [rect, setRect] = useState(null);
  const [missing, setMissing] = useState(false);
  const elRef = useRef(null);
  const scrolled = useRef(-1);

  useEffect(() => {
    const on = () => setRun(load());
    window.addEventListener(EVT, on);
    return () => window.removeEventListener(EVT, on);
  }, []);

  const stop = useCallback((toArticle) => {
    const slug = run?.slug;
    save(null);
    setRun(null);
    setRect(null);
    if (toArticle && slug) navigate(`/wiki/${slug}`);
  }, [run, navigate]);

  const next = useCallback(() => {
    setRun((r) => {
      if (!r) return r;
      if (r.i + 1 >= (r.steps || []).length) { save(null); setRect(null); return null; }
      const n = { ...r, i: r.i + 1 };
      save(n);
      return n;
    });
    setMissing(false);
    scrolled.current = -1;
  }, []);

  const step = run ? (run.steps || [])[run.i] : null;
  const route = run ? tpl(run.route, run.vars) : '';

  // the run opens its screen once; after that the player may go anywhere (the sheet stays until «Готово» / «К статье»)
  useEffect(() => {
    if (!run || !route || run.navd) return;
    const n = { ...run, navd: true };
    save(n);
    setRun(n);
    const [p, q] = route.split('?');
    if (loc.pathname !== p || (q && !loc.search.includes(q))) navigate(route);
  }, [run, route, loc.pathname, loc.search, navigate]);

  // follow the framed button
  useEffect(() => {
    if (!step) return undefined;
    let tries = 0;
    let gone = null;
    const tick = () => {
      const el = findTarget(step.sel, run.vars);
      elRef.current = el;
      if (el) {
        if (scrolled.current !== run.i) {
          scrolled.current = run.i;
          el.scrollIntoView({ block: 'center', behavior: 'smooth' });
        }
        const r = el.getBoundingClientRect();
        setRect({ x: r.left - 4, y: r.top - 4, w: r.width + 8, h: r.height + 8 });
        setMissing(false);
      } else if (++tries > 16 && !gone) {
        setRect(null);
        setMissing(true);
        gone = setTimeout(next, 1800);
      }
    };
    tick();
    const id = setInterval(tick, 250);
    return () => { clearInterval(id); if (gone) clearTimeout(gone); };
  }, [step, run, next]);

  // «Действие»: the step moves on after the player presses the framed button (the press itself works as usual)
  useEffect(() => {
    if (!step?.tap) return undefined;
    const on = (e) => {
      const el = elRef.current;
      if (el && (el === e.target || el.contains(e.target))) setTimeout(next, 450);
    };
    document.addEventListener('click', on, true);
    return () => document.removeEventListener('click', on, true);
  }, [step, next]);

  if (!run || !step) return null;
  const total = (run.steps || []).length;
  const last = run.i + 1 >= total;
  const top = rect && rect.y + rect.h > window.innerHeight * 0.6;
  return (
    <>
      {rect && (
        <svg className="wk-show-dim" width="100%" height="100%" aria-hidden="true">
          <defs><mask id="wk-mask"><rect width="100%" height="100%" fill="#fff" /><rect x={rect.x} y={rect.y} width={rect.w} height={rect.h} rx="12" fill="#000" /></mask></defs>
          <rect width="100%" height="100%" fill="rgba(3,6,14,.55)" mask="url(#wk-mask)" />
        </svg>
      )}
      {rect && <div className={`wk-show-ring ${step.tap ? '' : 'look'}`} style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }} />}
      <div className={`wk-show-sheet ${top ? 'top' : ''}`} role="dialog" aria-live="polite" data-testid="wiki-show">
        <div className="wk-show-h"><span>📖 {T('help')} · {run.title}</span><small>{fill(T('step'), { n: run.i + 1, total })}</small></div>
        <div className="wk-show-bar"><i style={{ width: `${((run.i + 1) / total) * 100}%` }} /></div>
        <p className="wk-show-t">
          <span className={`wk-show-k ${step.tap ? '' : 'look'}`}>{step.tap ? T('kindTap') : T('kindLook')}</span>
          {missing ? T('missing') : step.text}
        </p>
        <div className="wk-show-f">
          <button type="button" className="l" onClick={() => stop(true)} data-testid="wiki-show-back">{T('toArticle')}</button>
          {step.tap && !missing
            ? <span className="hint">{T('tapHint')}</span>
            : <button type="button" className="wk-btn" onClick={() => (last ? stop(false) : next())} data-testid="wiki-show-next">{last ? T('done') : T('next')}</button>}
        </div>
      </div>
    </>
  );
}
