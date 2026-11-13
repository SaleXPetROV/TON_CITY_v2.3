/**
 * Renders the body of a «Справочник» article (markup — see backend routes/wiki.py):
 *   # heading · - bullet · 1. step · > note · [[table:NAME]] · = Term | meaning
 *   inline: **bold**, [[slug|text]] (link to an article), {res:<id>} (resource icon + name in the player's language)
 * Steps are gathered into one «Как это сделать» list.
 */
import { Fragment } from 'react';
import { getResource } from '@/lib/resourceConfig';
import { tBusiness } from '@/lib/translationsExtra';

const BUSINESS_ICONS = { helios: '☀️', nano_dc: '🖥️', quartz_mine: '💎', signal_tower: '📡', hydro_cooling: '❄️', bio_farm: '🌿', scrap_yard: '🏗️',
  chips_factory: '🏭', nft_studio: '🎨', ai_lab: '🧪', logistics_hub: '🚁', cyber_cafe: '☕', repair_shop: '🛠️', vr_club: '👓',
  validator: '🛡️', gram_bank: '🏦', dex: '💹', casino: '🎰', arena: '🏟️', incubator: '🐣', bridge: '🌉' };

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;

export async function wikiApi(path, { auth = false, method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const tok = localStorage.getItem('token');
    if (!tok) throw new Error('no_token');
    headers.Authorization = `Bearer ${tok}`;
  }
  const r = await fetch(`${API}/wiki${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export function resText(s, lang) {
  return String(s ?? '').replace(/\{biz:(\w+)\}/g, (m, code) => `${BUSINESS_ICONS[code] || ''} ${tBusiness(code, lang)}`.trim()).replace(/\{res:(\w+)\}/g, (m, id) => {
    const r = getResource(id, lang);
    return r ? `${r.icon || ''} ${r.name || id}`.trim() : id;
  });
}

/** Inline: **bold**, [[slug|text]] links, {res:id}; `hl` highlights search words. */
export function Inline({ text, lang, onLink, hl }) {
  const parts = [];
  const re = /\*\*([^*]+)\*\*|\[\[([\w-]+)\|([^\]]+)\]\]/g;
  let last = 0;
  let m;
  const src = resText(text, lang);
  const mark = (s, k) => {
    if (!hl || !hl.length) return <Fragment key={k}>{s}</Fragment>;
    const rx = new RegExp(`(${hl.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
    return <Fragment key={k}>{s.split(rx).map((p, i) => (i % 2 ? <mark key={i} className="wk-hl">{p}</mark> : p))}</Fragment>;
  };
  while ((m = re.exec(src))) {
    if (m.index > last) parts.push(mark(src.slice(last, m.index), `t${last}`));
    if (m[1]) parts.push(<b key={`b${m.index}`}>{mark(m[1], 'x')}</b>);
    else parts.push(
      <a key={`a${m.index}`} href={`/wiki/${m[2]}`} className="wk-link"
        onClick={(e) => { if (onLink) { e.preventDefault(); onLink(m[2]); } }}>{m[3]}</a>,
    );
    last = re.lastIndex;
  }
  if (last < src.length) parts.push(mark(src.slice(last), `t${last}`));
  return <>{parts}</>;
}

export function WikiTable({ t, lang }) {
  if (!t) return null;
  if (t.list) {        // long texts: one card per row — name, what it gives, how long
    return (
      <div className="wk-tlist" role="list">
        {t.rows.map((r, i) => (
          <div className="wk-tli" role="listitem" key={i}>
            <div className="wk-tli-h"><b>{resText(r[0], lang)}</b>{r[2] && <span>{r[2]}</span>}</div>
            <p>{resText(r[1], lang)}</p>
          </div>
        ))}
        {t.note && <p className="wk-tnote">{t.note}</p>}
      </div>
    );
  }
  return (
    <div className="wk-table" role="table">
      <div className="wk-tr wk-th" role="row">{t.head.map((h, i) => <span key={i} role="columnheader">{h}</span>)}</div>
      {t.rows.map((r, i) => (
        <div className="wk-tr" role="row" key={i}>{r.map((c, j) => <span key={j} role="cell">{resText(c, lang)}</span>)}</div>
      ))}
      {t.note && <p className="wk-tnote">{t.note}</p>}
    </div>
  );
}

/** The whole body. `howto` — the title of the steps list. */
export default function WikiText({ body, tables = {}, lang, onLink, howto }) {
  const lines = String(body || '').split('\n');
  const out = [];
  let list = null; // {type: 'ul'|'ol'|'gl', items: []}
  const flush = () => {
    if (!list) return;
    const k = `l${out.length}`;
    if (list.type === 'ul') out.push(<ul key={k} className="wk-ul">{list.items.map((x, i) => <li key={i}><Inline text={x} lang={lang} onLink={onLink} /></li>)}</ul>);
    if (list.type === 'ol') out.push(
      <div key={k} className="wk-steps">
        {howto && <h3 className="wk-h3">{howto}</h3>}
        <ol>{list.items.map((x, i) => <li key={i}><i>{i + 1}</i><span><Inline text={x} lang={lang} onLink={onLink} /></span></li>)}</ol>
      </div>,
    );
    if (list.type === 'gl') out.push(
      <dl key={k} className="wk-gl">{list.items.map(([term, mean], i) => (
        <div key={i}><dt>{term}</dt><dd><Inline text={mean} lang={lang} onLink={onLink} /></dd></div>
      ))}</dl>,
    );
    list = null;
  };
  const push = (type, item) => {
    if (!list || list.type !== type) { flush(); list = { type, items: [] }; }
    list.items.push(item);
  };
  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    if (!line.trim()) { flush(); return; }
    let m;
    if ((m = line.match(/^\s*\[\[table:(\w+)\]\]\s*$/))) { flush(); out.push(<WikiTable key={`t${idx}`} t={tables[m[1]]} lang={lang} />); return; }
    if ((m = line.match(/^-\s+(.*)$/))) { push('ul', m[1]); return; }
    if ((m = line.match(/^\d+\.\s+(.*)$/))) { push('ol', m[1]); return; }
    if ((m = line.match(/^=\s+([^|]+)\|\s*(.*)$/))) { push('gl', [m[1].trim(), m[2]]); return; }
    flush();
    if ((m = line.match(/^#\s+(.*)$/))) { out.push(<h3 key={`h${idx}`} className="wk-h3">{m[1]}</h3>); return; }
    if ((m = line.match(/^>\s+(.*)$/))) { out.push(<p key={`n${idx}`} className="wk-note"><Inline text={m[1]} lang={lang} onLink={onLink} /></p>); return; }
    out.push(<p key={`p${idx}`} className="wk-p"><Inline text={line} lang={lang} onLink={onLink} /></p>);
  });
  flush();
  return <div className="wk-body">{out}</div>;
}
