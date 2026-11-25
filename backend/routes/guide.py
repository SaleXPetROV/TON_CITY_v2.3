"""The in-game guide — server side.

Since 17 Nov 2026 (owner): the guide is a window of 9 illustrated steps «как заработать» shown once on entering the
game (frontend src/guide/EarnIntro.jsx), short hints on every page shown on the first visit (src/guide/Guide.jsx,
replayed from the «?» of a page), and the 3-day plan with its reward on the «Задания» page (src/guide/PlanBlock.jsx):
  GET  /api/guide/plan             the plan: 5 goals, a 3-day timer from the first time the player saw it
  POST /api/guide/plan/claim       {choice} the reward — only if the goals were done before the timer ran out
  POST /api/guide/intro-seen       the 9-step window was seen (it does not open by itself any more)
  POST /api/guide/tour-seen        {key} the hints of a page were seen
The old linear steps below are kept for older app builds.

The guide itself is drawn by the frontend (src/guide). The server keeps the player's progress and gives the guide the
facts it adapts to: which business the player took, what it makes and uses, whether a shift runs, the first lot, the
3-day plan. Nothing here is a sandbox: every step works on the player's real account.

  GET  /api/guide                  progress + facts
  POST /api/guide/step             {step} — remember the step the player is on (closing the app resumes there)
  POST /api/guide/trial-batch      step 19 «Первая партия»: tier 1 +10, tier 2 +1, tier 3 nothing — once per account
  POST /api/guide/first-sale       step 34: the City buys the player's first lot 10 s after it went up
  POST /api/guide/reward           screen 63: the 3-day plan is done (a business of level 1+) → one tier-3 resource
                                   that cannot be sold; the player switches its buff on himself (Склад → Усилители). Once per account. No $CITY.
  POST /api/guide/finish           the guide is over (also after screen 62 when the plan is not done yet)
  POST /api/guide/restart          «Пройти гид заново» (settings) — progress only, rewards stay once per account
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.dependencies import get_current_user
from core.models import User
from core.helpers import get_user_identifiers, resolve_owner_keys, owner_businesses_query

logger = logging.getLogger(__name__)

TOTAL_STEPS = 62
FIRST_SALE_DELAY_SEC = 10          # «Город выкупает первую партию через 10 секунд после выставления»
T3_REWARD = ("neuro_core", "gold_bill", "license_token", "luck_chip", "war_protocol", "bio_module", "gateway_code")
TRIAL_BATCH = {1: 10, 2: 1, 3: 0}   # step 19, by the tier of the player's business


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


class StepIn(BaseModel):
    step: int
    path: Optional[str] = None      # "new" | "returning"


class FirstSaleIn(BaseModel):
    listing_id: str


class RewardIn(BaseModel):
    choice: str


class TourIn(BaseModel):
    key: str


PLAN_DAYS = 3
PLAN_ITEMS = ("business", "shift", "sale", "repair", "upgrade")


def create_guide_router(db, apply_sale=None):
    router = APIRouter(prefix="/api/guide", tags=["guide"])

    async def _me(current_user: User):
        ui = await get_user_identifiers(db, current_user)
        if not ui["user"]:
            raise HTTPException(status_code=401, detail="user not found")
        return ui

    async def _businesses(user: Dict[str, Any]):
        keys = await resolve_owner_keys(db, user.get("id"))
        q = {**owner_businesses_query(keys), "tutorial": {"$ne": True}, "is_seized": {"$ne": True}}
        return await db.businesses.find(q, {"_id": 0}).sort("created_at", 1).to_list(50)

    async def _facts(ui) -> Dict[str, Any]:
        from business_config import (BUSINESSES, BUSINESS_KEY_MAP, RESOURCE_TYPES, get_production,
                                     get_consumption_breakdown, get_storage_capacity)
        from core.business_rules import shift_is_active
        user = ui["user"]
        bizs = await _businesses(user)
        f: Dict[str, Any] = {"has_business": bool(bizs), "business_count": len(bizs), "max_level": 0}
        if bizs:
            f["max_level"] = max(int(b.get("level") or 0) for b in bizs)
            b = bizs[0]
            bt = BUSINESS_KEY_MAP.get(b.get("business_type"), b.get("business_type"))
            cfg = BUSINESSES.get(bt) or {}
            level = int(b.get("level") or 0)
            produces = cfg.get("produces") or ""
            per_day = float(get_production(bt, level) or 0)
            uses = {r: float(v) for r, v in (get_consumption_breakdown(bt, max(1, level)) or {}).items()}
            tier = int(cfg.get("tier") or 1)
            f["biz"] = {
                "id": b.get("id"), "type": bt, "level": level, "tier": tier, "icon": cfg.get("icon"),
                "name": cfg.get("name") or {}, "produces": produces, "per_hour": round(per_day / 24.0, 2),
                "per_day": per_day, "uses": uses, "durability": float(b.get("durability", 100) or 0),
                "shift_active": bool(shift_is_active(b)), "shift_ends_at": b.get("shift_ends_at"),
                "expires_at": b.get("expires_at"), "is_zero": bool(b.get("is_zero_business")) or level == 0,
                "storage": int(((b.get("storage") or {}).get("capacity")) or get_storage_capacity(bt, max(1, level)) or 0),
                "x": b.get("x"), "y": b.get("y"),
                "city_buys": tier == 1,             # the City Market buys tier-1 goods only
                # level 0 → 1 costs the plot's map price (routes/business_mgmt.upgrade_business), real $CITY only
                "upgrade_city": round(float(b.get("zero_map_price") or cfg.get("base_cost_ton") or cfg.get("price_ton") or 0) * 1000.0, 2),
            }
            res = user.get("resources") or {}
            f["product_amount"] = int(float(res.get(produces, 0) or 0))
            # the price the City buys this product at (the admin's «Цена выкупа», market_maker): step 31 names it.
            # (the key keeps its old name: the guide texts use it as {price})
            try:
                import market_maker as _mm
                cfg_mm = await _mm.get_config(db)
                f["system_price_city"] = round(_mm.prices_city(cfg_mm, produces)[0], 2) if produces else 0
                f["biz"]["city_buys"] = bool(produces in (cfg_mm.get("buy_resources") or []))
            except Exception:
                f["system_price_city"] = 0
            meta = RESOURCE_TYPES.get(produces) or {}
            f["product_tier"] = int(meta.get("tier") or tier)
        # the player's lots of anything (step 33/34 follows the newest lot)
        ids = list(ui["ids"])
        lot = await db.market_listings.find_one({"seller_id": {"$in": ids}, "status": "active", "is_bot": {"$ne": True}},
                                                {"_id": 0}, sort=[("created_at", -1)])
        if lot:
            f["lot"] = {"id": lot.get("id"), "resource": lot.get("resource_type"), "amount": int(lot.get("amount") or 0),
                        "created_at": lot.get("created_at"), "price_city": round(float(lot.get("price_per_unit") or 0) * 1000, 2)}
        sold = await db.market_listings.find_one({"seller_id": {"$in": ids}, "status": "sold"}, {"_id": 0, "id": 1, "sold_via": 1})
        trade = await db.mm_trades.find_one({"user_id": user.get("id"), "side": "buy"}, {"_id": 0, "units": 1, "resource": 1, "total_ton": 1, "seller_received_ton": 1}, sort=[("ts", -1)])
        f["sold_once"] = bool(sold or trade)
        if trade:
            f["city_trade"] = {"units": trade.get("units"), "resource": trade.get("resource"),
                               "total_city": round(float(trade.get("total_ton") or 0) * 1000, 2),
                               "received_city": round(float(trade.get("seller_received_ton") or 0) * 1000, 2)}
        # activity rule (step 50): bought ≥ 40 or sold ≥ 100 units in 10 days
        try:
            import inactivity as _ia
            cutoff = (_now() - timedelta(days=_ia.WINDOW_DAYS)).isoformat()
            async def _sum(field):
                n = 0.0
                async for row in db.transactions.aggregate([
                        {"$match": {"tx_type": "market_purchase", "created_at": {"$gte": cutoff}, field: {"$in": ids}}},
                        {"$group": {"_id": None, "u": {"$sum": "$resource_amount"}}}]):
                    n = float(row.get("u") or 0)
                return n
            f["activity"] = {"bought": int(await _sum("buyer_id")), "sold": int(await _sum("seller_id")),
                             "buy_min": _ia.MARKET_BUY_MIN, "sell_min": _ia.MARKET_SELL_MIN, "days": _ia.WINDOW_DAYS}
        except Exception as e:
            logger.debug(f"guide activity: {e}")
        # steps 10–12 need a free business from the City (presale, level 0 for 3 days). None on sale now, or the
        # player may not take one (already upgraded one before) → he goes the «returning» way, like a player who
        # already has a business (the steps about his own business are passed over while he has none)
        if not bizs:
            try:
                import presale_gate as _pg
                import zero_business as _zb
                f["free_lots"] = int(await _pg.free_plots_open(db))
                f["can_claim_free"] = f["free_lots"] > 0 and await _zb.can_stake_zero(db, user, set(ids))
            except Exception as e:  # noqa: BLE001
                logger.debug(f"guide free lots: {e}")
                f["can_claim_free"] = True          # unknown: keep the usual way
        g = user.get("guide") or {}
        f["trial_batch_done"] = bool(g.get("trial_batch_at"))
        f["reward_claimed"] = bool(user.get("tutorial_t3_reward_granted"))
        f["reward_choice"] = user.get("tutorial_t3_reward_choice")
        f["plan_done"] = f["max_level"] >= 1
        return f

    def _state(user: Dict[str, Any]) -> Dict[str, Any]:
        g = user.get("guide") or {}
        return {"step": int(g.get("step") or 1), "path": g.get("path") or "new", "started_at": g.get("started_at"),
                "finished_at": g.get("finished_at"), "active": not g.get("finished_at"), "total": TOTAL_STEPS,
                "intro_seen": bool(g.get("intro_seen_at")), "tours_seen": list(g.get("tours_seen") or [])}

    async def _plan(ui) -> Dict[str, Any]:
        """The 3-day plan (the «Задания» page): 5 goals, the timer starts the first time the player sees it; the
        reward (one tier-3 resource, unsellable) only if every goal was done before the timer ran out."""
        user = ui["user"]
        now = _now()
        if user.get("tutorial_t3_reward_granted"):
            return {"show": False, "claimed": True}
        p = user.get("plan3") or {}
        started = _parse(p.get("started_at"))
        if not started:
            started = now
            await db.users.update_one({"id": user["id"], "plan3.started_at": {"$exists": False}},
                                      {"$set": {"plan3.started_at": now.isoformat()}})
        ends = started + timedelta(days=PLAN_DAYS)
        f = await _facts(ui)
        ids = list(ui["ids"])
        shift = bool(f.get("trial_batch_done") or (f.get("biz") or {}).get("shift_active"))
        if not shift:
            shift = bool(await db.analytics_events.find_one({"user_id": user["id"], "event": "first_shift"}, {"_id": 1}))
        if not shift:
            shift = bool(await db.businesses.find_one({**owner_businesses_query(set(ids)), "shift_started_at": {"$exists": True, "$ne": None}}, {"_id": 1}))
        repair = bool(await db.transactions.find_one({"tx_type": "repair", "user_id": user["id"]}, {"_id": 1}))
        done = {"business": bool(f.get("has_business")), "shift": shift, "sale": bool(f.get("sold_once")),
                "repair": repair, "upgrade": int(f.get("max_level") or 0) >= 1}
        all_done = all(done.values())
        done_at = _parse(p.get("done_at"))
        if all_done and not done_at and now <= ends:
            done_at = now
            await db.users.update_one({"id": user["id"]}, {"$set": {"plan3.done_at": now.isoformat()}})
        in_time = bool(done_at and done_at <= ends)
        return {"show": now <= ends or in_time, "claimed": False, "started_at": started.isoformat(),
                "ends_at": ends.isoformat(), "now": now.isoformat(), "days": PLAN_DAYS,
                "items": [{"id": k, "done": done[k]} for k in PLAN_ITEMS], "done": sum(done.values()),
                "all_done": all_done, "in_time": in_time, "can_claim": in_time,
                "biz_ends_at": (f.get("biz") or {}).get("expires_at"), "upgrade_city": (f.get("biz") or {}).get("upgrade_city")}

    async def _grant_reward(user: Dict[str, Any], choice: str) -> Dict[str, Any]:
        r = await db.users.update_one(
            {"id": user["id"], "tutorial_t3_reward_granted": {"$ne": True}},
            {"$inc": {f"resources.{choice}_tutorial": 1},
             "$set": {"tutorial_t3_reward_granted": True, "tutorial_t3_reward_choice": choice,
                      "tutorial_t3_reward_granted_at": _now().isoformat(), "guide.reward_at": _now().isoformat(),
                      "plan3.claimed_at": _now().isoformat()}})
        return {"ok": True, "already": not r.modified_count, "activated": False}

    @router.get("/plan")
    async def guide_plan(current_user: User = Depends(get_current_user)):
        return await _plan(await _me(current_user))

    @router.post("/plan/claim")
    async def guide_plan_claim(data: RewardIn, current_user: User = Depends(get_current_user)):
        if data.choice not in T3_REWARD:
            raise HTTPException(status_code=400, detail="bad choice")
        ui = await _me(current_user)
        p = await _plan(ui)
        if p.get("claimed"):
            return {"ok": True, "already": True, "activated": False}
        if not p.get("can_claim"):
            raise HTTPException(status_code=400, detail="plan_expired" if not p.get("show") else "plan_not_done")
        return await _grant_reward(ui["user"], data.choice)

    @router.post("/intro-seen")
    async def guide_intro_seen(current_user: User = Depends(get_current_user)):
        ui = await _me(current_user)
        await db.users.update_one({"id": ui["user"]["id"]}, {"$set": {"guide.intro_seen_at": _now().isoformat()}})
        return {"ok": True}

    @router.post("/tour-seen")
    async def guide_tour_seen(data: TourIn, current_user: User = Depends(get_current_user)):
        key = str(data.key or "")[:60]
        if not key:
            raise HTTPException(status_code=400, detail="no key")
        ui = await _me(current_user)
        await db.users.update_one({"id": ui["user"]["id"]}, {"$addToSet": {"guide.tours_seen": key}})
        return {"ok": True}

    @router.get("")
    async def guide_state(current_user: User = Depends(get_current_user)):
        ui = await _me(current_user)
        facts = await _facts(ui)
        st = _state(ui["user"])
        # Steps 10–12 = «claim a free business». A player who already HAS a business must never stand there
        # (an older build, a business bought outside the guide, the app closed mid-step): put him where he belongs —
        # 13 («the business is yours», then production) if the guide's free level-0 claim is his, else 20 like the
        # branch after the map (path «returning»).
        # The same 20 / «returning» when nothing can be claimed: the City has no free business on sale right now.
        no_free = not facts.get("has_business") and facts.get("can_claim_free") is False
        if st["active"] and 10 <= st["step"] <= 12 and (facts.get("has_business") or no_free):
            to, path = (13, st["path"]) if (facts.get("biz") or {}).get("is_zero") else (20, "returning")
            await db.users.update_one({"id": ui["user"]["id"]}, {"$set": {"guide.step": to, "guide.path": path,
                                                                           "guide.updated_at": _now().isoformat()}})
            st.update({"step": to, "path": path})
        return {"state": st, "facts": facts}

    @router.post("/step")
    async def guide_step(data: StepIn, current_user: User = Depends(get_current_user)):
        ui = await _me(current_user)
        step = max(1, min(TOTAL_STEPS + 1, int(data.step)))
        upd = {"guide.step": step, "guide.updated_at": _now().isoformat()}
        if not (ui["user"].get("guide") or {}).get("started_at"):
            upd["guide.started_at"] = _now().isoformat()
        if data.path in ("new", "returning"):
            upd["guide.path"] = data.path
        await db.users.update_one({"id": ui["user"]["id"]}, {"$set": upd})
        return {"ok": True, "step": step}

    @router.post("/trial-batch")
    async def guide_trial_batch(current_user: User = Depends(get_current_user)):
        ui = await _me(current_user)
        f = await _facts(ui)
        if not f.get("biz"):
            raise HTTPException(status_code=400, detail="no business")
        units = TRIAL_BATCH.get(int(f["biz"]["tier"]), 0)
        res = f["biz"]["produces"]
        if units <= 0 or not res:
            return {"ok": True, "units": 0, "resource": res}
        r = await db.users.update_one({"id": ui["user"]["id"], "guide.trial_batch_at": {"$exists": False}},
                                      {"$inc": {f"resources.{res}": units},
                                       "$set": {"guide.trial_batch_at": _now().isoformat()}})
        return {"ok": True, "units": units if r.modified_count else 0, "resource": res, "already": not r.modified_count}

    @router.post("/first-sale")
    async def guide_first_sale(data: FirstSaleIn, current_user: User = Depends(get_current_user)):
        """The City buys the newcomer's FIRST lot 10 s after it went up (the regular cycle runs every 5 min)."""
        ui = await _me(current_user)
        lot = await db.market_listings.find_one({"id": data.listing_id, "seller_id": {"$in": list(ui["ids"])}}, {"_id": 0})
        if not lot:
            raise HTTPException(status_code=404, detail="lot not found")
        if lot.get("status") == "sold":
            return {"sold": True}
        created = _parse(lot.get("created_at"))
        wait = FIRST_SALE_DELAY_SEC - ((_now() - created).total_seconds() if created else 0)
        if wait > 0.5:
            return {"sold": False, "wait_sec": int(wait + 0.999)}
        if apply_sale is None:
            return {"sold": False, "reason": "unavailable"}
        import market_maker
        out = await market_maker.run_buy_side(db, apply_sale, only_listing=data.listing_id,
                                              newbie_delay_min=FIRST_SALE_DELAY_SEC / 60.0)
        lot = await db.market_listings.find_one({"id": data.listing_id}, {"_id": 0, "status": 1, "amount": 1})
        return {"sold": bool(out.get("bought")), "status": (lot or {}).get("status"),
                "skipped": out.get("skipped") or {}}

    @router.post("/reward")
    async def guide_reward(data: RewardIn, current_user: User = Depends(get_current_user)):
        ui = await _me(current_user)
        user = ui["user"]
        if data.choice not in T3_REWARD:
            raise HTTPException(status_code=400, detail="bad choice")
        # the same rule as the plan on the «Задания» page: every goal, before the 3-day timer ran out
        p = await _plan(ui)
        if p.get("claimed"):
            return {"ok": True, "already": True, "activated": False}
        if not p.get("can_claim"):
            raise HTTPException(status_code=400, detail="plan_not_done")
        return await _grant_reward(user, data.choice)

    async def _activate_t3(uid: str, choice: str) -> bool:
        """The reward's buff goes on at once (the player owns a level-1+ business)."""
        try:
            from routes.buffs import RESOURCE_BUFFS
            buff = RESOURCE_BUFFS.get(choice)
            u = await db.users.find_one({"id": uid}, {"_id": 0})
            if not buff or not u or int(((u.get("resources") or {}).get(f"{choice}_tutorial")) or 0) < 1:
                return False
            now = _now()
            active = [b for b in (u.get("active_resource_buffs") or [])
                      if (_parse(b.get("expires_at")) or now) > now]
            if any(b.get("resource_id") == choice for b in active):
                return False
            active.append({"resource_id": choice, "buff_name": buff["name"], "buff_icon": buff["icon"],
                           "buff_description": buff["description"], "effect_type": buff["effect_type"],
                           "effect_value": buff["effect_value"], "activated_at": now.isoformat(),
                           "expires_at": (now + timedelta(days=buff["duration_days"])).isoformat(),
                           "duration_days": buff["duration_days"], "active": True, "source": "guide_reward"})
            await db.users.update_one({"id": uid}, {"$inc": {f"resources.{choice}_tutorial": -1},
                                                    "$set": {"active_resource_buffs": active}})
            return True
        except Exception as e:
            logger.warning(f"guide reward activation: {e}")
            return False

    @router.get("/rewards")
    async def guide_rewards(current_user: User = Depends(get_current_user)):
        """The 7 tier-3 resources of screen 63 with what each one gives and for how long."""
        await _me(current_user)
        try:
            from routes.buffs import RESOURCE_BUFFS
        except Exception:
            RESOURCE_BUFFS = {}
        out = []
        for r in T3_REWARD:
            b = RESOURCE_BUFFS.get(r) or {}
            out.append({"resource": r, "icon": b.get("icon"), "effect_type": b.get("effect_type"),
                        "effect_value": b.get("effect_value"), "days": b.get("duration_days")})
        return {"items": out}

    @router.post("/finish")
    async def guide_finish(current_user: User = Depends(get_current_user)):
        ui = await _me(current_user)
        await db.users.update_one({"id": ui["user"]["id"]}, {"$set": {"guide.finished_at": _now().isoformat(),
                                                                      "guide.step": TOTAL_STEPS + 1}})
        return {"ok": True}

    @router.post("/restart")
    async def guide_restart(current_user: User = Depends(get_current_user)):
        ui = await _me(current_user)
        # «Пройти гид заново»: the 9-step window and every page's hints show again (the plan and rewards stay)
        await db.users.update_one({"id": ui["user"]["id"]},
                                  {"$set": {"guide.step": 1, "guide.started_at": _now().isoformat(), "guide.tours_seen": []},
                                   "$unset": {"guide.finished_at": "", "guide.intro_seen_at": ""}})
        return {"ok": True}

    return router
