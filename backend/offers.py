"""«Рекламные задания» on the Tasks page — offers that are ALWAYS there, even when every own task (subscribe to a
channel, follow, visit…) is done. Paid by the ad networks the project already uses:

  • AdsGram «Task» — an advertiser's task (subscribe to a channel, open a bot / Mini App…) shown by AdsGram's
    <adsgram-task> component. AdsGram calls our Reward URL when the player has done it:
        GET /api/offers/adsgram-task/reward?userid=[userId]&secret=<postback secret of «Реклама»>
    The app also reports the component's «reward» event (POST /api/offers/adsgram-task/done). By default only
    AdsGram's server call credits the reward; with «trust_client» on, the app's report credits it at once (and the
    server call that follows only confirms it — never a second reward).
  • «Посмотри рекламу» — rewarded ad views (Monetag / AdsGram rewarded, in the order set in «Реклама»), N per day.
    With «Засчитывать только подтверждённые» (ads.verify_postback) the reward comes with the network's postback
    (ads.py calls on_confirmed_view), otherwise with the app's report (min gap between two views).

A reward goes to the BONUS balance (credit_task_reward_bonus). Clicks on ads are never rewarded.
Every reward is one document in `offer_rewards` (one per show / task), the daily limits count them.

  GET  /api/offers                         what the player can do now + today's progress
  POST /api/offers/ad/start                a ymid for the next rewarded ad (ad_sessions, purpose "offer")
  POST /api/offers/ad/watched              the app: the ad was watched {ymid, reward_event_type}
  POST /api/offers/adsgram-task/done       the app: <adsgram-task> fired «reward»
  GET  /api/offers/adsgram-task/reward     AdsGram's Reward URL for the Task block
  GET/PUT /api/admin/offers                settings + today's numbers (admin)
"""
from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

DEFAULTS = {
    "adsgram_task_enabled": False, "adsgram_task_block_id": "", "adsgram_task_reward": 50, "adsgram_task_daily_cap": 10,
    "adsgram_task_trust_client": False,
    "ad_offers_enabled": False, "ad_offer_reward": 20, "ad_offer_daily_cap": 5, "ad_offer_gap_sec": 30,
}
PAIR_MIN = 30          # the app's report and AdsGram's server call within 30 minutes are the same task
TASK_MIN_GAP = 15      # seconds between two AdsGram tasks of one player (a burst of reports is not N tasks)


def _now():
    return datetime.now(timezone.utc)


def _day() -> str:
    from core.timeutil import msk_today_str
    return msk_today_str()


def next_reset_iso() -> str:
    """The next 00:00 MSK — when the daily limits start again."""
    msk = timezone(timedelta(hours=3))
    n = _now().astimezone(msk)
    nxt = (n + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt.astimezone(timezone.utc).isoformat()


async def get_config(db) -> Dict[str, Any]:
    d = await db.admin_settings.find_one({"type": "offers"}, {"_id": 0}) or {}
    return {**DEFAULTS, **{k: v for k, v in d.items() if k in DEFAULTS}}


def _task_block_ok(v: str) -> bool:
    return bool(re.match(r"^task-\d{1,12}$", v or ""))


async def _credited_today(db, uid: str, kind: str) -> int:
    return await db.offer_rewards.count_documents({"user_id": uid, "day": _day(), "kind": kind, "credited": True})


async def _credit(db, uid: str, kind: str, reward: float, cap: int, extra: Dict[str, Any]) -> bool:
    """Credit one offer reward if the daily cap allows; writes the offer_rewards doc either way. Returns credited."""
    ok = reward > 0 and await _credited_today(db, uid, kind) < cap
    await db.offer_rewards.insert_one({"id": str(uuid.uuid4()), "user_id": uid, "day": _day(), "kind": kind,
                                       "reward": reward if ok else 0, "credited": ok, "created_at": _now().isoformat(),
                                       **({} if ok else {"reason": "cap"}), **extra})
    if ok:
        from routes.tasks import credit_task_reward_bonus
        await credit_task_reward_bonus(db, uid, reward, "Рекламное задание" if kind == "adsgram_task" else "Просмотр рекламы",
                                       tx_type="offer_reward")
    return ok


# ───────── rewarded ad views ─────────
async def _ads_cfg(db):
    import ads
    return await ads.get_config(db)


def _ad_networks_on(acfg) -> bool:
    import ads
    return ads.monetag_on(acfg) or ads.adsgram_on(acfg)


async def credit_ad_view(db, uid: str, ymid: str, reward_event: str = "") -> Dict[str, Any]:
    """One watched rewarded ad of the «Посмотри рекламу» offer → the reward (once per ymid, within the daily cap)."""
    cfg = await get_config(db)
    acfg = await _ads_cfg(db)
    if acfg.get("require_valued") and reward_event == "non_valued":
        return {"credited": False, "reason": "non_valued"}
    if await db.offer_rewards.find_one({"ymid": ymid, "kind": "ad"}, {"_id": 0, "id": 1}):
        return {"credited": False, "reason": "already"}
    ok = await _credit(db, uid, "ad", float(cfg["ad_offer_reward"] or 0), int(cfg["ad_offer_daily_cap"] or 0), {"ymid": ymid})
    return {"credited": ok, "reason": "" if ok else "cap"}


async def on_confirmed_view(db, uid: str, ymid: str, reward_event: str = "") -> None:
    """ads.py: the network confirmed a show of purpose «offer» (Monetag postback / AdsGram Reward URL).
    Credits only in the verify mode — otherwise the app's report already did."""
    try:
        acfg = await _ads_cfg(db)
        if acfg.get("verify_postback"):
            await credit_ad_view(db, uid, ymid, reward_event)
    except Exception:
        pass


# ───────── AdsGram Task ─────────
async def adsgram_task_server(db, uid: str) -> Dict[str, Any]:
    """AdsGram's Reward URL for the Task block: the player has done an advertiser's task."""
    cfg = await get_config(db)
    reward, cap = float(cfg["adsgram_task_reward"] or 0), int(cfg["adsgram_task_daily_cap"] or 0)
    since = (_now() - timedelta(minutes=PAIR_MIN)).isoformat()
    # the app already reported this task → confirm that report (credit now if it waited for us)
    rep = await db.offer_rewards.find({"user_id": uid, "kind": "adsgram_task", "source": "client", "confirmed": {"$ne": True},
                                       "created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", 1).limit(1).to_list(1)
    if rep:
        r = rep[0]
        if r.get("credited"):
            await db.offer_rewards.update_one({"id": r["id"]}, {"$set": {"confirmed": True}})
            return {"ok": True, "credited": False, "reason": "already_credited_by_app"}
        await db.offer_rewards.delete_one({"id": r["id"]})              # the pending report becomes the credited one
        ok = await _credit(db, uid, "adsgram_task", reward, cap, {"source": "server", "confirmed": True, "client_seen": True})
        return {"ok": True, "credited": ok, "reason": "" if ok else "cap"}
    ok = await _credit(db, uid, "adsgram_task", reward, cap, {"source": "server", "confirmed": True, "client_seen": False})
    return {"ok": True, "credited": ok, "reason": "" if ok else "cap"}


async def adsgram_task_client(db, uid: str) -> Dict[str, Any]:
    cfg = await get_config(db)
    since = (_now() - timedelta(minutes=PAIR_MIN)).isoformat()
    # AdsGram's server call came first → this report is the same task
    srv = await db.offer_rewards.find_one({"user_id": uid, "kind": "adsgram_task", "source": "server", "client_seen": False,
                                           "created_at": {"$gte": since}}, {"_id": 0, "id": 1, "credited": 1})
    if srv:
        await db.offer_rewards.update_one({"id": srv["id"]}, {"$set": {"client_seen": True}})
        return {"credited": bool(srv.get("credited")), "pending": False, "already": True}
    last = await db.offer_rewards.find({"user_id": uid, "kind": "adsgram_task", "source": "client"}, {"_id": 0, "created_at": 1}) \
        .sort("created_at", -1).limit(1).to_list(1)
    if last and (_now() - datetime.fromisoformat(last[0]["created_at"])).total_seconds() < TASK_MIN_GAP:
        raise HTTPException(status_code=429, detail="too_fast")
    if cfg.get("adsgram_task_trust_client"):
        ok = await _credit(db, uid, "adsgram_task", float(cfg["adsgram_task_reward"] or 0), int(cfg["adsgram_task_daily_cap"] or 0),
                           {"source": "client", "confirmed": False})
        return {"credited": ok, "pending": False, "reason": "" if ok else "cap"}
    pending = await db.offer_rewards.count_documents({"user_id": uid, "kind": "adsgram_task", "source": "client",
                                                      "credited": False, "confirmed": {"$ne": True}, "reason": {"$exists": False},
                                                      "created_at": {"$gte": since}})
    if pending >= 3:
        return {"credited": False, "pending": True}
    await db.offer_rewards.insert_one({"id": str(uuid.uuid4()), "user_id": uid, "day": _day(), "kind": "adsgram_task",
                                       "reward": 0, "credited": False, "source": "client", "confirmed": False,
                                       "created_at": _now().isoformat()})
    return {"credited": False, "pending": True}


async def _user_by_telegram(db, tid: str) -> str:
    tid = str(tid or "").strip()
    if not tid:
        return ""
    q = [{"telegram_id": tid}]
    if tid.isdigit():
        q.append({"telegram_id": int(tid)})
    u = await db.users.find_one({"$or": q}, {"_id": 0, "id": 1})
    return (u or {}).get("id") or ""


def create_offers_router(db, get_current_user, get_current_admin) -> APIRouter:
    r = APIRouter()

    async def _state(uid: str) -> Dict[str, Any]:
        cfg = await get_config(db)
        acfg = await _ads_cfg(db)
        out: Dict[str, Any] = {"resets_at": next_reset_iso()}
        block = str(cfg.get("adsgram_task_block_id") or "")
        if cfg.get("adsgram_task_enabled") and _task_block_ok(block):
            cap = int(cfg["adsgram_task_daily_cap"] or 0)
            done = await _credited_today(db, uid, "adsgram_task")
            since = (_now() - timedelta(minutes=PAIR_MIN)).isoformat()
            pend = await db.offer_rewards.count_documents({"user_id": uid, "kind": "adsgram_task", "source": "client", "credited": False,
                                                           "confirmed": {"$ne": True}, "reason": {"$exists": False},
                                                           "created_at": {"$gte": since}})
            out["adsgram_task"] = {"enabled": True, "block_id": block, "reward": float(cfg["adsgram_task_reward"] or 0),
                                   "cap": cap, "done_today": done, "left": max(0, cap - done), "pending": pend}
        else:
            out["adsgram_task"] = {"enabled": False}
        if cfg.get("ad_offers_enabled") and _ad_networks_on(acfg):
            cap = int(cfg["ad_offer_daily_cap"] or 0)
            done = await _credited_today(db, uid, "ad")
            gap = int(cfg["ad_offer_gap_sec"] or 0)
            last = await db.offer_rewards.find({"user_id": uid, "kind": "ad"}, {"_id": 0, "created_at": 1}) \
                .sort("created_at", -1).limit(1).to_list(1)
            nxt = ""
            if last and gap:
                t = datetime.fromisoformat(last[0]["created_at"]) + timedelta(seconds=gap)
                nxt = t.isoformat() if t > _now() else ""
            pend = 0
            if acfg.get("verify_postback"):
                since = (_now() - timedelta(minutes=15)).isoformat()
                rep = await db.ad_views.distinct("ymid", {"user_id": uid, "purpose": "offer", "source": "client", "created_at": {"$gte": since}})
                got = set(await db.offer_rewards.distinct("ymid", {"user_id": uid, "kind": "ad", "ymid": {"$in": rep}})) if rep else set()
                pend = len([y for y in rep if y not in got])
            out["ad"] = {"enabled": True, "reward": float(cfg["ad_offer_reward"] or 0), "cap": cap, "done_today": done,
                         "left": max(0, cap - done), "gap_sec": gap, "next_at": nxt, "pending": pend}
        else:
            out["ad"] = {"enabled": False}
        return out

    @r.get("/api/offers")
    async def offers(current_user=Depends(get_current_user)):
        return await _state(current_user.id)

    @r.post("/api/offers/ad/start")
    async def ad_start(current_user=Depends(get_current_user)):
        st = await _state(current_user.id)
        a = st["ad"]
        if not a.get("enabled"):
            raise HTTPException(status_code=400, detail="offers_off")
        if a["left"] <= 0:
            raise HTTPException(status_code=400, detail="cap")
        ymid = f"{current_user.id}.o{secrets.token_hex(5)}"
        await db.ad_sessions.insert_one({"ymid": ymid, "user_id": current_user.id, "day": _day(), "purpose": "offer",
                                         "created_at": _now().isoformat()})
        return {"ymid": ymid, "request_var": "offer"}

    @r.post("/api/offers/ad/watched")
    async def ad_watched(body: Dict[str, Any] = None, current_user=Depends(get_current_user)):
        body = body or {}
        uid = current_user.id
        ymid = str(body.get("ymid") or "")
        sess = await db.ad_sessions.find_one({"ymid": ymid, "user_id": uid, "purpose": "offer"}, {"_id": 0, "ymid": 1})
        if not sess:
            raise HTTPException(status_code=400, detail="no_show")
        reward = str(body.get("reward_event_type") or "").lower()
        reward = reward if reward in ("valued", "non_valued") else ""
        if not await db.ad_views.find_one({"ymid": ymid, "source": "client"}, {"_id": 0, "id": 1}):
            await db.ad_views.insert_one({"id": str(uuid.uuid4()), "user_id": uid, "day": _day(), "purpose": "offer",
                                          "source": "client", "ymid": ymid, "reward": reward, "created_at": _now().isoformat()})
        acfg = await _ads_cfg(db)
        res: Dict[str, Any] = {"credited": False, "pending": False}
        if acfg.get("verify_postback"):
            # the network's postback may already be here
            if await db.offer_rewards.find_one({"ymid": ymid, "kind": "ad", "credited": True}, {"_id": 0, "id": 1}):
                res["credited"] = True
            else:
                res["pending"] = True
        else:
            cfg = await get_config(db)
            gap = int(cfg["ad_offer_gap_sec"] or 0)
            last = await db.offer_rewards.find({"user_id": uid, "kind": "ad"}, {"_id": 0, "created_at": 1}) \
                .sort("created_at", -1).limit(1).to_list(1)
            if gap and last and (_now() - datetime.fromisoformat(last[0]["created_at"])).total_seconds() < gap:
                raise HTTPException(status_code=429, detail="too_fast")
            res.update(await credit_ad_view(db, uid, ymid, reward))
        return {**res, "state": await _state(uid)}

    @r.post("/api/offers/adsgram-task/done")
    async def task_done(current_user=Depends(get_current_user)):
        st = await _state(current_user.id)
        if not st["adsgram_task"].get("enabled"):
            raise HTTPException(status_code=400, detail="offers_off")
        res = await adsgram_task_client(db, current_user.id)
        return {**res, "state": await _state(current_user.id)}

    @r.get("/api/offers/adsgram-task/reward")
    async def task_reward_url(request: Request):
        """AdsGram «Reward URL» of the Task block: …/api/offers/adsgram-task/reward?userid=[userId]&secret=<secret>"""
        acfg = await _ads_cfg(db)
        q = request.query_params
        if q.get("secret") != acfg["postback_secret"]:
            raise HTTPException(status_code=403, detail="bad secret")
        tid = q.get("userid") or q.get("userId") or q.get("user_id") or ""
        log_id = str(uuid.uuid4())
        await db.ad_postbacks.insert_one({"id": log_id, "network": "adsgram_task", "ymid": "", "event": "adsgram_task",
                                          "telegram_id": str(tid)[:32], "day": _day(),
                                          "ip": request.client.host if request.client else "", "created_at": _now().isoformat()})
        uid = await _user_by_telegram(db, tid)
        res = {"ok": False, "reason": "unknown_user"} if not uid else await adsgram_task_server(db, uid)
        await db.ad_postbacks.update_one({"id": log_id}, {"$set": {"result": res}})
        return res

    @r.get("/api/admin/offers")
    async def a_get(_=Depends(get_current_admin)):
        cfg = await get_config(db)
        acfg = await _ads_cfg(db)
        today = _day()

        async def _sum(kind):
            n = await db.offer_rewards.count_documents({"day": today, "kind": kind, "credited": True})
            players = len(await db.offer_rewards.distinct("user_id", {"day": today, "kind": kind, "credited": True}))
            city = 0.0
            async for x in db.offer_rewards.find({"day": today, "kind": kind, "credited": True}, {"_id": 0, "reward": 1}):
                city += float(x.get("reward") or 0)
            return {"count": n, "players": players, "city": city}
        return {**cfg, "postback_secret": acfg["postback_secret"], "ad_networks_on": _ad_networks_on(acfg),
                "verify_postback": bool(acfg.get("verify_postback")),
                "today": {"adsgram_task": await _sum("adsgram_task"), "ad": await _sum("ad"),
                          "adsgram_task_pending": await db.offer_rewards.count_documents(
                              {"day": today, "kind": "adsgram_task", "source": "client", "credited": False,
                               "confirmed": {"$ne": True}, "reason": {"$exists": False}})}}

    @r.put("/api/admin/offers")
    async def a_put(body: Dict[str, Any], _=Depends(get_current_admin)):
        upd = {k: v for k, v in (body or {}).items() if k in DEFAULTS}
        if "adsgram_task_block_id" in upd:
            v = str(upd["adsgram_task_block_id"] or "").strip()
            if v.isdigit():
                v = f"task-{v}"
            if v and not _task_block_ok(v):
                raise HTTPException(status_code=400, detail="ID блока AdsGram Task должен быть вида task-12345")
            upd["adsgram_task_block_id"] = v
        for k, lo, hi in (("adsgram_task_reward", 0, 100000), ("ad_offer_reward", 0, 100000)):
            if k in upd:
                upd[k] = max(lo, min(hi, float(upd[k] or 0)))
        for k, lo, hi in (("adsgram_task_daily_cap", 0, 100), ("ad_offer_daily_cap", 0, 50), ("ad_offer_gap_sec", 0, 3600)):
            if k in upd:
                upd[k] = max(lo, min(hi, int(float(upd[k] or 0))))
        for k in ("adsgram_task_enabled", "adsgram_task_trust_client", "ad_offers_enabled"):
            if k in upd:
                upd[k] = bool(upd[k])
        await db.admin_settings.update_one({"type": "offers"}, {"$set": {"type": "offers", **upd}}, upsert=True)
        return await a_get()

    return r
