"""GitBook ⇄ «Справочник»: the in-game wiki shows what is in the project's GitBook space.

The GitBook space «Документация» (Git Sync → documentation/ of the repo) holds the same articles as the game. This
module reads that space through the GitBook API and puts it into db.wiki_articles, so an article written or changed
in GitBook is what the players see in the game, on /wiki and what Willy GRAM links to.

How one sync goes (every 10 minutes by the scheduler leader, or «Синхронизировать сейчас» in the admin):
  1. the space's current revision; nothing changed since the last sync → nothing to do;
  2. the page tree: a top page = a section (its title and emoji), its sub-pages = the articles, in GitBook's order;
  3. an article whose file is EXACTLY what tools/docs/gen_wiki_docs.py makes from the code (git blob id of the page =
     git blob id of the generated file) or whose text means the same → the code's article stays: live numbers, live
     tables, «Что нужно», «Показать на деле» and the ready translations of the 9 languages;
  4. an article changed or written in GitBook → its Russian text comes from GitBook (title, summary, body), the other
     8 languages are translated by LibreTranslate (markup kept);
  5. an article that is not in GitBook any more (or hidden there) → hidden in the game; back in GitBook → shown again.
Every change of a text keeps the previous one in db.wiki_versions, like the admin editor.

The same module renders the GitBook files (render_docs) — tools/docs/gen_wiki_docs.py writes them into documentation/,
and the sync compares with them, so «unchanged» is exact.

Settings: env GITBOOK_API_TOKEN (personal token, app.gitbook.com → Settings → Developer → Personal access tokens);
GITBOOK_ORG_ID / GITBOOK_SITE_ID / GITBOOK_SPACE_ID are found by the token when not set. Switches (admin «Справочник» →
GitBook): admin_settings {type: "gitbook"}: wiki_sync, ai_support. State: admin_settings {type: "gitbook_state"}.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

API = os.environ.get("GITBOOK_API_URL", "https://api.gitbook.com/v1").rstrip("/")
LANGS = ["ru", "en", "es", "zh", "fr", "de", "ja", "ko", "id"]
FOOTER = "\n\n---\n_Цифры в статье — значения по умолчанию; в игре всегда показываются текущие._\n"
DEFAULTS = {"wiki_sync": True, "ai_support": True}
MIN_ARTICLES = 5           # a GitBook space with fewer articles is taken for a mistake: nothing is hidden


class GitBookError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def token() -> str:
    return (os.environ.get("GITBOOK_API_TOKEN") or "").strip()


def configured() -> bool:
    return bool(token())


# ───────────────────────────── settings / state ─────────────────────────────

async def settings(db) -> Dict[str, Any]:
    s = await db.admin_settings.find_one({"type": "gitbook"}, {"_id": 0}) or {}
    return {**DEFAULTS, **{k: v for k, v in s.items() if k in DEFAULTS}}


async def save_settings(db, patch: Dict[str, Any]) -> Dict[str, Any]:
    upd = {k: bool(v) for k, v in (patch or {}).items() if k in DEFAULTS}
    if upd:
        await db.admin_settings.update_one({"type": "gitbook"}, {"$set": upd}, upsert=True)
    return await settings(db)


async def state(db) -> Dict[str, Any]:
    return await db.admin_settings.find_one({"type": "gitbook_state"}, {"_id": 0}) or {}


async def _save_state(db, upd: Dict[str, Any]) -> None:
    await db.admin_settings.update_one({"type": "gitbook_state"}, {"$set": upd}, upsert=True)


# ───────────────────────────── the API ─────────────────────────────

async def _request(method: str, path: str, *, params: Optional[Dict[str, Any]] = None,
                   body: Optional[Dict[str, Any]] = None, timeout: float = 20.0) -> Any:
    if not configured():
        raise GitBookError("GITBOOK_API_TOKEN не задан")
    import httpx
    async with httpx.AsyncClient(timeout=timeout) as cl:
        r = await cl.request(method, API + path, params=params, json=body,
                             headers={"Authorization": f"Bearer {token()}", "Accept": "application/json"})
    if r.status_code >= 400:
        raise GitBookError(f"GitBook {r.status_code}: {r.text[:200]}")
    return r.json() if r.content else {}


async def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    return await _request("GET", path, params=params)


async def ids(db) -> Dict[str, str]:
    """organization, site, space: from the env, or found once by the token and remembered."""
    out = {"org": os.environ.get("GITBOOK_ORG_ID", "").strip(), "site": os.environ.get("GITBOOK_SITE_ID", "").strip(),
           "space": os.environ.get("GITBOOK_SPACE_ID", "").strip()}
    if all(out.values()):
        return out
    st = await state(db)
    known = st.get("ids") or {}
    if all(known.get(k) for k in out) and all(not out[k] or out[k] == known[k] for k in out):
        return {k: known[k] for k in out}
    if not out["org"]:
        orgs = (await _get("/orgs")).get("items") or []
        if not orgs:
            raise GitBookError("у токена нет организаций GitBook")
        out["org"] = orgs[0]["id"]
    if not out["site"]:
        sites = (await _get(f"/orgs/{out['org']}/sites")).get("items") or []
        if not sites:
            raise GitBookError("в организации GitBook нет сайтов")
        out["site"] = sites[0]["id"]
    if not out["space"]:
        ss = (await _get(f"/orgs/{out['org']}/sites/{out['site']}/site-spaces")).get("items") or []
        ss.sort(key=lambda x: not x.get("default"))
        if not ss:
            raise GitBookError("на сайте GitBook нет пространства")
        out["space"] = (ss[0].get("space") or {}).get("id") or ""
    await _save_state(db, {"ids": out})
    return out


# ───────────────────────────── the files (same as documentation/) ─────────────────────────────

class _NoDB:
    """A database with nothing in it but the default taxes — wiki_vars on it gives the game's default numbers."""

    class _Cursor:
        def sort(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def skip(self, *a, **k):
            return self

        async def to_list(self, *a, **k):
            return []

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class _Coll:
        async def find_one(self, q=None, *a, **k):
            if isinstance(q, dict) and q.get("type") == "tax_settings":
                return {"type": "tax_settings", "small_business_tax": 15, "medium_business_tax": 23, "large_business_tax": 30}
            return None

        def find(self, *a, **k):
            return _NoDB._Cursor()

        def aggregate(self, *a, **k):
            return _NoDB._Cursor()

        async def count_documents(self, *a, **k):
            return 0

        async def _none(self, *a, **k):
            return None

        insert_one = update_one = update_many = delete_one = delete_many = replace_one = _none
        find_one_and_update = create_index = _none

    def __getattr__(self, name):
        return _NoDB._Coll()

    def __getitem__(self, name):
        return _NoDB._Coll()


async def default_vars() -> Dict[str, Any]:
    import routes.wiki as W
    return await W.wiki_vars(_NoDB(), use_cache=False)


def seed_docs() -> List[Dict[str, Any]]:
    """The articles that come with the code, in the order of their sections."""
    from wiki_content import ARTICLES, SECTIONS, load_texts
    texts = load_texts()
    docs = []
    for order, meta in enumerate(ARTICLES):
        slug = meta["slug"]
        docs.append({**meta, "order": order, "i18n": {lg: texts[lg][slug] for lg in LANGS if slug in texts.get(lg, {})}})
    so = {s["id"]: i for i, s in enumerate(SECTIONS)}
    return sorted(docs, key=lambda d: (so.get(d.get("section"), 99), d["order"]))


def tidy(md: str) -> str:
    """GitBook (CommonMark) needs a blank line before a table, a list and a quote that follow a paragraph."""
    out, prev = [], ""

    def kind(x: str) -> str:
        if x.startswith("|"):
            return "table"
        if re.match(r"(\s*[-*] |\s*\d+\. )", x):
            return "list"
        if x.startswith(">"):
            return "quote"
        if x.startswith("#"):
            return "head"
        return "text" if x.strip() else ""
    for line in md.split("\n"):
        k, pk = kind(line), kind(prev)
        if k and pk and k != pk and not (k == "text" and pk == "list" and line.startswith("  ")):
            out.append("")
        out.append(line)
        prev = line
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def render_docs(docs: List[Dict[str, Any]], v: Dict[str, Any]) -> Dict[str, str]:
    """{path inside documentation/: text} — README, SUMMARY, the section pages and the articles (Russian)."""
    import routes.wiki as W
    from wiki_content import SECTIONS
    secs: Dict[str, Tuple[str, str, List[Dict[str, Any]]]] = {s["id"]: (s["icon"], s["t"]["ru"], []) for s in SECTIONS}
    for d in docs:
        secs.setdefault(d.get("section") or "start", ("", d.get("section") or "start", []))[2].append(d)
    slugsec = {d["slug"]: d.get("section") for d in docs}
    files: Dict[str, str] = {}

    def put(rel: str, text: str) -> None:
        files[rel] = text.rstrip() + "\n"
    nav = []
    for sid, (icon, title, ds) in secs.items():
        if not ds:
            continue
        items = []
        for d in ds:
            md = W._md(d, "ru", v)

            def link(m, sid=sid):
                sec = slugsec.get(m.group(2))
                if not sec:
                    return m.group(0)
                return f"]({'../' + sec + '/' if sec != sid else ''}{m.group(2)}.md)"
            md = re.sub(r"\]\((https?://[^)\s]*?)/wiki/([\w-]+)\)", link, md)
            put(f"{sid}/{d['slug']}.md", tidy(md).rstrip() + FOOTER)
            c = W._card(d, "ru", v)
            items.append((d["slug"], c["title"], d.get("icon") or "", c["summary"]))
        put(f"{sid}/README.md", "\n".join([f"# {icon} {title}", "",
                                           *[f"- [{ic} {t}]({s}.md){' — ' + sm if sm else ''}" for s, t, ic, sm in items]]))
        nav.append((sid, icon, title, items))
    total = sum(len(n[3]) for n in nav)
    put("README.md", "\n".join([
        "# Справочник игрока GRAM CITY", "",
        "Всё об игре простыми словами: как начать, заработать на бизнесе, торговать, пополнять и выводить GRAM.",
        "Это те же статьи, что в игре: меню ☰ → «Справочник» и кнопка «?» на экранах.", "",
        "> GRAM — это монета TON. Пополняйте баланс только монетой TON.", "",
        "## Разделы", "",
        *[f"- [{icon} {title}]({sid}/README.md) ({len(items)})" for sid, icon, title, items in nav], "",
        f"Всего статей: {total}. Не нашли ответ — напишите в поддержку из игры.",
    ]))
    lines = ["# Table of contents", "", "* [Справочник игрока](README.md)", ""]
    for sid, icon, title, items in nav:
        lines.append(f"* [{icon} {title}]({sid}/README.md)")
        lines += [f"  * [{ic} {t}]({sid}/{s}.md)" for s, t, ic, _ in items]
    put("SUMMARY.md", "\n".join(lines))
    return files


def git_oid(text: str) -> str:
    """The git blob id of a file with this text (what GitBook reports as page.git.oid)."""
    b = text.encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


# ───────────────────────────── GitBook markdown → the wiki's markup ─────────────────────────────

_FOOT_RE = re.compile(r"\n\s*(?:\*\*\*|---|___)\s*\n+\s*_?Цифры в статье[^\n]*\s*$")


def _inline(s: str, links: Dict[str, str]) -> str:
    """Inline markdown → the wiki's inline markup: **bold**, [[slug|text]], [text](https://…); the rest is plain."""
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<(?:mark|span|kbd|code|sup|sub|u|em|i)[^>]*>|</(?:mark|span|kbd|code|sup|sub|u|em|i)>", "", s)
    s = re.sub(r"<(?:strong|b)>(.*?)</(?:strong|b)>", r"**\1**", s)

    def link(m: re.Match) -> str:
        text, url = m.group(1).strip(), m.group(2).strip().split(" ")[0].strip("<>")
        text = re.sub(r"[*_`]", "", text)
        slug = _slug_of(url, links)
        if slug:
            return f"[[{slug}|{text}]]"
        if re.match(r"https?://", url):
            return f"[{text}]({url})"
        return text
    s = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", link, s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    # italics → plain (bold stays): _x_ / *x* that are not part of **x**
    s = re.sub(r"(?<![\w*])\*(?!\*)([^*\n]+?)\*(?![\w*])", r"\1", s)
    s = re.sub(r"(?<![\w_])_(?!_)([^_\n]+?)_(?![\w_])", r"\1", s)
    s = s.replace("__", "**")
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>~<])", r"\1", s)
    return re.sub(r"[ \t]+", " ", s).strip()


def _slug_of(url: str, links: Dict[str, str]) -> Optional[str]:
    """A link to another page of the space → the article's slug (or None)."""
    u = url.split("#")[0]
    m = re.match(r"^/pages/([\w-]+)", u)
    if m:
        return links.get(m.group(1))
    m = re.match(r"^https?://[^/]+/(?:.*/)?wiki/([\w-]+)", u)
    if m:
        return m.group(1)
    if re.match(r"^(https?:|mailto:)", u):
        m = re.search(r"/s/[\w-]+/(?:[\w-]+/)*([\w-]+)/?$", u) if "app.gitbook.com" in u else None
        return links.get(m.group(1)) if m and m.group(1) in links.values() else None
    m = re.search(r"([\w-]+)(?:\.md)?/?$", u)
    if m and m.group(1) not in ("README", "readme"):
        slug = m.group(1).lower()
        return slug if slug in set(links.values()) else None
    return None


def to_markup(md: str, links: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """A GitBook page (markdown) → {t: title, s: summary, b: body} in the wiki's markup.

    links: {page id: slug} of the space (for `/pages/<id>` links); a link to an unknown page becomes plain text."""
    links = links or {}
    md = (md or "").replace("\r\n", "\n")
    desc = ""
    fm = re.match(r"^---\n(.*?)\n---\n", md, re.S)
    if fm:
        md = md[fm.end():]
        m = re.search(r"^description:\s*(?:[>|]-?\s*\n((?:\s+.*\n?)+)|(.*))$", fm.group(1), re.M)
        if m:
            desc = re.sub(r"\s+", " ", (m.group(1) or m.group(2) or "")).strip().strip("'\"")
    md = _FOOT_RE.sub("", md.rstrip() + "\n").rstrip()
    lines = md.split("\n")
    title = ""
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^#\s+", lines[0]):
        title = _inline(re.sub(r"^#\s+", "", lines.pop(0)), links)
    out: List[str] = []
    hint = False
    para: List[str] = []

    def flush_para():
        if para:
            out.append(_inline(" ".join(x.strip() for x in para), links))
            para.clear()

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        st = line.strip()
        i += 1
        # GitBook blocks: hints become notes, the other tags are dropped (their text stays)
        m = re.match(r"^\{%\s*hint\b.*%\}\s*(.*)$", st)
        if m:
            flush_para()
            hint = True
            if m.group(1):
                out.append("> " + _inline(m.group(1), links))
            continue
        if re.match(r"^\{%\s*endhint\s*%\}$", st):
            flush_para()
            hint = False
            continue
        if re.match(r"^\{%.*%\}$", st):
            flush_para()
            continue
        st = re.sub(r"\{%.*?%\}", "", st).strip()
        img = re.search(r"<img\b[^>]*>", st)
        if img or re.match(r"^!\[[^\]]*\]\([^)]+\)$", st):
            flush_para()
            if img:
                src = re.search(r'src="([^"]+)"', img.group(0))
                alt = re.search(r'alt="([^"]*)"', img.group(0))
                if src:
                    out.append(f"![{alt.group(1) if alt else ''}]({src.group(1)})")
            else:
                mm = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)", st)
                out.append(f"![{mm.group(1)}]({mm.group(2)})")
            continue
        if re.match(r"^</?(figure|figcaption|details|div|p|table|thead|tbody|tr)\b[^>]*>$", st):
            flush_para()
            continue
        m = re.match(r"^<summary>(.*)</summary>$", st)
        if m:
            flush_para()
            out.append("# " + _inline(m.group(1), links))
            continue
        if not st:
            flush_para()
            if out and out[-1] != "":
                out.append("")
            continue
        if re.match(r"^(\*\*\*|---|___)$", st):
            flush_para()
            continue
        m = re.match(r"^#{1,6}\s+(.*)$", st)
        if m:
            flush_para()
            out.append("# " + _inline(m.group(1), links))
            continue
        if st.startswith("|"):
            flush_para()
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", st.strip().strip("|"))]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            out.append("| " + " | ".join(_inline(c, links) for c in cells) + " |")
            continue
        m = re.match(r"^\s*[*+-]\s+(?:\[[ xX]\]\s+)?(.*)$", line)
        if m:
            flush_para()
            out.append("- " + _inline(m.group(1), links))
            continue
        m = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
        if m:
            flush_para()
            out.append("1. " + _inline(m.group(2), links))
            continue
        m = re.match(r"^>\s?(.*)$", st)
        if m:
            flush_para()
            if m.group(1).strip():
                out.append("> " + _inline(m.group(1), links))
            continue
        if hint:
            flush_para()
            out.append("> " + _inline(st, links))
            continue
        if re.match(r"^\s{2,}\S", raw) and out and re.match(r"^(- |1\. )", out[-1] or ""):
            out[-1] += " " + _inline(st, links)        # a list item that goes on, on the next line
            continue
        para.append(st)
    flush_para()
    # the first paragraph after the title is the summary (unless the page has a description)
    body = [x for x in out]
    while body and body[0] == "":
        body.pop(0)
    summary = desc
    if not summary and body and not re.match(r"^(# |- |1\. |> |\| |!\[)", body[0]):
        summary = body.pop(0)
    # numbers of steps: «1.» for every step (the wiki numbers them itself)
    text = "\n".join(body).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return {"t": title, "s": summary, "b": text}


def same(a: Dict[str, str], b: Dict[str, str]) -> bool:
    def n(x: str) -> str:
        x = (x or "").replace(" ", " ").replace("️", "")
        return re.sub(r"\s+", " ", x).strip()
    return all(n(a.get(k, "")) == n(b.get(k, "")) for k in ("t", "s", "b"))


def _hash(conv: Dict[str, str]) -> str:
    return hashlib.sha1(json.dumps([conv.get("t"), conv.get("s"), conv.get("b")], ensure_ascii=False).encode()).hexdigest()


def emoji(e: Any) -> str:
    """GitBook gives an emoji as its code point(s) in hex ("1f680", "2696") or as the character."""
    if not e:
        return ""
    e = str(e)
    if re.fullmatch(r"[0-9a-fA-F]{4,6}(?:[-_ ][0-9a-fA-F]{4,6})*", e):
        try:
            s = "".join(chr(int(x, 16)) for x in re.split(r"[-_ ]", e))
            if len(s) == 1 and ord(s) < 0x2b00:
                s += "️"      # ⚖ → ⚖️ (text-style symbols need the emoji selector)
            return s
        except ValueError:
            return ""
    return e


def _base(e: str) -> str:
    return (e or "").replace("️", "")


# ───────────────────────────── the sync ─────────────────────────────

def _walk(pages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
    """The page tree → (sections, articles, {page id: slug}). Hidden pages and links are skipped."""
    from wiki_content import SECTIONS
    known = {s["id"] for s in SECTIONS}
    sections: List[Dict[str, Any]] = []
    articles: List[Dict[str, Any]] = []
    links: Dict[str, str] = {}

    def slug_of(p: Dict[str, Any]) -> str:
        gp = ((p.get("git") or {}).get("path") or "")
        base = os.path.splitext(os.path.basename(gp))[0] if gp else ""
        s = base if base and base.lower() != "readme" else (p.get("slug") or "")
        return re.sub(r"[^a-z0-9-]", "", s.lower().replace("_", "-"))[:60]

    docs = [p for p in pages if p.get("type", "document") == "document" and not p.get("hidden")]
    first = True
    for p in docs:
        kids = [k for k in (p.get("pages") or []) if k.get("type", "document") == "document" and not k.get("hidden")]
        gp = ((p.get("git") or {}).get("path") or "")
        sid = re.sub(r"[^a-z0-9-]", "", (p.get("slug") or "").lower())[:40]
        is_intro = gp.endswith("documentation/README.md") or gp == "README.md" or (first and not kids and sid not in known)
        first = False
        if is_intro:
            continue
        if not kids and sid not in known:
            # a page at the top without sub-pages: an article of the first section
            a_slug = slug_of(p)
            links[p["id"]] = a_slug
            articles.append({"page": p, "slug": a_slug, "section": (sections[0]["id"] if sections else "start")})
            continue
        sections.append({"id": sid, "title": p.get("title") or sid, "icon": emoji(p.get("emoji")), "page": p.get("id")})

        def add(items: List[Dict[str, Any]]):
            for k in items:
                if k.get("type", "document") != "document" or k.get("hidden"):
                    continue
                s = slug_of(k)
                if s:
                    links[k["id"]] = s
                    articles.append({"page": k, "slug": s, "section": sid})
                add(k.get("pages") or [])
        add(kids)
    for s in sections:
        links.setdefault(s["page"], "")
    return sections, articles, {k: v for k, v in links.items() if v}


async def _page_md(space: str, page_id: str) -> str:
    r = await _get(f"/spaces/{space}/content/page/{page_id}", {"format": "markdown", "format.markdown.refs": "stable"})
    return r.get("markdown") or ""


async def translate(ru: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The 8 other languages of a Russian article (LibreTranslate). {} when it is not set up."""
    try:
        import translation_service as ts
        if not ts.libretranslate_configured():
            return {}
    except Exception:
        return {}
    import routes.wiki as W
    out: Dict[str, Dict[str, Any]] = {}
    for lg in LANGS:
        if lg == "ru":
            continue
        try:
            out[lg] = {"t": await W.translate_markup(ru.get("t", ""), lg), "s": await W.translate_markup(ru.get("s", ""), lg),
                       "b": await W.translate_markup(ru.get("b", ""), lg)}
        except Exception as e:  # noqa: BLE001
            logger.warning(f"gitbook wiki: translation to {lg} failed: {e}")
    return out


async def sync(db, force: bool = False, fetch=None) -> Dict[str, Any]:
    """One sync of the space into the wiki. `fetch(path, params)` replaces the API (tests)."""
    global _get
    s = await settings(db)
    if not s["wiki_sync"]:
        return {"ok": True, "skipped": "off"}
    if fetch is None and not configured():
        return {"ok": False, "error": "GITBOOK_API_TOKEN не задан"}
    real_get = _get
    if fetch is not None:
        _get = fetch  # type: ignore[assignment]
    try:
        return await _sync(db, force)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"gitbook wiki sync failed: {e}")
        await _save_state(db, {"last_error": str(e)[:300], "last_try": _now()})
        return {"ok": False, "error": str(e)[:300]}
    finally:
        _get = real_get  # type: ignore[assignment]


async def _sync(db, force: bool) -> Dict[str, Any]:
    import routes.wiki as W
    from wiki_content import SECTIONS
    t0 = time.time()
    st = await state(db)
    gid = await ids(db)
    space = await _get(f"/spaces/{gid['space']}")
    rev = space.get("revision") or ""
    if rev and rev == st.get("revision") and not force:
        await _save_state(db, {"last_try": _now(), "last_error": None})
        return {"ok": True, "skipped": "same revision"}
    content = await _get(f"/spaces/{gid['space']}/content")
    sections, arts, links = _walk(content.get("pages") or [])

    seed = seed_docs()
    seed_by = {d["slug"]: d for d in seed}
    v = await default_vars()
    files = render_docs(seed, v)
    oids = {p: git_oid(t) for p, t in files.items()}
    known_pages = st.get("pages") or {}

    stats = {"articles": len(arts), "from_code": 0, "from_gitbook": 0, "changed": 0, "new": 0, "hidden": 0, "shown": 0,
             "translated": 0}
    wanted: Dict[str, Dict[str, Any]] = {}
    pages_state: Dict[str, Any] = {}
    for order, a in enumerate(arts):
        p, slug = a["page"], a["slug"]
        if slug in wanted:
            continue
        git = p.get("git") or {}
        gp = re.sub(r"^documentation/", "", git.get("path") or "")
        item = {"section": a["section"], "order": order, "icon": emoji(p.get("emoji")), "page": p["id"]}
        if slug in seed_by and gp and git.get("oid") and oids.get(gp) == git.get("oid"):
            item["kind"] = "code"
        else:
            prev = known_pages.get(p["id"]) or {}
            stamp = f"{git.get('oid') or ''}|{p.get('updatedAt') or ''}"
            if prev.get("stamp") == stamp and prev.get("conv"):
                conv = prev["conv"]
            else:
                conv = to_markup(await _page_md(gid["space"], p["id"]), links)
            pages_state[p["id"]] = {"slug": slug, "stamp": stamp, "conv": conv}
            if not conv.get("t"):
                conv["t"] = p.get("title") or slug
            if slug in seed_by:
                base_path = f"{seed_by[slug].get('section')}/{slug}.md"
                base = to_markup(files.get(base_path, ""), links)
                item["kind"] = "code" if same(conv, base) else "gitbook"
            else:
                item["kind"] = "gitbook"
            item["conv"] = conv
        pages_state.setdefault(p["id"], {"slug": slug})
        wanted[slug] = item

    for slug, it in wanted.items():
        cur = await db.wiki_articles.find_one({"slug": slug}, {"_id": 0})
        common: Dict[str, Any] = {"section": it["section"], "order": it["order"], "published": True, "gitbook_page": it["page"]}
        if it["icon"] and (not cur or _base(cur.get("icon") or "") != _base(it["icon"])):
            common["icon"] = it["icon"]
        if cur and cur.get("published") is False:
            stats["shown"] += 1
        if it["kind"] == "code":
            stats["from_code"] += 1
            sd = seed_by[slug]
            if not cur:
                from wiki_content import SEED_REV
                await db.wiki_articles.insert_one({**sd, **common, "origin": "seed", "seed_rev": SEED_REV,
                                                   "created_at": _now(), "updated_at": _now()})
                stats["new"] += 1
                continue
            if cur.get("origin") == "gitbook":
                # the text in GitBook is the code's again: back to the code's article (live numbers, translations)
                await _version(db, cur, "gitbook")
                from wiki_content import SEED_REV
                common.update({"i18n": sd["i18n"], "origin": "seed", "seed_rev": SEED_REV, "gitbook_hash": None,
                               "updated_at": _now()})
                stats["changed"] += 1
            await db.wiki_articles.update_one({"slug": slug}, {"$set": common})
            continue
        stats["from_gitbook"] += 1
        conv = it["conv"]
        h = _hash(conv)
        if cur and cur.get("gitbook_hash") == h:
            await db.wiki_articles.update_one({"slug": slug}, {"$set": common})
            continue
        ru = {**((cur or {}).get("i18n", {}).get("ru") or {}), "t": conv["t"], "s": conv["s"], "b": conv["b"]}
        i18n = {**((cur or {}).get("i18n") or {}), "ru": ru}
        tr = await translate(conv)
        for lg, x in tr.items():
            i18n[lg] = {**(i18n.get(lg) or {}), **{k: val for k, val in x.items() if val}}
            stats["translated"] += 1
        upd = {**common, "i18n": i18n, "origin": "gitbook", "gitbook_hash": h, "updated_at": _now(), "updated_by": "gitbook"}
        if cur:
            await _version(db, cur, "gitbook")
            await db.wiki_articles.update_one({"slug": slug}, {"$set": upd})
            stats["changed"] += 1
        else:
            await db.wiki_articles.insert_one({"slug": slug, "icon": it["icon"] or "📄", "screens": [], "needs": [],
                                               "related": [], "show": None, "created_at": _now(), **upd})
            stats["new"] += 1

    if len(wanted) >= MIN_ARTICLES:
        res = await db.wiki_articles.update_many(
            {"published": {"$ne": False}, "slug": {"$nin": list(wanted)}},
            {"$set": {"published": False, "hidden_by": "gitbook", "updated_at": _now()}})
        stats["hidden"] = int(getattr(res, "modified_count", 0) or 0)

    # sections: GitBook's order, titles and emoji (a new section gets its title translated)
    builtin = {x["id"]: x for x in SECTIONS}
    prev_secs = {x["id"]: x for x in (st.get("sections") or [])}
    out_secs = []
    for sct in sections:
        b = builtin.get(sct["id"])
        old = prev_secs.get(sct["id"]) or {}
        t = dict((b or {}).get("t") or {})
        if (b and t.get("ru") != sct["title"]) or not b:
            if old.get("t", {}).get("ru") == sct["title"]:
                t = old["t"]
            else:
                t = {"ru": sct["title"]}
                tr = await translate({"t": sct["title"]})
                for lg, x in tr.items():
                    if x.get("t"):
                        t[lg] = x["t"]
                if b:
                    t = {**{k: val for k, val in b["t"].items() if k not in t or k == "ru"}, **t}
        icon = sct["icon"] if sct["icon"] else ((b or {}).get("icon") or "📄")
        if b and _base(icon) == _base(b.get("icon") or ""):
            icon = b["icon"]
        out_secs.append({"id": sct["id"], "icon": icon, "t": t})

    await _save_state(db, {"revision": rev, "last_sync": _now(), "last_try": _now(), "last_error": None,
                           "stats": stats, "sections": out_secs, "pages": pages_state,
                           "seconds": round(time.time() - t0, 1)})
    W.set_gitbook_sections(out_secs)
    W._CACHE["at"] = 0
    logger.info(f"gitbook wiki sync: {stats}")
    return {"ok": True, **stats}


async def _version(db, cur: Dict[str, Any], by: str) -> None:
    try:
        await db.wiki_versions.insert_one({"slug": cur["slug"], "at": _now(), "by": by, "doc": cur})
    except Exception:  # noqa: BLE001
        pass


async def load(db) -> None:
    """At start: the sections of the last sync (order, titles) for the wiki."""
    try:
        import routes.wiki as W
        st = await state(db)
        if st.get("sections"):
            W.set_gitbook_sections(st["sections"])
    except Exception as e:  # noqa: BLE001
        logger.debug(f"gitbook load: {e}")


async def status(db) -> Dict[str, Any]:
    st = await state(db)
    return {"configured": configured(), "settings": await settings(db), "last_sync": st.get("last_sync"),
            "last_try": st.get("last_try"), "last_error": st.get("last_error"), "stats": st.get("stats") or {},
            "seconds": st.get("seconds"), "ai": st.get("ai") or {},
            "sections": [{"id": x["id"], "icon": x["icon"], "title": x["t"].get("ru")} for x in st.get("sections") or []]}


# ───────────────────────────── GitBook AI for the support ─────────────────────────────

NO_ANSWER_MARK = "NO_ANSWER"
# the AI's own words for «the docs have nothing on it» — an answer with them is not an answer, even with a hedge before
_NO_ANSWER_RE = re.compile(
    r"(NO_ANSWER|не (?:удалось|могу) найти|нет информации|не нашёл|не нашел|информаци\w* (?:\w+ )*нет|"
    r"документаци\w* (?:\w+ )?не (?:описыва|содержит|упомина|охватыва|говорит)|в документации (?:\w+ )?нет|"
    r"описывает только|не относится к|вне (?:темы|рамок)|"
    r"couldn['’]t find|could not find|no information|i don['’]t know|not (?:covered|mentioned|described|documented)|"
    r"documentation (?:does not|doesn['’]t|only covers)|outside (?:the )?scope)", re.I)


def plain(md: str) -> str:
    """The AI's markdown → the text of a chat message (the chat shows plain text)."""
    out = []
    for line in (md or "").replace("\r\n", "\n").split("\n"):
        s = line.rstrip()
        s = re.sub(r"^#{1,6}\s+", "", s)
        s = re.sub(r"^\s*[*+-]\s+", "• ", s)
        s = re.sub(r"^>\s?", "", s)
        s = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        s = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m.group(1) or m.group(2), s)
        s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])|(?<![\w_])_([^_\n]+)_(?![\w_])", lambda m: m.group(1) or m.group(2), s)
        s = re.sub(r"`([^`]+)`", r"\1", s)
        s = re.sub(r"\{%.*?%\}", "", s)
        s = re.sub(r"<[^>]+>", "", s)
        if re.fullmatch(r"\s*(\*\*\*|---|___)\s*", s):
            continue
        out.append(s)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


async def ask(db, question: str, lang: str, post=None) -> Dict[str, Any]:
    """Ask the GitBook site's AI. → {ok, answer (markdown), sources: [{page, title}], followups}; ok=False with
    `none`=True when the docs have no answer, or `error` when GitBook could not be asked.
    `post(path, body)` replaces the API (tests): it returns the list of streamed events."""
    gid = await ids(db) if post is None else {"org": "o", "site": "s", "space": "sp"}
    lang_name = {"ru": "русском", "en": "английском", "es": "испанском", "zh": "китайском", "fr": "французском",
                 "de": "немецком", "ja": "японском", "ko": "корейском", "id": "индонезийском"}.get(lang, "английском")
    body = {"question": question[:512], "scope": {"mode": "default"},
            "context": {"goal": (f"Ответить игроку GRAM CITY в чате поддержки на {lang_name} языке, только по документации "
                                 f"игры. Если вопрос не про игру GRAM CITY или в документации нет ответа, ответь только "
                                 f"словом {NO_ANSWER_MARK} — без догадок и без ответа на соседний вопрос.")[:1024]}}
    path = f"/orgs/{gid['org']}/sites/{gid['site']}/ask"
    if post is not None:
        events = await post(path, body)
    else:
        events = await _stream(path, body)
    ans = None
    for ev in events:
        if isinstance(ev, dict) and ev.get("type") == "answer" and ev.get("answer"):
            ans = ev["answer"]
    if not ans:
        return {"ok": False, "none": True}
    md = ((ans.get("answer") or {}).get("markdown") or "").strip()
    sources = [{"page": x.get("page"), "title": x.get("title")} for x in ans.get("sources") or [] if x.get("type") == "page"]
    if not md or not (ans.get("sources") or []) or _NO_ANSWER_RE.search(md):
        return {"ok": False, "none": True, "answer": md}
    return {"ok": True, "answer": md, "sources": sources, "followups": ans.get("followupQuestions") or []}


async def _stream(path: str, body: Dict[str, Any], deadline: float = 35.0) -> List[Dict[str, Any]]:
    """POST …/ask?format=markdown — the answer comes as a stream of server-sent events; every event is the answer so far.
    The stream is read for at most `deadline` seconds: a stream that stays open after the answer must not keep the
    player waiting — what came by then is the answer (no event at all → an error)."""
    if not configured():
        raise GitBookError("GITBOOK_API_TOKEN не задан")
    import asyncio
    import httpx
    events: List[Dict[str, Any]] = []

    def take(block: str) -> None:
        data = "\n".join(x[5:].lstrip() for x in block.split("\n") if x.startswith("data:"))
        if data and data != "[DONE]":
            try:
                events.append(json.loads(data))
            except ValueError:
                pass

    async def read() -> None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(deadline, connect=10.0)) as cl:
            async with cl.stream("POST", API + path, params={"format": "markdown"}, json=body,
                                 headers={"Authorization": f"Bearer {token()}", "Accept": "text/event-stream"}) as r:
                if r.status_code >= 400:
                    txt = (await r.aread()).decode("utf-8", "replace")
                    raise GitBookError(f"GitBook {r.status_code}: {txt[:200]}")
                buf = ""
                it = r.aiter_text().__aiter__()
                while True:
                    # once an answer with sources is in, 4 s of silence = the answer is complete
                    done = any(isinstance(e, dict) and ((e.get("answer") or {}).get("sources")) for e in events)
                    try:
                        chunk = await (asyncio.wait_for(it.__anext__(), timeout=4.0) if done else it.__anext__())
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        break
                    buf += chunk.replace("\r\n", "\n")
                    while "\n\n" in buf:
                        block, buf = buf.split("\n\n", 1)
                        take(block)
                if buf.strip():
                    take(buf)
    try:
        await asyncio.wait_for(read(), timeout=deadline)
    except (asyncio.TimeoutError, httpx.ReadTimeout):
        if not events:
            raise GitBookError(f"GitBook не ответил за {int(deadline)} с")
        logger.info("GitBook AI: the stream stayed open — the answer so far is taken")
    return events


async def note_ai(db, outcome: str) -> None:
    """Counters of the support AI for the admin (answered / no answer / error) — per MSK day and in total."""
    try:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await db.admin_settings.update_one({"type": "gitbook_state"},
                                           {"$inc": {f"ai.total.{outcome}": 1, f"ai.days.{day}.{outcome}": 1}}, upsert=True)
    except Exception:  # noqa: BLE001
        pass

