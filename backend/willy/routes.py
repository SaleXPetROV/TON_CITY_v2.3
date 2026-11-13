"""Admin «Поддержка → Willy GRAM» (Russian): the answer base, preview, test, gaps, stats, rules.

  GET    /api/admin/willy/answers?q=&topic=&status=&page=   list (status: all|ok|off|review)
  GET    /api/admin/willy/answers/{id}
  POST   /api/admin/willy/answers                            create
  PUT    /api/admin/willy/answers/{id}                       save (origin → admin: a newer seed never overwrites it)
  DELETE /api/admin/willy/answers/{id}
  POST   /api/admin/willy/preview      {text|answer_id, lang, user_id?}   «как увидит игрок»
  POST   /api/admin/willy/test         {q, lang}                          what Willy would do with a question
  GET    /api/admin/willy/stats?days=7
  GET    /api/admin/willy/gaps?status=open
  POST   /api/admin/willy/gaps/{id}    {action: attach|dismiss|reopen, answer_id?}
  GET    /api/admin/willy/log?limit=
  GET/PUT /api/admin/willy/settings
  POST   /api/admin/willy/reindex
  GET    /api/admin/willy/vars
"""
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import core as W
from . import index as _index
from .rules import REASONS, check as _rules
from .text import is_russian


class AnswerIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    topic: str = ""
    phrasings: List[str] = []
    text: str = Field(..., min_length=1, max_length=3000)
    wiki: Optional[str] = None
    route: Optional[str] = None
    checks: List[str] = []
    handoff: bool = False
    enabled: bool = True
    show: bool = True
    agent_only: bool = False


class PreviewIn(BaseModel):
    text: Optional[str] = None
    answer_id: Optional[str] = None
    lang: str = "ru"
    user_id: Optional[str] = None


class TestIn(BaseModel):
    q: str = Field(..., min_length=1, max_length=1000)
    lang: str = "ru"


class GapIn(BaseModel):
    action: str
    answer_id: Optional[str] = None


def _clean_phr(xs: List[str]) -> List[str]:
    out, seen = [], set()
    for x in xs or []:
        x = re.sub(r"\s+", " ", str(x)).strip()[:300]
        if x and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return out[:200]


def create_willy_admin_router(db, get_admin):
    r = APIRouter(prefix="/api/admin/willy", tags=["Willy GRAM admin"])

    @r.get("/answers")
    async def list_answers(q: str = "", topic: str = "", status: str = "all", page: int = 1, admin=Depends(get_admin)):
        f: Dict[str, Any] = {}
        if topic:
            f["topic"] = topic
        if status == "ok":
            f["enabled"] = True
        elif status == "off":
            f["enabled"] = False
            f["status"] = {"$ne": "review"}
        elif status == "review":
            f["status"] = "review"
        rows = await db.willy_answers.find(f, {"_id": 0}).sort([("topic", 1), ("title", 1)]).to_list(20000)
        if q.strip():
            ql = q.strip().lower()
            rows = [a for a in rows if ql in (a.get("title") or "").lower() or ql in (a.get("text") or "").lower()
                    or any(ql in p.lower() for p in a.get("phrasings") or [])]
        total = len(rows)
        per = 50
        page = max(1, page)
        items = rows[(page - 1) * per: page * per]
        counts = {
            "all": await db.willy_answers.count_documents({}),
            "ok": await db.willy_answers.count_documents({"enabled": True}),
            "review": await db.willy_answers.count_documents({"status": "review"}),
        }
        phr = 0
        async for a in db.willy_answers.find({"enabled": True}, {"_id": 0, "phrasings": 1}):
            phr += len(a.get("phrasings") or [])
        counts["phrasings"] = phr
        return {"items": items, "total": total, "page": page, "pages": max(1, (total + per - 1) // per), "counts": counts}

    @r.get("/answers/{aid}")
    async def get_answer(aid: str, admin=Depends(get_admin)):
        a = await db.willy_answers.find_one({"id": aid}, {"_id": 0})
        if not a:
            raise HTTPException(404, "Ответ не найден")
        return a

    @r.post("/answers")
    async def create_answer(data: AnswerIn, admin=Depends(get_admin)):
        now = datetime.now(timezone.utc).isoformat()
        doc = {**data.dict(), "phrasings": _clean_phr(data.phrasings), "id": str(uuid.uuid4()), "key": None,
               "origin": "admin", "status": "ok", "created_at": now, "updated_at": now,
               "stats": {"shown": 0, "helped": 0, "not_helped": 0}}
        await db.willy_answers.insert_one(doc.copy())
        await _index.bump(db)
        await _index.service_upsert([{"id": doc["id"], "title": doc["title"], "phrasings": doc["phrasings"]}])
        doc.pop("_id", None)
        return doc

    @r.put("/answers/{aid}")
    async def save_answer(aid: str, data: AnswerIn, admin=Depends(get_admin)):
        cur = await db.willy_answers.find_one({"id": aid}, {"_id": 0})
        if not cur:
            raise HTTPException(404, "Ответ не найден")
        upd = {**data.dict(), "phrasings": _clean_phr(data.phrasings), "origin": "admin",
               "status": "ok" if data.enabled else ("review" if cur.get("status") == "review" else "ok"),
               "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.willy_answers.update_one({"id": aid}, {"$set": upd, "$unset": {"suggested": ""}})
        await db.willy_answer_versions.insert_one({"answer_id": aid, "at": upd["updated_at"],
                                                   "by": getattr(admin, "email", None) or "admin",
                                                   "prev": {k: cur.get(k) for k in ("title", "text", "phrasings", "enabled")}})
        await _index.bump(db)
        await _index.service_upsert([{"id": aid, "title": upd["title"], "phrasings": upd["phrasings"]}])
        return await db.willy_answers.find_one({"id": aid}, {"_id": 0})

    @r.delete("/answers/{aid}")
    async def delete_answer(aid: str, admin=Depends(get_admin)):
        cur = await db.willy_answers.find_one({"id": aid}, {"_id": 0, "origin": 1, "key": 1})
        if not cur:
            raise HTTPException(404, "Ответ не найден")
        if cur.get("origin") == "seed" and cur.get("key"):
            # a seed answer would come back with the next seed: switch it off instead
            await db.willy_answers.update_one({"id": aid}, {"$set": {"enabled": False, "origin": "admin"}})
        else:
            await db.willy_answers.delete_one({"id": aid})
        await _index.bump(db)
        return {"ok": True}

    @r.post("/preview")
    async def preview(data: PreviewIn, admin=Depends(get_admin)):
        lang = W._lang(data.lang)
        if data.answer_id:
            ans = await db.willy_answers.find_one({"id": data.answer_id}, {"_id": 0})
            if not ans:
                raise HTTPException(404, "Ответ не найден")
            if data.text:
                ans = {**ans, "text": data.text}
        else:
            ans = {"id": "preview", "text": data.text or "", "wiki": None, "checks": []}
        user = await db.users.find_one({"id": data.user_id}, {"_id": 0}) if data.user_id else None
        out = await W.render(db, ans, lang, user)
        unknown = sorted(set(re.findall(r"\{(\w+)\}", out["text"])))
        return {**out, "lang": lang, "unknown_vars": unknown}

    @r.post("/test")
    async def test(data: TestIn, admin=Depends(get_admin)):
        s = await W.settings(db)
        q_ru = data.q if is_russian(data.q) else (await W.tr(db, data.q, "ru", "auto", W.Q_TTL_MIN) or data.q)
        reason = _rules([data.q, q_ru], s)
        cands, eng = await W.search(db, data.q, q_ru, k=5)
        rows = await W._answers(db, [c[0] for c in cands])
        top = [{"id": a, "title": (rows.get(a) or {}).get("title"), "conf": round(sc, 3)} for a, sc in cands]
        if reason:
            decision = f"Сразу к человеку: {REASONS.get(reason, reason)}"
        elif cands and cands[0][1] >= s["high"]:
            decision = "Ответ"
        elif cands and cands[0][1] >= s["low"]:
            decision = "«О чём вопрос?» — кнопки"
        else:
            decision = "Нет в базе → человек" if s.get("handoff_on_low", True) else "«О чём вопрос?»"
        return {"q_ru": q_ru, "rule": reason, "engine": eng, "top": top, "decision": decision,
                "high": s["high"], "low": s["low"]}

    @r.get("/stats")
    async def stats(days: int = 7, admin=Depends(get_admin)):
        since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))).isoformat()
        rows = await db.willy_log.find({"at": {"$gte": since}}, {"_id": 0, "outcome": 1, "reason": 1, "answer_id": 1,
                                                                   "answer_title": 1, "helped": 1, "conf": 1, "lang": 1}).to_list(200000)
        by: Dict[str, int] = {}
        reasons: Dict[str, int] = {}
        top: Dict[str, Dict[str, Any]] = {}
        langs: Dict[str, int] = {}
        helped = nothelped = 0
        for x in rows:
            o = x.get("outcome")
            by[o] = by.get(o, 0) + 1
            if o in ("answer", "clarify", "handoff") and x.get("lang"):
                langs[x["lang"]] = langs.get(x["lang"], 0) + 1
            if o == "handoff":
                rr = x.get("reason") or "?"
                reasons[rr] = reasons.get(rr, 0) + 1
            if o == "answer" and x.get("answer_id"):
                t = top.setdefault(x["answer_id"], {"id": x["answer_id"], "title": x.get("answer_title"), "n": 0})
                t["n"] += 1
            if o == "feedback":
                if x.get("helped"):
                    helped += 1
                else:
                    nothelped += 1
        asked = by.get("answer", 0) + by.get("clarify", 0) + by.get("handoff", 0)
        chats = await db.support_chats.count_documents({"created_at": {"$gte": since}})
        solo = await db.support_chats.count_documents({"created_at": {"$gte": since}, "handoff_at": {"$exists": False},
                                                       "mode": {"$ne": "human"}, "status": {"$in": ["bot", "archived"]}})
        return {
            "days": days, "questions": asked, "answers": by.get("answer", 0), "clarify": by.get("clarify", 0),
            "handoff": by.get("handoff", 0), "seed_hidden": by.get("seed", 0),
            "helped": helped, "not_helped": nothelped, "chats": chats, "chats_without_human": solo,
            "reasons": [{"reason": k, "label": REASONS.get(k, k), "n": v} for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])],
            "top": sorted(top.values(), key=lambda t: -t["n"])[:15],
            "langs": langs,
            "open_gaps": await db.willy_gaps.count_documents({"status": "open"}),
            "service": await _index.health(),
        }

    @r.get("/gaps")
    async def gaps(status: str = "open", admin=Depends(get_admin)):
        rows = await db.willy_gaps.find({"status": status} if status != "all" else {}, {"_id": 0}
                                        ).sort([("count", -1), ("last_at", -1)]).to_list(500)
        ids = [g["best"]["answer_id"] for g in rows if g.get("best")]
        ans = await W._answers(db, ids) if ids else {}
        for g in rows:
            if g.get("best"):
                g["best"]["title"] = (ans.get(g["best"]["answer_id"]) or {}).get("title")
        return {"items": rows}

    @r.post("/gaps/{gid}")
    async def gap_action(gid: str, data: GapIn, admin=Depends(get_admin)):
        g = await db.willy_gaps.find_one({"id": gid}, {"_id": 0})
        if not g:
            raise HTTPException(404, "Не найдено")
        if data.action == "attach":
            if not data.answer_id:
                raise HTTPException(400, "Выберите ответ")
            res = await db.willy_answers.update_one({"id": data.answer_id}, {"$addToSet": {"phrasings": g["q_ru"][:300]},
                                                                             "$set": {"origin": "admin"}})
            if not res.matched_count:
                raise HTTPException(404, "Ответ не найден")
            await db.willy_gaps.update_one({"id": gid}, {"$set": {"status": "resolved", "answer_id": data.answer_id}})
            await _index.bump(db)
        elif data.action == "dismiss":
            await db.willy_gaps.update_one({"id": gid}, {"$set": {"status": "dismissed"}})
        elif data.action == "reopen":
            await db.willy_gaps.update_one({"id": gid}, {"$set": {"status": "open"}})
        else:
            raise HTTPException(400, "Неизвестное действие")
        return {"ok": True}

    @r.get("/log")
    async def log(limit: int = 100, admin=Depends(get_admin)):
        rows = await db.willy_log.find({}, {"_id": 0}).sort("at", -1).limit(max(1, min(limit, 500))).to_list(500)
        return {"items": rows}

    @r.get("/settings")
    async def get_settings(admin=Depends(get_admin)):
        s = await W.settings(db)
        return {**s, "reasons": REASONS}

    @r.put("/settings")
    async def put_settings(data: Dict[str, Any], admin=Depends(get_admin)):
        allowed = {"enabled", "high", "low", "sem_high", "sem_low", "handoff_on_low", "rules"}
        patch = {k: v for k, v in (data or {}).items() if k in allowed}
        for k in ("high", "low", "sem_high", "sem_low"):
            if k in patch:
                patch[k] = max(0.05, min(0.99, float(patch[k])))
        if "rules" in patch:
            rules = {}
            for k, v in (patch["rules"] or {}).items():
                if k in W.DEFAULT_SETTINGS["rules"]:
                    rules[k] = {"enabled": bool((v or {}).get("enabled", True)),
                                "words": [str(w).strip()[:60] for w in (v or {}).get("words") or [] if str(w).strip()][:50]}
                    if k == "money":
                        rules[k]["strict"] = bool((v or {}).get("strict"))
            patch["rules"] = rules
        await db.willy_settings.update_one({"_id": "main"}, {"$set": patch}, upsert=True)
        return await W.settings(db)

    @r.post("/reindex")
    async def reindex(admin=Depends(get_admin)):
        idx = await _index.get(db, force=True)
        ok = await _index.service_rebuild(db)
        return {"keyword_phrasings": idx.size, "answers": len(idx.answers), "service": ok}

    @r.get("/vars")
    async def vars_(admin=Depends(get_admin)):
        from .player import PLAYER_VARS
        from routes.wiki import wiki_vars
        from wiki_content.ui import CHECKS
        from routes.wiki import fill as wfill
        g = await wiki_vars(db)
        arts = []
        async for d in db.wiki_articles.find({"published": {"$ne": False}}, {"_id": 0, "slug": 1, "icon": 1, "i18n": 1, "section": 1, "order": 1}).sort("order", 1):
            arts.append({"slug": d["slug"], "title": wfill(((d.get("i18n") or {}).get("ru") or {}).get("t") or d["slug"], g),
                         "icon": d.get("icon"), "section": d.get("section")})
        return {"player": PLAYER_VARS, "game": {k: str(v) for k, v in g.items()},
                "checks": {cid: (x.get("ru") or {}).get("t", cid) for cid, x in CHECKS.items()},
                "articles": arts, "reasons": REASONS}

    return r


async def nightly(db) -> Dict[str, Any]:
    """04:00 МСК, only when the base changed since the last night: rebuild the meaning index; trim the log."""
    m = await db.willy_meta.find_one({"_id": "rev"}) or {}
    out: Dict[str, Any] = {"dirty": bool(m.get("dirty"))}
    if m.get("dirty"):
        out["service"] = await _index.service_rebuild(db)
        await db.willy_meta.update_one({"_id": "rev"}, {"$set": {"dirty": False, "night_at": datetime.now(timezone.utc).isoformat()}})
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    try:
        await db.willy_log.delete_many({"at": {"$lt": cutoff}})
    except Exception:
        pass
    return out
