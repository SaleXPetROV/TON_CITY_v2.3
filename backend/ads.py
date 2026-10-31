"""Rewarded ads (Monetag) before the daily login bonus.

The player presses «Забрать» → watches N ads (default 2) → the bonus is credited.

  GET  /api/ads/config                     public: enabled, zone id, how many ads, min gap
  POST /api/ads/daily/start                a new ad show: returns its ymid = "<user id>.<nonce>"
  POST /api/ads/daily/watched              the app reports one finished ad (Monetag SDK promise resolved)
  GET  /api/ads/daily/gate                 light progress poll {required, watched, ok, pending}
  POST /api/ads/client-error               the app reports why an ad failed (Empty feed / Timeout / ...)
  GET  /api/ads/monetag/postback           Monetag server-to-server postback (?ymid=…&event=…&reward=…&secret=…)
  GET/PUT /api/admin/ads                   settings (admin)

The same ymid / postback mechanics serve the Arcade (arcade.py): its ad sessions carry purpose "arcade" and
`ref` = the reward id, and the postback stores both on the view.

ymid: Monetag only passes back what the app gave to show_XXX({ymid}). The app asks the server for a fresh
ymid before every show ("<user id>.<nonce>", only letters/digits/-/./_ as Monetag requires), so every
show is counted once: the postback is matched by ymid, retries and the extra «click» postback of the
same show do not count again.

With «verify_postback» on, only views confirmed by Monetag's postback count (the client report alone is not
trusted). Without it the client's report counts, limited by a minimum gap between two ads. With
«require_valued» on, only shows Monetag marked as `valued` (paid) count.
"""
from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

DEFAULTS = {"enabled": False, "monetag_zone_id": "", "daily_ads_required": 2, "min_gap_sec": 8,
            "verify_postback": False, "postback_secret": "", "require_valued": False,
            # the SDK tag copied from the Monetag cabinet (admin → «Данные» → «Monetag»), and what was parsed from it
            "sdk_tag": "", "sdk_src": "", "sdk_fn": "",
            # AdsGram (ads made for Telegram Mini Apps) as a second network: block id from partner.adsgram.ai;
            # order: which network is tried first — the other one is used when the first has no ad («no fill»)
            "adsgram_enabled": False, "adsgram_block_id": "", "ads_order": "monetag_first"}
ADS_ORDERS = ("monetag_first", "adsgram_first", "monetag", "adsgram")

DEFAULT_SDK_SRC = "https://libtl.com/sdk.js"
_ATTR = r"""\b{name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))"""


def _attr(tag: str, name: str) -> str:
    m = re.search(_ATTR.format(name=re.escape(name)), tag, re.I)
    return (m.group(1) or m.group(2) or m.group(3) or "").strip() if m else ""


def parse_sdk_tag(tag: str) -> Dict[str, str]:
    """`<script src='//libtl.com/sdk.js' data-zone='10012345' data-sdk='show_10012345'></script>` →
    {sdk_src, monetag_zone_id, sdk_fn}. Raises ValueError with a Russian message for the admin."""
    tag = (tag or "").strip()
    if "<script" not in tag.lower():
        raise ValueError("Вставьте тег целиком: <script src=… data-zone=… data-sdk=…></script>")
    src = _attr(tag, "src")
    if src.startswith("//"):
        src = "https:" + src
    if not re.match(r"^https://[A-Za-z0-9.-]+(/[^\s\"'<>]*)?$", src):
        raise ValueError("В теге нет адреса SDK (src=https://…)")
    zone = "".join(ch for ch in _attr(tag, "data-zone") if ch.isdigit())
    if not zone:
        raise ValueError("В теге нет номера зоны (data-zone)")
    fn = _attr(tag, "data-sdk") or f"show_{zone}"
    if not re.match(r"^[A-Za-z_$][A-Za-z0-9_$]{0,63}$", fn):
        raise ValueError("Неверное имя функции в data-sdk")
    return {"sdk_src": src, "monetag_zone_id": zone, "sdk_fn": fn}


def _now():
    return datetime.now(timezone.utc)


def _day() -> str:
    from core.timeutil import msk_today_str
    return msk_today_str()


async def get_config(db) -> Dict[str, Any]:
    d = await db.admin_settings.find_one({"type": "ads"}, {"_id": 0}) or {}
    cfg = {**DEFAULTS, **{k: v for k, v in d.items() if k in DEFAULTS}}
    if not cfg["postback_secret"]:
        cfg["postback_secret"] = secrets.token_urlsafe(16)
        await db.admin_settings.update_one({"type": "ads"}, {"$set": {"type": "ads", "postback_secret": cfg["postback_secret"]}}, upsert=True)
    return cfg


def monetag_on(cfg) -> bool:
    return bool(str(cfg.get("monetag_zone_id") or "").strip()) and cfg.get("ads_order") != "adsgram"


def adsgram_on(cfg) -> bool:
    return bool(cfg.get("adsgram_enabled")) and bool(str(cfg.get("adsgram_block_id") or "").strip()) and cfg.get("ads_order") != "monetag"


def ads_active(cfg) -> bool:
    """Ads are shown when they are switched on and at least one network (Monetag / AdsGram) is set up."""
    return bool(cfg.get("enabled")) and (monetag_on(cfg) or adsgram_on(cfg)) and int(cfg.get("daily_ads_required") or 0) > 0


async def watched_today(db, uid: str, cfg=None) -> int:
    cfg = cfg or await get_config(db)
    q: Dict[str, Any] = {"user_id": uid, "day": _day(), "purpose": "daily",
                         "source": "postback" if cfg.get("verify_postback") else "client"}
    if cfg.get("require_valued"):
        q["reward"] = {"$ne": "non_valued"}          # "valued", or unknown (zone without reward postback)
    return await db.ad_views.count_documents(q)


def _ymid_ok(v: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._-]{1,120}$", v or ""))


def _uid_from_ymid(ymid: str) -> str:
    # "<uid>.<nonce>" (current) · "<uid>:<x>" or plain "<uid>" (older builds)
    return re.split(r"[.:]", ymid or "", maxsplit=1)[0]


async def daily_gate(db, uid: str) -> Dict[str, Any]:
    """{required, watched, ok} for the daily login bonus."""
    cfg = await get_config(db)
    if not ads_active(cfg):
        return {"required": 0, "watched": 0, "ok": True}
    req = int(cfg["daily_ads_required"])
    w = await watched_today(db, uid, cfg)
    return {"required": req, "watched": min(w, req), "ok": w >= req}


ADSGRAM_PAUSE_MIN = 120


async def adsgram_paused_until(db) -> str:
    """AdsGram answered «Block … is not active» (the block is on moderation / switched off) — until this time players
    are not sent to AdsGram at all: they get Monetag straight away and never see AdsGram's error window."""
    d = await db.admin_settings.find_one({"type": "ads_runtime"}, {"_id": 0, "adsgram_paused_until": 1}) or {}
    until = d.get("adsgram_paused_until") or ""
    return until if until and until > _now().isoformat() else ""


def create_ads_router(db, get_current_user, get_current_admin) -> APIRouter:
    r = APIRouter()

    @r.get("/api/ads/config")
    async def config():
        cfg = await get_config(db)
        zone = str(cfg["monetag_zone_id"] or "")
        return {"enabled": ads_active(cfg), "zone_id": zone, "daily_ads_required": int(cfg["daily_ads_required"]),
                "sdk_src": cfg.get("sdk_src") or DEFAULT_SDK_SRC, "sdk_fn": cfg.get("sdk_fn") or (f"show_{zone}" if zone else ""),
                "min_gap_sec": int(cfg["min_gap_sec"]), "verify_postback": bool(cfg["verify_postback"]),
                "monetag": monetag_on(cfg),
                "adsgram": {"enabled": adsgram_on(cfg) and not await adsgram_paused_until(db),
                            "block_id": str(cfg.get("adsgram_block_id") or "")},
                "order": cfg.get("ads_order") or "monetag_first"}

    @r.post("/api/ads/adsgram-inactive")
    async def adsgram_inactive(body: Dict[str, Any] = None, current_user=Depends(get_current_user)):
        """The app saw AdsGram answer «Block … is not active»: AdsGram is skipped for everybody for 2 hours
        (the next players get Monetag at once instead of AdsGram's error window). Only that exact answer counts."""
        desc = str((body or {}).get("description") or "")
        if not re.search(r"not active|moderation", desc, re.I):
            return {"ok": False}
        until = (_now() + timedelta(minutes=ADSGRAM_PAUSE_MIN)).isoformat()
        await db.admin_settings.update_one({"type": "ads_runtime"}, {"$set": {
            "type": "ads_runtime", "adsgram_paused_until": until, "adsgram_paused_reason": desc[:200],
            "adsgram_paused_at": _now().isoformat()}}, upsert=True)
        return {"ok": True, "paused_until": until}

    async def _gate_with_pending(uid: str, cfg) -> Dict[str, Any]:
        g = await daily_gate(db, uid)
        if cfg.get("verify_postback") and not g["ok"]:
            # shows the app reported today that Monetag has not confirmed yet
            client = await db.ad_views.distinct("ymid", {"user_id": uid, "day": _day(), "purpose": "daily", "source": "client"})
            conf = await db.ad_views.distinct("ymid", {"user_id": uid, "day": _day(), "purpose": "daily", "source": "postback"})
            g["pending"] = len([y for y in client if y and y not in set(conf)])
        else:
            g["pending"] = 0
        return g

    @r.post("/api/ads/daily/start")
    async def start(current_user=Depends(get_current_user)):
        """A fresh ymid for the next show (the app passes it to show_XXX and Monetag returns it in the postback)."""
        ymid = f"{current_user.id}.{secrets.token_hex(5)}"
        await db.ad_sessions.insert_one({"ymid": ymid, "user_id": current_user.id, "day": _day(), "purpose": "daily",
                                         "created_at": _now().isoformat()})
        return {"ymid": ymid, "request_var": "daily_bonus"}

    @r.get("/api/ads/daily/gate")
    async def gate(current_user=Depends(get_current_user)):
        cfg = await get_config(db)
        if not ads_active(cfg):
            return {"required": 0, "watched": 0, "ok": True, "pending": 0}
        return await _gate_with_pending(current_user.id, cfg)

    @r.post("/api/ads/daily/watched")
    async def watched(body: Dict[str, Any] = None, current_user=Depends(get_current_user)):
        body = body or {}
        cfg = await get_config(db)
        if not ads_active(cfg):
            return {"required": 0, "watched": 0, "ok": True, "pending": 0}
        uid = current_user.id
        ymid = str(body.get("ymid") or "")
        if not _ymid_ok(ymid) or _uid_from_ymid(ymid) != uid:
            ymid = f"{uid}.c{secrets.token_hex(4)}"         # an old app build without /start
        reward = str(body.get("reward_event_type") or "").lower()
        reward = reward if reward in ("valued", "non_valued") else ""
        if await db.ad_views.find_one({"ymid": ymid, "source": "client"}, {"_id": 0, "id": 1}):
            return await _gate_with_pending(uid, cfg)       # the same show reported twice
        req = int(cfg["daily_ads_required"])
        if await db.ad_views.count_documents({"user_id": uid, "day": _day(), "purpose": "daily", "source": "client"}) >= req * 3:
            return await _gate_with_pending(uid, cfg)
        last = await db.ad_views.find({"user_id": uid, "purpose": "daily", "source": "client"}, {"_id": 0, "created_at": 1}) \
            .sort("created_at", -1).limit(1).to_list(1)
        if last:
            gap = (_now() - datetime.fromisoformat(last[0]["created_at"])).total_seconds()
            if gap < int(cfg["min_gap_sec"]):
                raise HTTPException(status_code=429, detail="ad_too_fast")
        await db.ad_views.insert_one({"id": str(uuid.uuid4()), "user_id": uid, "day": _day(), "purpose": "daily",
                                      "source": "client", "ymid": ymid, "reward": reward, "created_at": _now().isoformat()})
        return await _gate_with_pending(uid, cfg)

    @r.post("/api/ads/client-error")
    async def client_error(body: Dict[str, Any] = None, current_user=Depends(get_current_user)):
        """Why an ad failed on the player's device — shown to the admin (Empty feed, Timeout, sdk, ...)."""
        msg = re.sub(r"[^\w .:/-]", "", str((body or {}).get("message") or "unknown"))[:80] or "unknown"
        await db.ad_errors.insert_one({"user_id": current_user.id, "day": _day(), "message": msg,
                                       "created_at": _now().isoformat()})
        return {"ok": True}

    async def handle_postback(q, ip: str) -> Dict[str, Any]:
        """Monetag's postback (also used by the admin's «Проверка рекламы»): every request is logged together with
        the server's answer, so the admin sees exactly what was decided for each event."""
        cfg = await get_config(db)
        if q.get("secret") != cfg["postback_secret"]:
            raise HTTPException(status_code=403, detail="bad secret")
        ymid = (q.get("ymid") or "").strip()
        event = (q.get("event") or q.get("event_type") or "impression").lower()
        reward = (q.get("reward") or q.get("reward_event_type") or "").lower()
        reward = reward if reward in ("valued", "non_valued") else ""
        log_id = str(uuid.uuid4())
        # every postback is logged (the admin sees what Monetag sends), answered with 200 so Monetag does not retry
        await db.ad_postbacks.insert_one({"id": log_id, "ymid": ymid[:140], "event": event[:20], "reward": reward, "day": _day(),
                                          "ip": ip, "test": bool(q.get("test")), "created_at": _now().isoformat()})
        res = await _postback_decide(ymid, event, reward, cfg)
        await db.ad_postbacks.update_one({"id": log_id}, {"$set": {"result": res}})
        return res

    async def _postback_decide(ymid: str, event: str, reward: str, cfg) -> Dict[str, Any]:
        if not ymid or not _ymid_ok(ymid):
            return {"ok": False, "reason": "no_ymid"}
        sess = await db.ad_sessions.find_one({"ymid": ymid}, {"_id": 0, "user_id": 1, "day": 1, "purpose": 1, "ref": 1})
        uid = (sess or {}).get("user_id") or _uid_from_ymid(ymid)
        if not uid or not await db.users.find_one({"id": uid}, {"_id": 0, "id": 1}):
            return {"ok": False, "reason": "unknown_user"}
        if event in ("click",):                      # the same show: a click is not one more view
            await db.ad_views.update_one({"ymid": ymid, "source": "postback"}, {"$set": {"clicked": True}})
            return {"ok": True, "counted": False, "reason": "click_same_show"}
        if event not in ("impression", "valued", "complete", "reward"):
            return {"ok": False, "reason": "event"}
        if await db.ad_views.find_one({"ymid": ymid, "source": "postback"}, {"_id": 0, "id": 1}):
            if reward:
                await db.ad_views.update_one({"ymid": ymid, "source": "postback"}, {"$set": {"reward": reward}})
            return {"ok": True, "counted": False, "reason": "already_counted"}   # a retry of a postback already counted
        await db.ad_views.insert_one({"id": str(uuid.uuid4()), "user_id": uid, "day": (sess or {}).get("day") or _day(),
                                      "purpose": (sess or {}).get("purpose") or "daily", "source": "postback", "event": event,
                                      "ymid": ymid, "reward": reward, "created_at": _now().isoformat(),
                                      **({"ref": sess["ref"]} if (sess or {}).get("ref") else {})})
        out = {"ok": True, "counted": True, "purpose": (sess or {}).get("purpose") or "daily"}
        if cfg.get("require_valued") and reward == "non_valued":
            out["note"] = "non_valued: with «только оплачиваемые» on, this view does not count for the bonus"
        return out

    @r.get("/api/ads/monetag/postback")
    async def postback(request: Request):
        """Monetag postback URL (set in the Monetag dashboard):
        https://<domain>/api/ads/monetag/postback?ymid={ymid}&event={event_type}&reward={reward_event_type}&secret=<postback_secret>"""
        q = dict(request.query_params)
        q.pop("test", None)
        return await handle_postback(q, request.client.host if request.client else "")

    async def adsgram_reward(telegram_id: str, ip: str, test_uid: str = "", only_ymid: str = "") -> Dict[str, Any]:
        """AdsGram's «Reward URL» (GET, [userId] = the player's Telegram id) — the server-side confirmation of a
        watched rewarded ad. AdsGram sends no ymid, so the player's latest ad show (started within 10 minutes, not
        confirmed yet) is the one confirmed. Logged like Monetag's postbacks, with the server's answer."""
        log_id = str(uuid.uuid4())
        await db.ad_postbacks.insert_one({"id": log_id, "network": "adsgram", "ymid": "", "event": "adsgram_reward",
                                          "telegram_id": str(telegram_id)[:32], "day": _day(), "ip": ip, "test": bool(test_uid),
                                          "created_at": _now().isoformat()})
        res: Dict[str, Any]
        uid = test_uid
        if not uid:
            tid = str(telegram_id or "").strip()
            q = [{"telegram_id": tid}]
            if tid.isdigit():
                q.append({"telegram_id": int(tid)})
            u = await db.users.find_one({"$or": q}, {"_id": 0, "id": 1}) if tid else None
            uid = (u or {}).get("id") or ""
        if not uid:
            res = {"ok": False, "reason": "unknown_user"}
        else:
            since = (_now() - timedelta(minutes=10)).isoformat()
            sq: Dict[str, Any] = {"user_id": uid, "created_at": {"$gte": since}}
            if only_ymid:
                sq["ymid"] = only_ymid
            sessions = await db.ad_sessions.find(sq, {"_id": 0}) \
                .sort("created_at", -1).limit(10).to_list(10)
            sess = None
            for x in sessions:
                if not await db.ad_views.find_one({"ymid": x["ymid"], "source": "postback"}, {"_id": 0, "id": 1}):
                    sess = x
                    break
            if not sess:
                res = {"ok": False, "reason": "no_open_show"}
            else:
                await db.ad_views.insert_one({"id": str(uuid.uuid4()), "user_id": uid, "day": sess.get("day") or _day(),
                                              "purpose": sess.get("purpose") or "daily", "source": "postback", "event": "impression",
                                              "network": "adsgram", "ymid": sess["ymid"], "reward": "valued",
                                              "created_at": _now().isoformat(), **({"ref": sess["ref"]} if sess.get("ref") else {})})
                res = {"ok": True, "counted": True, "purpose": sess.get("purpose") or "daily", "ymid": sess["ymid"]}
        await db.ad_postbacks.update_one({"id": log_id}, {"$set": {"result": res, "ymid": res.get("ymid", "")}})
        return res

    @r.get("/api/ads/adsgram/reward")
    async def adsgram_reward_url(request: Request):
        """AdsGram «Reward URL»: https://<domain>/api/ads/adsgram/reward?userid=[userId]&secret=<postback_secret>"""
        cfg = await get_config(db)
        q = request.query_params
        if q.get("secret") != cfg["postback_secret"]:
            raise HTTPException(status_code=403, detail="bad secret")
        return await adsgram_reward(q.get("userid") or q.get("userId") or q.get("user_id") or "",
                                    request.client.host if request.client else "")

    @r.post("/api/admin/ads/test/adsgram-reward")
    async def test_adsgram_reward(body: Dict[str, Any] = None, admin=Depends(get_current_admin)):
        """Simulates AdsGram's reward request for the admin's test show — the answer is what the real endpoint returns."""
        body = body or {}
        ymid = str(body.get("ymid") or "")
        if not await db.ad_sessions.find_one({"ymid": ymid, "purpose": "admin_test", "user_id": admin.id}, {"_id": 0, "ymid": 1}):
            raise HTTPException(status_code=400, detail="Сначала нажмите «Новый тест»")
        return {"request": {"userid": "<Telegram id администратора>", "test": True},
                "response": await adsgram_reward("", "admin-test", test_uid=admin.id, only_ymid=ymid)}

    # ───────── admin «Проверка рекламы»: a test show with every step and the server's answers ─────────
    @r.post("/api/admin/ads/test/start")
    async def test_start(request: Request, admin=Depends(get_current_admin)):
        ymid = f"{admin.id}.t{secrets.token_hex(5)}"
        await db.ad_sessions.insert_one({"ymid": ymid, "user_id": admin.id, "day": _day(), "purpose": "admin_test",
                                         "created_at": _now().isoformat()})
        cfg = await get_config(db)
        zone = str(cfg["monetag_zone_id"] or "")
        h = request.headers
        country = h.get("cf-ipcountry") or h.get("x-country-code") or h.get("x-geo-country") or ""
        return {"ymid": ymid, "request_var": "admin_test", "country": country.upper()[:4],
                "adsgram": {"enabled": adsgram_on(cfg), "block_id": str(cfg.get("adsgram_block_id") or "")},
                "order": cfg.get("ads_order") or "monetag_first",
                "sdk": {"enabled": ads_active(cfg), "zone_id": zone, "sdk_src": cfg.get("sdk_src") or DEFAULT_SDK_SRC,
                        "sdk_fn": cfg.get("sdk_fn") or (f"show_{zone}" if zone else "")}}

    @r.post("/api/admin/ads/test/report")
    async def test_report(body: Dict[str, Any] = None, admin=Depends(get_current_admin)):
        """What the server does with the app's report «реклама досмотрена» for a player (nothing is counted here)."""
        body = body or {}
        cfg = await get_config(db)
        ymid = str(body.get("ymid") or "")
        rt = str((body.get("sdk_result") or {}).get("reward_event_type") or "").lower()
        await db.ad_test_log.insert_one({"ymid": ymid[:140], "admin_id": admin.id, "kind": "client_report",
                                         "sdk_result": body.get("sdk_result"), "error": str(body.get("error") or "")[:200],
                                         "created_at": _now().isoformat()})
        if body.get("error"):
            return {"ok": False, "would_count": False,
                    "explain": f"Показ не состоялся ({body.get('error')}): игроку засчитано не будет. Приложение отправит ошибку в «Ошибки показа»."}
        if cfg.get("verify_postback"):
            explain = ("Включено «Засчитывать только подтверждённые»: отчёт приложения только отмечает показ как «ждёт подтверждения». "
                       "Засчитан он будет, когда придёт postback Monetag с этим ymid (смотрите ниже).")
            would = False
        else:
            explain = "Проверка через postback выключена: игроку показ засчитался бы сразу по отчёту приложения (с учётом минимальной паузы между рекламами)."
            would = True
        if cfg.get("require_valued") and rt == "non_valued":
            explain += " Monetag пометил показ как non_valued (неоплачиваемый) — при «только оплачиваемые» он не засчитается."
            would = False
        return {"ok": True, "would_count": would, "reward_event_type": rt or None, "verify_postback": bool(cfg.get("verify_postback")),
                "require_valued": bool(cfg.get("require_valued")), "explain": explain}

    @r.post("/api/admin/ads/test/postback")
    async def test_postback(body: Dict[str, Any] = None, admin=Depends(get_current_admin)):
        """Simulates Monetag's postback for the test ymid — the answer is EXACTLY what the real endpoint returns."""
        body = body or {}
        cfg = await get_config(db)
        ymid = str(body.get("ymid") or "")
        sess = await db.ad_sessions.find_one({"ymid": ymid, "purpose": "admin_test"}, {"_id": 0, "ymid": 1})
        if not sess:
            raise HTTPException(status_code=400, detail="Сначала нажмите «Новый тест»")
        q = {"ymid": ymid, "event": str(body.get("event") or "impression"), "reward": str(body.get("reward") or ""),
             "secret": cfg["postback_secret"], "test": True}
        return {"request": {k: v for k, v in q.items() if k != "secret"}, "response": await handle_postback(q, "admin-test")}

    @r.get("/api/admin/ads/test/{ymid}")
    async def test_status(ymid: str, admin=Depends(get_current_admin)):
        """Everything the server knows about the test show: postbacks that came (real or simulated) and its answers."""
        pbs = await db.ad_postbacks.find({"ymid": ymid}, {"_id": 0, "ip": 0}).sort("created_at", 1).to_list(50)
        views = await db.ad_views.find({"ymid": ymid}, {"_id": 0}).sort("created_at", 1).to_list(20)
        return {"ymid": ymid, "postbacks": pbs, "views": views}

    @r.get("/api/admin/ads")
    async def a_get(_=Depends(get_current_admin)):
        cfg = await get_config(db)
        today = _day()
        errs: Dict[str, int] = {}
        for e in await db.ad_errors.find({"day": today}, {"_id": 0, "message": 1}).to_list(5000):
            errs[e.get("message") or "unknown"] = errs.get(e.get("message") or "unknown", 0) + 1
        last_pb = await db.ad_postbacks.find({}, {"_id": 0}).sort("created_at", -1).limit(1).to_list(1)
        return {**cfg,
                "views_today": await db.ad_views.count_documents({"day": today, "source": "client"}),
                "postbacks_today": await db.ad_views.count_documents({"day": today, "source": "postback"}),
                "postbacks_raw_today": await db.ad_postbacks.count_documents({"day": today}),
                "players_today": len(await db.ad_views.distinct("user_id", {"day": today})),
                "errors_today": errs, "last_postback": last_pb[0] if last_pb else None,
                "adsgram_paused_until": await adsgram_paused_until(db),
                "adsgram_paused_reason": ((await db.admin_settings.find_one({"type": "ads_runtime"}, {"_id": 0}) or {})
                                          .get("adsgram_paused_reason") or "")}

    @r.post("/api/admin/ads/adsgram-resume")
    async def a_adsgram_resume(_=Depends(get_current_admin)):
        """The admin: «блок AdsGram уже активен» — players get AdsGram again right away."""
        await db.admin_settings.update_one({"type": "ads_runtime"}, {"$set": {"type": "ads_runtime", "adsgram_paused_until": ""}},
                                           upsert=True)
        return {"ok": True}

    @r.put("/api/admin/ads")
    async def a_put(body: Dict[str, Any], _=Depends(get_current_admin)):
        upd = {k: v for k, v in body.items() if k in DEFAULTS and k not in ("sdk_src", "sdk_fn", "postback_secret")}
        if "sdk_tag" in upd:
            tag = str(upd["sdk_tag"] or "").strip()
            if tag:
                try:
                    upd.update(parse_sdk_tag(tag))
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
                upd["sdk_tag"] = tag[:2000]
            else:
                upd.update({"sdk_tag": "", "sdk_src": "", "sdk_fn": ""})
        if "daily_ads_required" in upd:
            upd["daily_ads_required"] = max(0, min(5, int(upd["daily_ads_required"] or 0)))
        if "min_gap_sec" in upd:
            upd["min_gap_sec"] = max(0, min(120, int(upd["min_gap_sec"] or 0)))
        if "monetag_zone_id" in upd:
            upd["monetag_zone_id"] = "".join(ch for ch in str(upd["monetag_zone_id"]) if ch.isdigit())
        if "adsgram_block_id" in upd:
            upd["adsgram_block_id"] = "".join(ch for ch in str(upd["adsgram_block_id"] or "") if ch.isalnum() or ch == "-")[:40]
        if "ads_order" in upd and upd["ads_order"] not in ADS_ORDERS:
            upd["ads_order"] = "monetag_first"
        for k in ("enabled", "verify_postback", "require_valued", "adsgram_enabled"):
            if k in upd:
                upd[k] = bool(upd[k])
        await db.admin_settings.update_one({"type": "ads"}, {"$set": {"type": "ads", **upd}}, upsert=True)
        return await a_get()

    return r
