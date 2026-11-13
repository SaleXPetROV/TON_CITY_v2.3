/**
 * The «?» button of a screen: in the screen's header, next to its other buttons and of the same size.
 * It opens a sheet with the «Справочник» articles about this screen (GET /api/wiki/screen/{screen}).
 * Every screen has it except «Бизнесы».
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/context/LanguageContext';
import { wt, fill } from './wikiI18n';
import { wikiApi } from './WikiText';
import './wiki.css';

export default function WikiHelp({ screen, className = '' }) {
  const { lang } = useLanguage();
  const T = wt(lang);
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState(null);

  useEffect(() => {
    if (!open) return undefined;
    let alive = true;
    wikiApi(`/screen/${screen}?lang=${lang}`).then((d) => { if (alive) setItems(d.items || []); }).catch(() => { if (alive) setItems([]); });
    const esc = (e) => { if (e.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', esc);
    return () => { alive = false; window.removeEventListener('keydown', esc); };
  }, [open, screen, lang]);

  const go = (to) => { setOpen(false); navigate(to); };
  const name = T(`screens.${screen}`);
  return (
    <>
      <button type="button" className={`wk-q ${className}`} onClick={() => setOpen(true)} aria-label={fill(T('screen'), { title: name })}
        data-testid={`wiki-help-${screen}`}>?</button>
      {open && (
        <div className="wk">
          <div className="wk-sheet-bg" onClick={() => setOpen(false)} />
          <div className="wk-sheet" role="dialog" aria-label={fill(T('screen'), { title: name })} data-testid="wiki-help-sheet">
            <div className="wk-grab" />
            <div className="wk-sheet-h"><span>📖 {fill(T('screen'), { title: name })}</span>
              <button type="button" onClick={() => setOpen(false)} aria-label="✕">✕</button></div>
            {items == null ? <div className="wk-spin" /> : (
              <div className="wk-list">
                {items.map((a) => (
                  <button key={a.slug} type="button" className="wk-row" onClick={() => go(`/wiki/${a.slug}`)} data-testid={`wiki-help-item-${a.slug}`}>
                    <span className="i">{a.icon}</span>
                    <span className="x"><b>{a.title}</b><small>{a.summary}</small></span>
                  </button>
                ))}
              </div>
            )}
            <button type="button" className="wk-btn ghost wide" style={{ marginTop: 10 }} onClick={() => go('/wiki')} data-testid="wiki-help-all">{T('openAll')}</button>
          </div>
        </div>
      )}
    </>
  );
}
