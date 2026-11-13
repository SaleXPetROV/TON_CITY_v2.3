/**
 * «Справочник» — /wiki (home, search), /wiki/s/:section (a section), /wiki/:slug (an article).
 * The same page is the in-game wiki (signed in: sidebar, «Что нужно», «Показать на деле», support)
 * and the public site gramcity.app/wiki (no sign-in: language picker, «Открыть в GRAM City»).
 * Each article also exists as /wiki/<slug>.md, the whole wiki as /llms.txt (served by the backend).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import Sidebar from '@/components/Sidebar';
import SupportModal from '@/components/SupportModal';
import { useLanguage } from '@/context/LanguageContext';
import { gt } from '@/guide/guideI18n';
import WikiText, { Inline, wikiApi, resText } from '@/wiki/WikiText';
import { startWikiShow } from '@/wiki/WikiShow';
import { wt, fill } from '@/wiki/wikiI18n';
import '@/wiki/wiki.css';

const SEC_COLOR = { start: '#3B82F6', land: '#14B8A6', business: '#F97316', warehouse: '#F59E0B', trade: '#A855F7', money: '#EAB308', rewards: '#EC4899', community: '#EF4444', rules: '#94A3B8' };
const LANGS = [['ru', 'Русский'], ['en', 'English'], ['es', 'Español'], ['zh', '中文'], ['fr', 'Français'], ['de', 'Deutsch'], ['ja', '日本語'], ['ko', '한국어'], ['id', 'Indonesia']];
const RETURN = 'gc_wiki_return';
const fmtDate = (s, lang) => { try { return new Date(s).toLocaleDateString(lang, { day: '2-digit', month: '2-digit' }); } catch { return ''; } };

function useWiki(path, deps) {
  const [st, setSt] = useState({ data: null, err: false });
  useEffect(() => {
    let alive = true;
    setSt({ data: null, err: false });
    wikiApi(path).then((d) => alive && setSt({ data: d, err: false })).catch(() => alive && setSt({ data: null, err: true }));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return st;
}

function Top({ title, icon, onBack }) {
  return (
    <div className="wk-top">
      {onBack && <button type="button" className="wk-back" onClick={onBack} aria-label="←" data-testid="wiki-back">←</button>}
      <h1 className="wk-h1">{icon && <i style={{ fontStyle: 'normal' }}>{icon}</i>}<span>{title}</span></h1>
    </div>
  );
}

function SearchBox({ T, initial, onSearch }) {
  const [q, setQ] = useState(initial || '');
  useEffect(() => { setQ(initial || ''); }, [initial]);
  return (
    <form className="wk-search" role="search" onSubmit={(e) => { e.preventDefault(); onSearch(q.trim()); }}>
      <span aria-hidden="true">🔍</span>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={T('search')} aria-label={T('search')} data-testid="wiki-search-input" enterKeyHint="search" />
    </form>
  );
}

function GuideRoute({ T, lang, navigate }) {
  const [g, setG] = useState(null);
  useEffect(() => {
    const tok = localStorage.getItem('token');
    if (!tok) return;
    fetch(`${process.env.REACT_APP_BACKEND_URL || ''}/api/guide`, { headers: { Authorization: `Bearer ${tok}` } })
      .then((r) => (r.ok ? r.json() : null)).then((d) => setG(d?.state || null)).catch(() => {});
  }, []);
  if (!g) return null;
  const total = g.total || 62;
  const n = Math.min(total, Math.max(1, g.step || 1));
  const nextT = gt(lang, `s${String(n).padStart(2, '0')}.t`) || '';
  const again = async () => {
    try {
      await fetch(`${process.env.REACT_APP_BACKEND_URL || ''}/api/guide/restart`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
      window.location.assign('/my-businesses');
    } catch { /* offline */ }
  };
  return (
    <div className="wk-route" data-testid="wiki-route">
      <div className="wk-route-h"><span>{T('route').toUpperCase()}</span><small>{g.active ? fill(T('routeOf'), { n, total }) : `${total} / ${total}`}</small></div>
      <div className="wk-route-bar"><i style={{ width: `${(g.active ? n / total : 1) * 100}%` }} /></div>
      <div className="wk-route-row">
        <b>{g.active ? fill(T('routeNext'), { title: nextT.replace(/\{\w+\}/g, '').trim() || '…' }) : T('routeDone')}</b>
        {g.active
          ? <button type="button" className="wk-btn" onClick={() => navigate('/my-businesses')} data-testid="wiki-route-go">{T('routeGo')}</button>
          : <button type="button" className="wk-btn ghost" onClick={again} data-testid="wiki-route-again">{T('routeAgain')}</button>}
      </div>
    </div>
  );
}

function Home({ T, lang, signed, navigate }) {
  const { data, err } = useWiki(`/index?lang=${lang}`, [lang]);
  if (err) return <p className="wk-empty">{T('error')}</p>;
  return (
    <>
      <Top title={T('title')} icon="📖" />
      <p className="wk-sub">{T('sub')}</p>
      <SearchBox T={T} onSearch={(q) => q && navigate(`/wiki?q=${encodeURIComponent(q)}`)} />
      {signed && <GuideRoute T={T} lang={lang} navigate={navigate} />}
      {!data ? <div className="wk-spin" /> : (
        <div className="wk-grid" data-testid="wiki-sections">
          {data.sections.map((s, i) => (
            <button key={s.id} type="button" className={`wk-tile ${i === data.sections.length - 1 && data.sections.length % 2 ? 'wide' : ''}`}
              style={{ '--sc': SEC_COLOR[s.id] || '#00F0FF' }} onClick={() => navigate(`/wiki/s/${s.id}`)} data-testid={`wiki-section-${s.id}`}>
              <span className="i" aria-hidden="true">{s.icon}</span>
              <b>{s.title}</b>
              <small>{fill(T('articles'), { n: s.articles.length })}{s.articles.some((a) => a.new) ? ` · ${T('isNew')}` : ''}</small>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function Section({ T, lang, id, navigate }) {
  const { data, err } = useWiki(`/index?lang=${lang}`, [lang]);
  if (err) return <p className="wk-empty">{T('error')}</p>;
  const s = data?.sections.find((x) => x.id === id);
  const upd = s ? s.articles.map((a) => a.updated_at || '').sort().pop() : '';
  return (
    <>
      <Top title={s ? s.title : '…'} icon={s?.icon} onBack={() => navigate('/wiki')} />
      {!data ? <div className="wk-spin" /> : !s ? <p className="wk-empty">{T('notFound')}</p> : (
        <>
          <p className="wk-sub">{fill(T('articles'), { n: s.articles.length })}{upd ? ` · ${fill(T('updated'), { d: fmtDate(upd, lang) })}` : ''}</p>
          <div className="wk-list" data-testid="wiki-section-list">
            {s.articles.map((a) => (
              <button key={a.slug} type="button" className="wk-row" onClick={() => navigate(`/wiki/${a.slug}`)} data-testid={`wiki-article-${a.slug}`}>
                <span className="i" aria-hidden="true">{a.icon}</span>
                <span className="x"><b>{a.title}</b><small>{a.summary}</small></span>
                {a.new && <span className="wk-tag">{T('isNew')}</span>}
              </button>
            ))}
          </div>
        </>
      )}
    </>
  );
}

function Results({ T, lang, q, navigate, onAsk, signed }) {
  const { data, err } = useWiki(`/search?lang=${lang}&q=${encodeURIComponent(q)}`, [lang, q]);
  return (
    <>
      <Top title={T('title')} icon="📖" onBack={() => navigate('/wiki')} />
      <SearchBox T={T} initial={q} onSearch={(x) => navigate(x ? `/wiki?q=${encodeURIComponent(x)}` : '/wiki')} />
      {err ? <p className="wk-empty">{T('error')}</p> : !data ? <div className="wk-spin" /> : (
        <>
          <p className="wk-sub" style={{ marginTop: 10 }}>{data.items.length ? fill(T('found'), { n: data.items.length }) : T('notFound')}</p>
          {data.items.length > 0 && (
            <div className="wk-list" data-testid="wiki-results">
              {data.items.map((a) => (
                <button key={a.slug} type="button" className="wk-row" onClick={() => navigate(`/wiki/${a.slug}`)} data-testid={`wiki-result-${a.slug}`}>
                  <span className="i" aria-hidden="true">{a.icon}</span>
                  <span className="x"><b>{a.title}</b><small><Inline text={a.snippet.replace(/\[\[[\w-]+\|([^\]]+)\]\]/g, '$1')} lang={lang} hl={(a.words || []).filter((w) => w.length > 2)} /></small></span>
                </button>
              ))}
            </div>
          )}
          {signed && (
            <div className="wk-ask">
              <span className="i" aria-hidden="true">🤖</span>
              <div><b>{T('noAnswer')}</b><small>{T('askText')}</small></div>
              <button type="button" className="wk-btn" onClick={onAsk} data-testid="wiki-ask">{T('ask')}</button>
            </div>
          )}
        </>
      )}
    </>
  );
}

function Need({ T, lang, a, navigate, signed }) {
  const [ck, setCk] = useState(null);
  const load = useCallback(() => {
    if (!signed || !(a.needs || []).length) return;
    wikiApi(`/check/${a.slug}?lang=${lang}`, { auth: true }).then(setCk).catch(() => setCk(null));
  }, [a, lang, signed]);
  useEffect(() => { load(); }, [load]);
  const goFix = (c) => {
    try { sessionStorage.setItem(RETURN, JSON.stringify({ slug: a.slug, title: a.title })); } catch { /* */ }
    navigate(`/wiki/${c.fix}`);
  };
  const firstFail = ck?.checks.find((c) => c.state === 'fail' && c.fix && c.fix !== a.slug);
  const showIt = () => startWikiShow({ slug: a.slug, title: a.title, route: a.show.route, steps: a.show.steps }, ck?.vars || {});
  if (!(a.needs || []).length && !a.show) return null;
  return (
    <>
      {(a.needs || []).length > 0 && (
        <div className="wk-need" data-testid="wiki-need">
          <div className="wk-need-h"><span>{T('need')}</span>{ck && <small>{T('checked')}</small>}</div>
          {!signed && <p className="wk-meta" style={{ marginTop: 6 }}>{T('login')}</p>}
          {signed && !ck && <div className="wk-spin" style={{ margin: '14px auto' }} />}
          {ck && ck.checks.map((c) => (
            <div key={c.id} className="wk-ck" data-testid={`wiki-check-${c.id}`} data-state={c.state}>
              <span className="s" aria-hidden="true">{c.state === 'ok' ? '✅' : c.state === 'fail' ? '❌' : 'ℹ️'}</span>
              <span><b>{c.label}</b><small>{resText(c.detail, lang)}{c.state === 'fail' && c.fix && c.fix !== a.slug && c.fix_title
                ? <> → <a role="link" tabIndex={0} onClick={() => goFix(c)} onKeyDown={(e) => e.key === 'Enter' && goFix(c)}>{c.fix_title}</a></> : null}</small></span>
            </div>
          ))}
        </div>
      )}
      {signed && firstFail ? (
        <>
          <button type="button" className="wk-btn wide" onClick={() => goFix(firstFail)} data-testid="wiki-fix">{fill(T('first'), { title: firstFail.fix_title })} →</button>
          <p className="wk-meta" style={{ textAlign: 'center', marginTop: 6 }}>{T('back')}</p>
        </>
      ) : signed && a.show && (a.show.steps || []).length > 0 ? (
        <button type="button" className="wk-btn wide" onClick={showIt} data-testid="wiki-show-btn">▶ {T('show')}</button>
      ) : null}
    </>
  );
}

const first = (t) => (t.replace(/^[^\p{L}]+/u, '') || t)[0].toUpperCase();

function Glossary({ T, a, lang, navigate }) {
  const items = useMemo(() => String(a.body || '').split('\n').map((l) => l.match(/^=\s+([^|]+)\|\s*(.*)$/)).filter(Boolean)
    .map((m) => [m[1].trim(), m[2]]).sort((x, y) => x[0].localeCompare(y[0], lang)), [a.body, lang]);
  const groups = useMemo(() => {
    const letters = [...new Set(items.map(([t]) => first(t)))];
    const n = Math.min(4, letters.length);
    const size = Math.ceil(letters.length / n);
    return Array.from({ length: n }, (_, i) => letters.slice(i * size, (i + 1) * size)).filter((g) => g.length);
  }, [items]);
  const [g, setG] = useState(0);
  const shown = items.filter(([t]) => (groups[g] || []).includes(first(t)));
  return (
    <>
      <p className="wk-sub">{fill(T('words'), { n: items.length })}</p>
      <div className="wk-letters" role="tablist">
        {groups.map((grp, i) => (
          <button key={i} type="button" role="tab" aria-selected={g === i} className={g === i ? 'on' : ''} onClick={() => setG(i)}>
            {grp.length > 1 ? `${grp[0]}–${grp[grp.length - 1]}` : grp[0]}
          </button>
        ))}
      </div>
      <dl className="wk-gl" data-testid="wiki-glossary">
        {shown.map(([term, mean]) => <div key={term}><dt>{term}</dt><dd><Inline text={mean} lang={lang} onLink={(s) => navigate(`/wiki/${s}`)} /></dd></div>)}
      </dl>
    </>
  );
}

function Article({ T, lang, slug, navigate, signed }) {
  const { data: a, err } = useWiki(`/article/${slug}?lang=${lang}`, [lang, slug]);
  const [fb, setFb] = useState(null);
  const [ret, setRet] = useState(null);
  useEffect(() => {
    setFb(null);
    try {
      const r = JSON.parse(sessionStorage.getItem(RETURN) || 'null');
      setRet(r && r.slug !== slug ? r : null);
      if (r && r.slug === slug) sessionStorage.removeItem(RETURN);
    } catch { setRet(null); }
    window.scrollTo?.(0, 0);
  }, [slug]);
  useEffect(() => { if (a?.title) document.title = `${a.title} — ${T('title')} GRAM City`; }, [a, T]);
  if (err) return (<><Top title={T('title')} onBack={() => navigate('/wiki')} /><p className="wk-empty">{T('notFound')}</p></>);
  if (!a) return <div className="wk-spin" />;
  const link = (s) => navigate(`/wiki/${s}`);
  const vote = (helpful) => { setFb(helpful); wikiApi('/feedback', { method: 'POST', body: { slug, helpful } }).catch(() => {}); };
  return (
    <article data-testid={`wiki-page-${slug}`}>
      <Top title={a.section_title} icon={a.section_icon} onBack={() => navigate(`/wiki/s/${a.section}`)} />
      {ret && <button type="button" className="wk-returnbar" onClick={() => navigate(`/wiki/${ret.slug}`)} data-testid="wiki-return">{fill(T('backTo'), { title: ret.title })}</button>}
      <div className="wk-kicker">{T('article')}</div>
      <h2 className="wk-title">{a.title}</h2>
      <div className="wk-meta">{fill(T('minutes'), { n: a.minutes })}{a.updated_at ? ` · ${fill(T('updated'), { d: fmtDate(a.updated_at, lang) })}` : ''}</div>
      <p className="wk-lead">{a.summary}</p>
      {slug === 'glossary'
        ? <Glossary T={T} a={a} lang={lang} navigate={navigate} />
        : <WikiText body={a.body} tables={a.tables} lang={lang} onLink={link} howto={T('howto')} />}
      <Need T={T} lang={lang} a={a} navigate={navigate} signed={signed} />
      {(a.related || []).length > 0 && (
        <>
          <p className="wk-meta" style={{ marginTop: 18 }}>{T('related')}</p>
          <div className="wk-rel">{a.related.map((r) => <button key={r.slug} type="button" onClick={() => link(r.slug)} data-testid={`wiki-rel-${r.slug}`}>{r.icon} {r.title}</button>)}</div>
        </>
      )}
      <div className="wk-fb">
        <span>{fb == null ? T('helped') : T('thanks')}</span>
        {fb == null && <span><button type="button" onClick={() => vote(true)} data-testid="wiki-fb-yes">👍 {T('yes')}</button> · <button type="button" onClick={() => vote(false)} data-testid="wiki-fb-no">👎 {T('no')}</button></span>}
      </div>
    </article>
  );
}

export default function WikiPage({ user }) {
  const { lang, setLang } = useLanguage();
  const T = wt(lang);
  const navigate = useNavigate();
  const loc = useLocation();
  const { slug, section } = useParams();
  const [ask, setAsk] = useState(false);
  const signed = !!user?.id;
  const q = new URLSearchParams(loc.search).get('q') || '';
  useEffect(() => { if (!slug) document.title = `${T('title')} — GRAM City`; }, [slug, T]);

  const body = (
    <div className="wk wk-wrap" data-testid="wiki-page">
      {section ? <Section T={T} lang={lang} id={section} navigate={navigate} />
        : slug ? <Article T={T} lang={lang} slug={slug} navigate={navigate} signed={signed} />
          : q ? <Results T={T} lang={lang} q={q} navigate={navigate} signed={signed} onAsk={() => setAsk(true)} />
            : <Home T={T} lang={lang} signed={signed} navigate={navigate} />}
    </div>
  );

  if (!signed) {
    return (
      <div className="min-h-screen bg-void wk">
        <div className="wk-pub">
          <span className="logo">GRAM City <small>· {T('title')}</small></span>
          <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Language" data-testid="wiki-lang">
            {LANGS.map(([k, n]) => <option key={k} value={k}>{n}</option>)}
          </select>
          <a href="/" className="wk-btn" data-testid="wiki-open-game">{T('openGame')}</a>
        </div>
        {body}
      </div>
    );
  }
  return (
    <div className="flex h-screen bg-void">
      <Sidebar user={user} />
      <div className="flex-1 overflow-y-auto lg:ml-16 tg-header-pad">
        {body}
      </div>
      <SupportModal open={ask} onOpenChange={setAsk} language={lang} currentUser={user} />
    </div>
  );
}
