/** Screen texts translated by the server's LibreTranslate.
 *  The Russian source of a namespace lives on the server (backend/ui_i18n.py); GET /api/i18n/{ns}?lang= returns it in
 *  the player's language, translated once by LibreTranslate and kept in the database. The app keeps its own Russian
 *  and English (instant first paint, and the fallback while LibreTranslate is not set up); for every language but
 *  Russian the server's LibreTranslate text wins. */
import { useEffect, useState } from 'react';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const mem = {};                                       // ns:lang → texts (one fetch per session)

function cached(key) {
  if (mem[key]) return mem[key];
  try { const v = JSON.parse(localStorage.getItem(`uii18n:${key}`) || 'null'); if (v && v.texts) return (mem[key] = v); } catch (e) { /* no storage */ }
  return null;
}

export function useUiText(ns, lang, builtin) {
  const key = `${ns}:${lang}`;
  const [srv, setSrv] = useState(() => (lang === 'ru' ? null : cached(key)));
  useEffect(() => {
    if (lang === 'ru') { setSrv(null); return undefined; }
    let alive = true;
    const c = cached(key);
    if (c) setSrv(c);
    if (c && c.complete && Date.now() - (c.at || 0) < 6 * 3600 * 1000) return undefined;
    fetch(`${API}/i18n/${ns}?lang=${encodeURIComponent(lang)}`).then((r) => (r.ok ? r.json() : null)).then((d) => {
      if (!alive || !d || !d.texts) return;
      const v = { texts: d.texts, complete: !!d.complete, at: Date.now() };
      mem[key] = v;
      try { localStorage.setItem(`uii18n:${key}`, JSON.stringify(v)); } catch (e) { /* no storage */ }
      setSrv(v);
    }).catch(() => {});
    return () => { alive = false; };
  }, [key, lang, ns]);
  const base = builtin[lang] || builtin.en || builtin.ru;
  if (lang === 'ru') return builtin.ru;
  return { ...builtin.en, ...base, ...((srv && srv.texts) || {}) };
}
