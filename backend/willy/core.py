"""Willy GRAM — the support assistant. No external AI: answers come from the Russian answer base (db.willy_answers),
the player's own numbers and the Справочник.

Flow of one player message (chat status "bot"):
  1. seed phrase?           → hide the message, warn, stop
  2. translate to Russian   (LibreTranslate, kept 1 day)
  3. rules (money, human…)  → hand over to a human at once
  4. search                 → high confidence: the answer; medium: «О чём вопрос?» buttons; low: a human
  5. the answer template is translated to the player's language (kept 30 days after the last use) and only then
     filled with the player's numbers — so one cached translation serves every player.
Every step is written to db.willy_log (which answer, how sure, what was done); misses go to db.willy_gaps.

Willy only READS the player's data. He never changes anything and never asks for codes or seed phrases."""
import hashlib
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import index as _index
from .phrases import p as _p
from .rules import REASONS, check as _rules, looks_like_seed
from .text import is_russian, norm

logger = logging.getLogger(__name__)

LANGS = ["ru", "en", "es", "zh", "fr", "de", "ja", "ko", "id"]
BOT_NAME = "Willy GRAM"
DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": True,
    "high": 0.50,          # ≥ high → answer
    "low": 0.42,           # < low → a human («Нет в базе»); between → «О чём вопрос?»
    "sem_high": 0.87,      # the same thresholds for the meaning engine (e5 cosine runs high: check with «Проверить вопрос»)
    "sem_low": 0.83,
    "handoff_on_low": True,
    "rules": {r: {"enabled": True, "words": []} for r in ("money", "human", "complaint", "bug", "seizure", "hack", "dispute")},
}
Q_TTL_MIN = 24 * 60            # a translated question is a one-off: kept one day
A_TTL_MIN = 30 * 24 * 60       # an answer translation lives 30 days after its last use

_db = None
_hooks: Dict[str, Any] = {}


def init(db, **hooks) -> None:
    """hooks: ws_manager, notify_telegram(user_doc, text, reply_markup=None), agent_panel_url, agent_panel_markup,
    public_url() — given by support_handler so this module does not import it back."""
    global _db
    _db = db
    _hooks.update(hooks)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lang(v: Optional[str]) -> str:
    v = (v or "").lower()[:2]
    return v if v in LANGS else "en"


async def settings(db=None) -> Dict[str, Any]:
    db = db if db is not None else _db
    s = await db.willy_settings.find_one({"_id": "main"}) or {}
    out = {**DEFAULT_SETTINGS, **{k: v for k, v in s.items() if k != "_id"}}
    rules = {**DEFAULT_SETTINGS["rules"]}
    for k, v in (s.get("rules") or {}).items():
        rules[k] = {**rules.get(k, {}), **(v or {})}
    out["rules"] = rules
    return out


async def is_on(db=None) -> bool:
    db = db if db is not None else _db
    s = await settings(db)
    if not s.get("enabled", True):
        return False
    return bool(await db.willy_answers.find_one({"enabled": True}, {"_id": 1}))


# ───────────────────────── translation (LibreTranslate only, cached) ─────────────────────────

async def tr(db, text: str, target: str, source: str = "ru", ttl_min: float = A_TTL_MIN) -> Optional[str]:
    """Translate with {placeholders} kept. None when LibreTranslate is not set up or failed.
    The cache entry's life is extended on every use (sliding), so answers in use never expire."""
    if not text or not text.strip() or target == source:
        return text
    from translation_service import translate_libre_protected, libretranslate_configured
    key = "willy|" + hashlib.sha1(f"{source}|{target}|{text}".encode("utf-8")).hexdigest()
    now = _now()
    try:
        hit = await db.translation_cache.find_one({"_id": key}, {"text": 1, "expires_at": 1})
        if hit and hit.get("text"):
            exp = hit.get("expires_at")
            if isinstance(exp, datetime) and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if not isinstance(exp, datetime) or exp > now:
                await db.translation_cache.update_one({"_id": key}, {"$set": {"expires_at": now + timedelta(minutes=ttl_min)}})
                return hit["text"]
    except Exception:
        pass
    if not libretranslate_configured():
        return None
    try:
        out = await translate_libre_protected(text, target, source, protect_emoji=True)
    except Exception as e:  # noqa: BLE001
        logger.info(f"willy translate {source}->{target} failed: {e}")
        return None
    if not out:
        return None
    try:
        await db.translation_cache.update_one({"_id": key}, {"$set": {
            "text": out, "lang": target, "kind": "willy", "keep": False, "created_at": now.isoformat(),
            "expires_at": now + timedelta(minutes=ttl_min)}}, upsert=True)
    except Exception:
        pass
    return out


# ───────────────────────── rendering an answer ─────────────────────────

_VAR = re.compile(r"\{(\w+)\}")


def fill(text: str, v: Dict[str, Any]) -> str:
    return _VAR.sub(lambda m: str(v[m.group(1)]) if m.group(1) in v else m.group(0), text or "")


def _res_names(text: str, lang: str) -> str:
    """{res:energy} → the resource name; {biz:helios} → the business name."""
    def r(m):
        try:
            from wiki_content.effects import RES
            return (RES.get(m.group(1)) or {}).get(lang) or (RES.get(m.group(1)) or {}).get("en") or m.group(1)
        except Exception:
            return m.group(1)

    def b(m):
        try:
            from wiki_content.effects import BIZ
            n = BIZ.get(m.group(1)) or {}
            return n.get(lang) or n.get("en") or m.group(1)
        except Exception:
            return m.group(1)
    text = re.sub(r"\{res:(\w+)\}", r, text or "")
    return re.sub(r"\{biz:(\w+)\}", b, text)


_CFG = re.compile(r"\{cfg:([a-z0-9]+)((?::[\w]+)*)\}")


async def _cfg(db, text: str, lang: str, user: Optional[Dict[str, Any]]) -> str:
    """Live numbers of the game config in an answer: {cfg:prod:helios:3}, {cfg:upg:helios:3}, {cfg:pass:5}, {cfg:have:quartz}…
    (willy/answers_gen.py). Filled at the moment of answering, after the translation, in the player's language."""
    if "{cfg:" not in (text or ""):
        return text
    import business_config as bc
    from .player import _n, _w

    def rn(r):
        try:
            from wiki_content.effects import RES
            return (RES.get(r) or {}).get(lang) or (RES.get(r) or {}).get("en") or r
        except Exception:
            return r

    def N(x, d=0):
        return _n(x, d, lang)

    cache: Dict[str, Any] = {}

    async def one(kind: str, args: List[str]) -> Optional[str]:
        try:
            if kind in ("prod", "prodh", "prodshift"):
                v = float(bc.get_production(args[0], int(args[1])) or 0)
                return N(v) if kind == "prod" else N(v / 24, 2) if kind == "prodh" else N(v / 3, 1)
            if kind in ("cons", "consshift"):
                lv = (bc.BUSINESS_LEVELS.get(args[0]) or {}).get("consumption", {}).get(int(args[1])) or {}
                k = 1 if kind == "cons" else 3
                return ", ".join(f"{N(q / k, 0 if k == 1 else 1)} {rn(r)}" for r, q in lv.items()) or "—"
            if kind == "store":
                return N(bc.get_storage_capacity(args[0], int(args[1])))
            if kind in ("upg", "upgsum"):
                t = bc.UPGRADE_COSTS_TABLE.get(args[0]) or {}
                lvls = [int(args[1])] if kind == "upg" else list(range(2, int(args[1]) + 1))
                city, res = 0.0, {}
                for L in lvls:
                    c = t.get(L) or {}
                    city += float(c.get("city") or 0)
                    if c.get("resource"):
                        res[c["resource"]] = res.get(c["resource"], 0) + int(c.get("qty") or 0)
                return f"{N(city)} $CITY" + "".join(f" + {q} × {rn(r)}" for r, q in res.items())
            if kind == "have":
                if not user:
                    return "—"
                r = args[0]
                res = user.get("resources") or {}
                reg = float(res.get(r) or 0)
                tut = float(res.get(f"{r}_tutorial") or 0)
                return N(reg) + (f" (+{N(tut)} 🎁)" if tut >= 1 else "")
            if kind in ("city", "sys"):
                import market_maker as mm
                if "mm" not in cache:
                    cache["mm"] = await mm.get_config(db)
                if kind == "sys":
                    from core.pricing import level0_price_ton
                    return N(await level0_price_ton(db, args[0]) * 1000, 2)
                cfg = cache["mm"]
                b, s_ = mm.prices_city(cfg, args[0])
                out = []
                out.append(f"⬇ {N(b, 2)} $CITY" if args[0] in (cfg.get("buy_resources") or []) and b else "⬇ —")
                out.append(f"⬆ {N(s_, 2)} $CITY" if args[0] in (cfg.get("sell_resources") or []) and s_ else "⬆ —")
                return " · ".join(out)
            if kind in ("pass", "passxp", "xp"):
                import city_pass as cp
                if "cp" not in cache:
                    cache["cp"] = await cp.get_config(db)
                cfg = cache["cp"]
                if kind == "passxp":
                    th = cp.thresholds(cfg)
                    n = int(args[0])
                    return N(th[n - 1]) if 0 < n <= len(th) else "—"
                if kind == "xp":
                    k = args[0]
                    v = (cfg.get("xp") or {}).get("sale_per_0_01_ton" if k == "sale" else k)
                    return f"{N(v or 0)} XP" + (" / 0,01 GRAM" if k == "sale" else "")
                lvl = args[0]

                def fmt(rw):
                    parts = []
                    for x in rw or []:
                        t = x.get("type") or x.get("kind")
                        cnt = int(x.get("count") or 1)
                        if t == "t3":
                            parts.append(f"{cnt} × {rn(x.get('resource'))}")
                        elif t == "city":
                            parts.append(f"{N(x.get('amount') or 0)} $CITY")
                        else:
                            try:
                                from wiki_content.effects import BOOST
                                nm = ((BOOST.get(t) or {}).get("n") or {})
                                nm = nm.get(lang) or nm.get("en") or t
                            except Exception:
                                nm = t
                            h = x.get("hours")
                            parts.append(f"{nm}" + (f" {h} {_w('h', lang)}" if h else "") + (f" × {cnt}" if cnt > 1 else ""))
                    return ", ".join(parts) or "—"
                fr = fmt((cfg.get("rewards_free") or {}).get(lvl))
                pr = fmt((cfg.get("rewards_premium") or {}).get(lvl))
                return f"🆓 {fr} · ⭐ {pr}"
            if kind == "daily":
                d = await db.tasks_config.find_one({"key": "daily_rewards"}, {"_id": 0}) or {}
                rw = [int(x) for x in (d.get("rewards") or [5, 10, 20, 35, 50, 75, 150])]
                i = int(args[0]) - 1
                return N(rw[i]) if 0 <= i < len(rw) else "—"
        except Exception as e:  # noqa: BLE001
            logger.debug(f"willy cfg {kind}{args}: {e}")
        return None

    out = []
    pos = 0
    for m in _CFG.finditer(text):
        out.append(text[pos:m.start()])
        v = await one(m.group(1), [x for x in m.group(2).split(":") if x])
        out.append(v if v is not None else "—")
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


async def _gvars(db) -> Dict[str, Any]:
    from routes.wiki import wiki_vars
    try:
        return await wiki_vars(db)
    except Exception:
        return {}


async def _pvars(db, user: Optional[Dict[str, Any]], lang: str = "ru") -> Dict[str, Any]:
    if not user:
        from .player import sample_vars
        return sample_vars()
    from .player import player_vars
    try:
        return await player_vars(db, user, lang)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"willy player vars: {e}")
        return {}


async def _checks(db, ans: Dict[str, Any], user: Optional[Dict[str, Any]], lang: str, gv: Dict[str, Any]) -> List[Dict[str, str]]:
    ids = [c for c in (ans.get("checks") or []) if c]
    if not ids or not user:
        return []
    from routes.wiki import _account, _check, _pick, fill1, LANGS as WL
    from wiki_content.ui import CHECKS
    try:
        a = await _account(db, user)
    except Exception:
        return []
    out = []
    for cid in ids:
        c = _check(cid, a, gv)
        if not c:
            continue
        tx = _pick({lg: CHECKS.get(cid, {}).get(lg, {}) for lg in WL}, lang)
        vv = {**gv, **c["vars"]}
        label = fill1(tx.get("t", cid), vv)
        detail = fill1(tx.get(c["state"]) or tx.get("ok") or "", vv)
        out.append({"state": c["state"], "text": _res_names(f"{label}: {detail}" if detail else label, lang), "fix": c.get("fix") or ""})
    return out


async def _article(db, slug: Optional[str], lang: str) -> Optional[Dict[str, Any]]:
    if not slug:
        return None
    d = await db.wiki_articles.find_one({"slug": slug, "published": {"$ne": False}}, {"_id": 0, "slug": 1, "icon": 1, "i18n": 1, "show": 1})
    if not d:
        return None
    i = d.get("i18n") or {}
    t = (i.get(lang) or {}).get("t") or (i.get("en") or {}).get("t") or (i.get("ru") or {}).get("t") or slug
    gv = await _gvars(db)
    from routes.wiki import fill as wfill
    return {"slug": slug, "title": wfill(t, gv), "icon": d.get("icon") or "📖", "has_show": bool(d.get("show"))}


async def render(db, ans: Dict[str, Any], lang: str, user: Optional[Dict[str, Any]], *, for_agent: bool = False) -> Dict[str, Any]:
    """{text, text_ru, buttons, checks, translated}. Template → translated (cached) → numbers filled in."""
    gv = await _gvars(db)
    tpl = ans.get("text") or ""
    out_lang = "ru" if for_agent else lang
    translated = True
    if out_lang != "ru":
        t = await tr(db, tpl, out_lang, "ru")
        if t is None:
            t, translated = tpl, False
        tpl_l = t
    else:
        tpl_l = tpl
    g = {k: (str(x) if not isinstance(x, bool) else x) for k, x in gv.items()}
    shown = out_lang if translated else "ru"
    pv = await _pvars(db, user, shown)
    text = _res_names(await _cfg(db, fill(tpl_l, {**g, **pv}), shown, user), shown)
    pv_ru = pv if shown == "ru" else await _pvars(db, user, "ru")
    text_ru = _res_names(await _cfg(db, fill(tpl, {**g, **pv_ru}), "ru", user), "ru")
    buttons = []
    art = await _article(db, ans.get("wiki"), out_lang)
    if art:
        buttons.append({"kind": "wiki", "slug": art["slug"], "title": art["title"], "icon": art["icon"]})
        if ans.get("show", True) and art["has_show"]:
            buttons.append({"kind": "show", "slug": art["slug"]})
    if ans.get("route"):
        buttons.append({"kind": "route", "path": ans["route"]})
    checks = await _checks(db, ans, user, out_lang, gv)
    return {"text": text, "text_ru": text_ru, "buttons": buttons, "checks": checks, "translated": translated}


# ───────────────────────── search ─────────────────────────

async def search(db, q_orig: str, q_ru: str, k: int = 5, agent: bool = False) -> Tuple[List[Tuple[str, float]], str]:
    """Best answers [(id, confidence 0..1)] and which engine decided ("kw" / "sem").
    Answers marked «только для оператора» (agent_only) are found only for the agent's draft."""
    s = await settings(db)
    idx = await _index.get(db)
    kw = idx.search(q_ru or q_orig, k, agent=agent) if (q_ru or q_orig) else []
    sem = await _index.semantic([q_ru, q_orig] if q_orig != q_ru else [q_ru], k)
    if not sem:
        return kw, "kw"
    # the meaning engine's scores are mapped onto the keyword scale with the admin's thresholds
    hi, lo, shi, slo = s["high"], s["low"], s["sem_high"], s["sem_low"]

    def m(x: float) -> float:
        if x >= shi:
            return hi + (x - shi) / max(1e-6, 1 - shi) * (1 - hi)
        if x >= slo:
            return lo + (x - slo) / max(1e-6, shi - slo) * (hi - lo)
        return x / max(1e-6, slo) * lo
    merged: Dict[str, float] = {aid: sc for aid, sc in kw}
    eng = "kw"
    for aid, sc in sem:
        if aid in idx.answers and (agent or aid not in idx.agent_only) and m(sc) > merged.get(aid, 0):
            merged[aid] = m(sc)
    top = sorted(merged.items(), key=lambda kv: -kv[1])[:k]
    if top and (not kw or top[0][0] != kw[0][0] or top[0][1] > kw[0][1] + 1e-9):
        eng = "sem"
    return top, eng


# ───────────────────────── messages ─────────────────────────

def _bot_msg(chat_id: str, content: str, lang: str, willy: Dict[str, Any], original: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()), "chat_id": chat_id, "sender_type": "bot", "sender_id": "willy", "sender_name": BOT_NAME,
        "content": content, "original_content": original if original and original != content else None, "lang": lang,
        "translations": {}, "image_url": None, "willy": willy, "created_at": _now().isoformat(),
    }


async def _post(db, chat: Dict[str, Any], msg: Dict[str, Any], user: Optional[Dict[str, Any]], tg: bool) -> Dict[str, Any]:
    await db.support_messages.insert_one(msg.copy())
    await db.support_chats.update_one({"id": chat["id"]}, {"$set": {"last_activity": msg["created_at"]},
                                                           "$inc": {"messages_count": 1}})
    ws = _hooks.get("ws_manager")
    if ws:
        try:
            await ws.send_to_user(chat["user_id"], {"type": "new_message", "chat_id": chat["id"], "message": msg})
        except Exception:
            pass
    if tg and user:
        await _to_telegram(db, user, msg)
    return msg


async def _to_telegram(db, user: Dict[str, Any], msg: Dict[str, Any]) -> None:
    """A player who writes through the bot gets Willy's reply in the bot."""
    send = _hooks.get("notify_telegram")
    if not send:
        return
    import html as _h
    lang = msg.get("lang") or "en"
    w = msg.get("willy") or {}
    lines = [f"🤖 <b>{BOT_NAME}</b>", "", _h.escape(msg.get("content") or "")]
    for c in w.get("checks") or []:
        lines.append(("✅ " if c["state"] == "ok" else "❌ " if c["state"] == "fail" else "ℹ️ ") + _h.escape(c["text"]))
    for i, o in enumerate(w.get("options") or [], 1):
        lines.append(f"{i}. {_h.escape(o['title'])}")
    kb = []
    base = ""
    try:
        base = await _hooks["public_url"]() if _hooks.get("public_url") else ""
    except Exception:
        base = ""
    for b in w.get("buttons") or []:
        if b.get("kind") == "wiki" and base:
            kb.append([{"text": f"{b.get('icon', '📖')} {b.get('title', '')}"[:60], "url": f"{base}/wiki/{b['slug']}?lang={lang}"}])
    if w.get("kind") in ("answer", "clarify"):
        lines += ["", "<i>" + _h.escape(_p("tg_footer", lang)) + "</i>"]
    try:
        from telegram_bot import TelegramBot
        d = TelegramBot.SUPPORT_L.get("close", {})
        kb.append([{"text": d.get(lang) or d.get("en") or "End chat", "callback_data": "support_close"}])
    except Exception:
        pass
    try:
        await send(user, "\n".join(lines), reply_markup={"inline_keyboard": kb} if kb else None)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"willy tg: {e}")


async def _log(db, **row) -> None:
    try:
        await db.willy_log.insert_one({"id": str(uuid.uuid4()), "at": _now().isoformat(), **row})
    except Exception:
        pass


async def _gap(db, q_ru: str, q_orig: str, lang: str, best: Optional[Tuple[str, float]], why: str) -> None:
    n = norm(q_ru or q_orig)[:300]
    if not n:
        return
    gid = hashlib.sha1(n.encode("utf-8")).hexdigest()[:16]
    try:
        await db.willy_gaps.update_one({"id": gid}, {
            "$setOnInsert": {"id": gid, "q_ru": n, "first_at": _now().isoformat(), "status": "open"},
            "$set": {"last_at": _now().isoformat(), "why": why,
                     "best": {"answer_id": best[0], "conf": round(best[1], 3)} if best else None},
            "$inc": {"count": 1},
            "$addToSet": {"examples": {"$each": [f"[{lang}] {q_orig[:200]}"]}},
        }, upsert=True)
        await db.willy_gaps.update_one({"id": gid, "status": "resolved"}, {"$set": {"status": "open"}})
    except Exception as e:  # noqa: BLE001
        logger.debug(f"willy gap: {e}")


async def _answers(db, ids: List[str]) -> Dict[str, Dict[str, Any]]:
    rows = await db.willy_answers.find({"id": {"$in": ids}}, {"_id": 0}).to_list(len(ids) + 1)
    return {r["id"]: r for r in rows}


async def _title(db, ans: Dict[str, Any], lang: str) -> str:
    t = ans.get("title") or ""
    if lang == "ru":
        return t
    return (await tr(db, t, lang, "ru")) or t


async def send_answer(db, chat, user, ans, lang, *, conf: float, q: str = "", q_ru: str = "", alts=None,
                      engine: str = "kw", tg: bool = False, picked: bool = False) -> Dict[str, Any]:
    r = await render(db, ans, lang, user)
    w = {"kind": "answer", "answer_id": ans["id"], "conf": round(conf, 3), "engine": engine, "buttons": r["buttons"],
         "checks": r["checks"], "alts": [a for a in (alts or []) if a != ans["id"]][:4], "feedback": None,
         "handoff_offer": bool(ans.get("handoff"))}
    msg = _bot_msg(chat["id"], r["text"], lang if r["translated"] else "ru", w, original=r["text_ru"])
    await _post(db, chat, msg, user, tg)
    await db.willy_answers.update_one({"id": ans["id"]}, {"$inc": {"stats.shown": 1}, "$set": {"stats.last_at": _now().isoformat()}})
    await _log(db, chat_id=chat["id"], user_id=chat["user_id"], q=q[:500], q_ru=q_ru[:500], lang=lang, outcome="answer",
               answer_id=ans["id"], answer_title=ans.get("title"), conf=round(conf, 3), engine=engine, picked=picked)
    if ans.get("handoff"):
        await handoff(db, chat, user, ans.get("handoff_reason") or "by_answer", lang,
                      q=q, q_ru=q_ru, tg=tg, quiet=True)
    return msg


async def send_clarify(db, chat, user, cands: List[Tuple[str, float]], lang, *, q="", q_ru="", key="clarify", tg=False,
                       engine="kw") -> Optional[Dict[str, Any]]:
    ids = [c[0] for c in cands[:3]]
    rows = await _answers(db, ids)
    opts = []
    for aid in ids:
        a = rows.get(aid)
        if a:
            opts.append({"answer_id": aid, "title": await _title(db, a, lang)})
    if not opts:
        return None
    w = {"kind": "clarify", "options": opts, "conf": round(cands[0][1], 3) if cands else 0, "engine": engine}
    msg = _bot_msg(chat["id"], _p(key, lang), lang, w)
    await _post(db, chat, msg, user, tg)
    await _log(db, chat_id=chat["id"], user_id=chat["user_id"], q=q[:500], q_ru=q_ru[:500], lang=lang, outcome="clarify",
               conf=w["conf"], engine=engine, options=ids)
    return msg


# ───────────────────────── a human ─────────────────────────

async def _eta(db, lang: str) -> str:
    """«Operator is online» / «answer today from 10:00 MSK» from the agents' working hours."""
    ws = _hooks.get("ws_manager")
    if ws and getattr(ws, "agent_conns", None):
        return _p("eta_online", lang)
    try:
        from zoneinfo import ZoneInfo
    except Exception:  # pragma: no cover
        return _p("eta_later", lang)
    agents = await db.support_agents.find({"is_removed": {"$ne": True}, "hours": {"$exists": True}}, {"_id": 0, "hours": 1}).to_list(200)
    msk = ZoneInfo("Europe/Moscow")
    now = _now()
    best = None
    for ag in agents:
        h = ag.get("hours") or {}
        days = [int(d) for d in (h.get("days") or [])]
        if not days or not h.get("from") or not h.get("to"):
            continue
        try:
            tz = ZoneInfo(h.get("tz") or "Europe/Moscow")
            fh, fm = [int(x) for x in str(h["from"]).split(":")[:2]]
            th, tm = [int(x) for x in str(h["to"]).split(":")[:2]]
        except Exception:
            continue
        loc = now.astimezone(tz)
        for add in range(0, 8):
            d = (loc + timedelta(days=add)).date()
            if d.weekday() not in days:
                continue
            start = datetime(d.year, d.month, d.day, fh, fm, tzinfo=tz)
            end = datetime(d.year, d.month, d.day, th, tm, tzinfo=tz)
            if end <= start:
                end += timedelta(days=1)
            if start <= loc < end:
                return _p("eta_later", lang)           # working hours now, just not at the screen
            if start > loc:
                if best is None or start < best:
                    best = start
                break
    if not best:
        return _p("eta_later", lang)
    b = best.astimezone(msk)
    today = now.astimezone(msk).date()
    if b.date() == today:
        when = _p("today", lang)
    elif b.date() == today + timedelta(days=1):
        when = _p("tomorrow", lang)
    else:
        when = _p("on_date", lang, d=b.strftime("%d.%m"))
    return _p("eta_hours", lang, when=when, time=b.strftime("%H:%M"))


async def _summary(db, chat, user, reason: str, lang: str, q: str, q_ru: str) -> str:
    """What the agent sees first (Russian): who, what, why, what was checked."""
    pv = await _pvars(db, user) if user else {}
    lines = [f"🤖 Willy GRAM передал чат. Причина: {REASONS.get(reason, reason)}.",
             f"Игрок: {pv.get('name', '—')} · ID {chat.get('user_id')} · язык: {lang}"]
    if q:
        lines.append(f"Вопрос: {q[:400]}")
    if q_ru and q_ru != q:
        lines.append(f"Вопрос (RU): {q_ru[:400]}")
    lines.append(f"Баланс: основной {pv.get('balance_main', '—')} $CITY, бонусный {pv.get('balance_bonus', '—')} $CITY, "
                 f"заморожено {pv.get('frozen', '—')}")
    lines.append(f"Бизнесов: {pv.get('biz_count', '—')} (первый — {pv.get('biz_name', '—')}, ур. {pv.get('biz_level', '—')}); "
                 f"2FA {pv.get('twofa', '—')}, кошелёк {pv.get('wallet', '—')}")
    try:
        txs = await db.transactions.find({"user_id": chat.get("user_id"),
                                          "tx_type": {"$in": ["deposit", "withdrawal", "withdraw", "instant_withdraw"]}},
                                         {"_id": 0, "id": 1, "tx_type": 1, "amount_ton": 1, "amount": 1, "status": 1, "created_at": 1}
                                         ).sort("created_at", -1).limit(3).to_list(3)
        for t in txs:
            amt = t.get("amount_ton", t.get("amount", 0)) or 0
            lines.append(f"Платёж: {t.get('tx_type')} {float(amt):.4f} GRAM · {t.get('status') or '—'} · "
                         f"{str(t.get('created_at', ''))[:16].replace('T', ' ')} · {str(t.get('id', ''))[:12]}")
    except Exception:
        pass
    last = await db.willy_log.find({"chat_id": chat["id"], "outcome": "answer"}, {"_id": 0, "answer_title": 1, "conf": 1}
                                   ).sort("at", -1).limit(2).to_list(2)
    for r in last:
        lines.append(f"Willy уже ответил: «{r.get('answer_title')}» (уверенность {int(float(r.get('conf') or 0) * 100)}%)")
    return "\n".join(lines)


async def handoff(db, chat, user, reason: str, lang: str, *, q: str = "", q_ru: str = "", tg: bool = False,
                  quiet: bool = False) -> None:
    """Hand the chat over to people: the queue «Нужен человек» (status new) with the reason, the agents get a push."""
    now = _now().isoformat()
    upd = {"status": "new", "mode": "human", "handoff_reason": reason, "handoff_at": now, "user_lang": lang,
           "unread_for_agent": 1, "handoff_q": (q or "")[:500], "handoff_q_ru": (q_ru or "")[:500]}
    res = await db.support_chats.update_one({"id": chat["id"], "status": "bot"}, {"$set": upd})
    if not res.modified_count:
        return
    from .rules import REASONS as R
    summ = await _summary(db, chat, user, reason, lang, q, q_ru)
    sysm = {"id": str(uuid.uuid4()), "chat_id": chat["id"], "sender_type": "system", "sender_id": "willy",
            "content": summ, "system_key": "willy_summary", "system_extra": {"reason": reason, "lang": lang},
            "agent_only": True, "image_url": None, "created_at": now}
    await db.support_messages.insert_one(sysm.copy())
    text = (_p("handoff", lang) + " " + await _eta(db, lang)).strip()
    if not quiet:
        await _post(db, chat, _bot_msg(chat["id"], text, lang, {"kind": "handoff", "reason": reason}), user, tg)
    else:
        await _post(db, chat, _bot_msg(chat["id"], await _eta(db, lang), lang, {"kind": "handoff", "reason": reason}), user, tg)
    await _log(db, chat_id=chat["id"], user_id=chat["user_id"], q=q[:500], q_ru=q_ru[:500], lang=lang, outcome="handoff", reason=reason)
    ws = _hooks.get("ws_manager")
    full = await db.support_chats.find_one({"id": chat["id"]}, {"_id": 0})
    if ws and full:
        try:
            await ws.broadcast_to_all_agents({"type": "new_chat", "chat": full})
        except Exception:
            pass
    send = _hooks.get("notify_telegram")
    if send:
        try:
            agents = await db.support_agents.find({"is_removed": {"$ne": True}}, {"_id": 0, "telegram_id": 1}).to_list(100)
            name = (full or chat).get("user_username") or "игрок"
            for ag in agents:
                url = await _hooks["agent_panel_url"](ag.get("telegram_id")) if _hooks.get("agent_panel_url") else None
                mk = _hooks["agent_panel_markup"](url) if (url and _hooks.get("agent_panel_markup")) else None
                await send({"telegram_chat_id": ag.get("telegram_id")},
                           f"🆘 Нужен человек: {name}\nПричина: {R.get(reason, reason)} · язык: {lang}", reply_markup=mk)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"willy agent notify: {e}")


# ───────────────────────── entry points ─────────────────────────

async def on_user_message(db, chat: Dict[str, Any], msg: Dict[str, Any], user: Optional[Dict[str, Any]], *,
                          tg: bool = False) -> List[Dict[str, Any]]:
    """Called after a player's message is stored in a chat with status "bot". Returns Willy's replies."""
    if chat.get("status") != "bot":
        return []
    text = (msg.get("content") or "").strip()
    lang = _lang((user or {}).get("language"))
    try:
        from translation_service import detect_language
        dl = detect_language(text)
        if dl and dl in LANGS and len(text) >= 12:
            lang = dl
    except Exception:
        pass
    before = await db.support_messages.count_documents({"chat_id": chat["id"], "sender_type": "bot"})
    if looks_like_seed(text):
        await db.support_messages.update_one({"id": msg["id"]}, {"$set": {"content": "[скрыто: похоже на seed-фразу]", "hidden": True}})
        msg["content"] = "[скрыто: похоже на seed-фразу]"
        await _post(db, chat, _bot_msg(chat["id"], _p("seed", lang), lang, {"kind": "info"}), user, tg)
        await _log(db, chat_id=chat["id"], user_id=chat["user_id"], q="[seed]", lang=lang, outcome="seed")
        return await _new_since(db, chat["id"], before)
    if not text:
        return []
    s = await settings(db)
    q_ru = text if is_russian(text) else (await tr(db, text, "ru", "auto", Q_TTL_MIN) or text)
    reason = _rules([text, q_ru], s)
    if reason:
        await handoff(db, chat, user, reason, lang, q=text, q_ru=q_ru, tg=tg)
        return await _new_since(db, chat["id"], before)
    cands, eng = await search(db, text, q_ru)
    best = cands[0] if cands else None
    hi, lo = float(s["high"]), float(s["low"])
    if best and best[1] >= hi:
        rows = await _answers(db, [best[0]])
        if rows.get(best[0]):
            await db.support_chats.update_one({"id": chat["id"]}, {"$set": {"willy_last_q": text[:500], "willy_last_q_ru": q_ru[:500]}})
            await send_answer(db, chat, user, rows[best[0]], lang, conf=best[1], q=text, q_ru=q_ru,
                              alts=[c[0] for c in cands[1:]], engine=eng, tg=tg)
            return await _new_since(db, chat["id"], before)
    if best and best[1] >= lo:
        await _gap(db, q_ru, text, lang, best, "medium")
        await db.support_chats.update_one({"id": chat["id"]}, {"$set": {"willy_last_q": text[:500], "willy_last_q_ru": q_ru[:500]}})
        if await send_clarify(db, chat, user, cands, lang, q=text, q_ru=q_ru, tg=tg, engine=eng):
            return await _new_since(db, chat["id"], before)
    await _gap(db, q_ru, text, lang, best, "low")
    if s.get("handoff_on_low", True):
        await handoff(db, chat, user, "no_answer", lang, q=text, q_ru=q_ru, tg=tg)
    else:
        await send_clarify(db, chat, user, cands, lang, q=text, q_ru=q_ru, tg=tg, engine=eng)
    return await _new_since(db, chat["id"], before)


async def _new_since(db, chat_id: str, before: int) -> List[Dict[str, Any]]:
    rows = await db.support_messages.find({"chat_id": chat_id, "sender_type": "bot"}, {"_id": 0}).sort("created_at", 1).to_list(500)
    return rows[before:]


async def feedback(db, chat, user, message_id: str, helped: bool) -> List[Dict[str, Any]]:
    m = await db.support_messages.find_one({"id": message_id, "chat_id": chat["id"], "sender_type": "bot"}, {"_id": 0})
    if not m or (m.get("willy") or {}).get("kind") != "answer" or (m.get("willy") or {}).get("feedback") is not None:
        return []
    w = m["willy"]
    lang = m.get("lang") or _lang((user or {}).get("language"))
    before = await db.support_messages.count_documents({"chat_id": chat["id"], "sender_type": "bot"})
    await db.support_messages.update_one({"id": message_id}, {"$set": {"willy.feedback": "yes" if helped else "no"}})
    await db.willy_answers.update_one({"id": w["answer_id"]}, {"$inc": {"stats.helped" if helped else "stats.not_helped": 1}})
    await _log(db, chat_id=chat["id"], user_id=chat["user_id"], outcome="feedback", answer_id=w["answer_id"], helped=helped)
    if helped:
        await db.support_chats.update_one({"id": chat["id"]}, {"$set": {"willy_no": 0}})
        await _post(db, chat, _bot_msg(chat["id"], _p("helped", lang), lang, {"kind": "info"}), user, False)
        return await _new_since(db, chat["id"], before)
    r = await db.support_chats.find_one_and_update({"id": chat["id"]}, {"$inc": {"willy_no": 1}}, return_document=True)
    q, q_ru = (r or {}).get("willy_last_q", ""), (r or {}).get("willy_last_q_ru", "")
    await _gap(db, q_ru, q, lang, (w["answer_id"], float(w.get("conf") or 0)), "not_helped")
    if int((r or {}).get("willy_no") or 0) >= 2 or not w.get("alts"):
        await handoff(db, chat, user, "not_helped", lang, q=q, q_ru=q_ru)
    else:
        await send_clarify(db, chat, user, [(a, 0.0) for a in w["alts"]], lang, q=q, q_ru=q_ru, key="not_helped")
    return await _new_since(db, chat["id"], before)


async def pick(db, chat, user, message_id: str, answer_id: str) -> List[Dict[str, Any]]:
    m = await db.support_messages.find_one({"id": message_id, "chat_id": chat["id"], "sender_type": "bot"}, {"_id": 0})
    opts = [o["answer_id"] for o in ((m or {}).get("willy") or {}).get("options") or []]
    if answer_id not in opts or chat.get("status") != "bot":
        return []
    lang = m.get("lang") or _lang((user or {}).get("language"))
    before = await db.support_messages.count_documents({"chat_id": chat["id"], "sender_type": "bot"})
    await db.support_messages.update_one({"id": message_id}, {"$set": {"willy.picked": answer_id}})
    rows = await _answers(db, [answer_id])
    if rows.get(answer_id):
        c = await db.support_chats.find_one({"id": chat["id"]}, {"_id": 0}) or chat
        await send_answer(db, chat, user, rows[answer_id], lang, conf=1.0, q=c.get("willy_last_q", ""),
                          q_ru=c.get("willy_last_q_ru", ""), alts=[o for o in opts if o != answer_id], picked=True)
        # what the player picked becomes a phrasing suggestion for that answer
        if c.get("willy_last_q_ru"):
            await db.willy_answers.update_one({"id": answer_id}, {"$addToSet": {"suggested": c["willy_last_q_ru"][:300]}})
    return await _new_since(db, chat["id"], before)


async def call_human(db, chat, user) -> List[Dict[str, Any]]:
    if chat.get("status") != "bot":
        return []
    lang = _lang((user or {}).get("language"))
    before = await db.support_messages.count_documents({"chat_id": chat["id"], "sender_type": "bot"})
    c = await db.support_chats.find_one({"id": chat["id"]}, {"_id": 0}) or chat
    await handoff(db, chat, user, "human", c.get("user_lang") or lang, q=c.get("willy_last_q", ""), q_ru=c.get("willy_last_q_ru", ""))
    return await _new_since(db, chat["id"], before)


# ───────────────────────── for the agent ─────────────────────────

async def draft(db, chat: Dict[str, Any], n: int = 0) -> Dict[str, Any]:
    """A ready answer for the agent (Russian), with the player's numbers and, for money questions, the payments."""
    # the question Willy handed over (already in Russian) — or the player's last messages
    q, q_ru = chat.get("handoff_q") or "", chat.get("handoff_q_ru") or ""
    last = await db.support_messages.find_one({"chat_id": chat["id"], "sender_type": "user", "hidden": {"$ne": True}},
                                              {"_id": 0, "content": 1, "created_at": 1}, sort=[("created_at", -1)])
    if last and chat.get("handoff_at") and str(last.get("created_at", "")) > str(chat["handoff_at"]):
        q, q_ru = "", ""            # the player wrote more after the handover: draft for the newest message
    if not (q_ru or q):
        q = (last or {}).get("content") or ""
        if not q:
            return {"text": "", "total": 0}
        q_ru = q if is_russian(q) else (await tr(db, q, "ru", "auto", Q_TTL_MIN) or q)
    q_ru = q_ru or q
    cands, _ = await search(db, q, q_ru, k=6, agent=True)
    if not cands:
        return {"text": "", "total": 0, "q_ru": q_ru}
    i = n % len(cands)
    rows = await _answers(db, [cands[i][0]])
    ans = rows.get(cands[i][0])
    if not ans:
        return {"text": "", "total": len(cands)}
    user = await db.users.find_one({"id": chat.get("user_id")}, {"_id": 0})
    r = await render(db, ans, "ru", user, for_agent=True)
    text = r["text"]
    if chat.get("handoff_reason") == "money":
        try:
            txs = await db.transactions.find({"user_id": chat.get("user_id"),
                                              "tx_type": {"$in": ["deposit", "withdrawal", "withdraw", "instant_withdraw"]}},
                                             {"_id": 0, "tx_type": 1, "amount_ton": 1, "amount": 1, "status": 1, "created_at": 1}
                                             ).sort("created_at", -1).limit(1).to_list(1)
            if txs:
                t = txs[0]
                amt = float(t.get("amount_ton", t.get("amount", 0)) or 0)
                kind = "пополнение" if t.get("tx_type") == "deposit" else "вывод"
                text += (f"\n\nПо вашему последнему платежу ({kind} {amt:.4f} GRAM от "
                         f"{str(t.get('created_at', ''))[:16].replace('T', ' ')} UTC) статус: {t.get('status') or '—'}.")
        except Exception:
            pass
    return {"text": text, "answer_id": ans["id"], "title": ans.get("title"), "conf": round(cands[i][1], 3),
            "n": i, "total": len(cands), "q_ru": q_ru, "wiki": ans.get("wiki")}


async def return_to_willy(db, chat: Dict[str, Any], agent_name: str) -> Optional[Dict[str, Any]]:
    now = _now().isoformat()
    res = await db.support_chats.update_one({"id": chat["id"], "status": {"$in": ["new", "active"]}}, {"$set": {
        "status": "bot", "mode": "bot", "agent_id": None, "agent_tg_id": None, "agent_name": None, "claimed_at": None,
        "returned_at": now, "returned_by": agent_name, "willy_no": 0, "unread_for_agent": 0}})
    if not res.modified_count:
        return None
    sysm = {"id": str(uuid.uuid4()), "chat_id": chat["id"], "sender_type": "system", "sender_id": "system",
            "content": f"{agent_name} вернул(а) чат Willy GRAM", "system_key": "willy_returned", "system_extra": {},
            "image_url": None, "created_at": now}
    await db.support_messages.insert_one(sysm.copy())
    user = await db.users.find_one({"id": chat["user_id"]}, {"_id": 0})
    lang = chat.get("user_lang") or _lang((user or {}).get("language"))
    ws = _hooks.get("ws_manager")
    if ws:
        try:
            await ws.send_to_user(chat["user_id"], {"type": "new_message", "chat_id": chat["id"], "message": sysm})
            await ws.broadcast_to_all_agents({"type": "chat_closed", "chat_id": chat["id"]})
        except Exception:
            pass
    c = await db.support_chats.find_one({"id": chat["id"]}, {"_id": 0})
    return await _post(db, c, _bot_msg(chat["id"], _p("returned", lang), lang, {"kind": "info"}), user, False)


async def learn(db, message: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
    """«Мой ответ — в базу»: the agent's Russian answer + the player's question → a new answer «На проверке»."""
    text = (message.get("original_content") or message.get("content") or "").strip()
    if not text:
        return {"ok": False, "reason": "empty"}
    prev = await db.support_messages.find({"chat_id": message["chat_id"], "sender_type": "user",
                                           "created_at": {"$lt": message["created_at"]}}, {"_id": 0, "content": 1}
                                          ).sort("created_at", -1).limit(2).to_list(2)
    q = " ".join(m.get("content") or "" for m in reversed(prev)).strip()
    q_ru = q if is_russian(q) else (await tr(db, q, "ru", "auto", Q_TTL_MIN) or q)
    doc = {"id": str(uuid.uuid4()), "key": None, "topic": "", "title": (q_ru or text)[:90], "phrasings": [q_ru[:300]] if q_ru else [],
           "text": text[:2000], "checks": [], "wiki": None, "route": None, "handoff": False, "enabled": False,
           "status": "review", "origin": "agent", "created_by": agent_name, "source_message": message["id"],
           "created_at": _now().isoformat(), "updated_at": _now().isoformat(), "stats": {"shown": 0, "helped": 0, "not_helped": 0}}
    await db.willy_answers.insert_one(doc.copy())
    await db.support_messages.update_one({"id": message["id"]}, {"$set": {"learned": doc["id"]}})
    return {"ok": True, "id": doc["id"]}
