"""Daily bonus when the ad network has no ad: after `no_ad_attempts` real tries the bonus is given without the ad."""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import ads  # noqa: E402


class U:
    id = "u1"


def run(c):
    return asyncio.run(c)


async def world(**cfg):
    cfg = {"no_ad_rev": 2, "no_ad_attempts": 2, **cfg}   # the admin's own choice (2 tries) — kept by the migration
    cfg = {k: v for k, v in cfg.items() if v is not None}
    db = mongomock_motor.AsyncMongoMockClient()["ads"]
    await db.users.insert_one({"id": "u1"})
    await db.admin_settings.insert_one({"type": "ads", "enabled": True, "monetag_zone_id": "123", "daily_ads_required": 2,
                                        "min_gap_sec": 8, "postback_secret": "s", **cfg})
    r = ads.create_ads_router(db, lambda: None, lambda: None)
    ep = {route.path: route.endpoint for route in r.routes}
    return db, ep


async def start(db, ep):
    return (await ep["/api/ads/daily/start"](current_user=U()))["ymid"]


async def age_misses(db):
    # the server keeps a gap between two counted tries — move the earlier ones back in time
    await db.ad_misses.update_many({}, {"$set": {"created_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()}})


def test_two_tries_without_an_ad_open_the_bonus():
    async def go():
        db, ep = await world()
        no_ad = ep["/api/ads/daily/no-ad"]
        assert not (await ads.daily_gate(db, "u1"))["ok"]
        g = await no_ad({"ymid": await start(db, ep), "code": "no_fill"}, current_user=U())
        assert g["counted"] and not g["ok"] and g["misses"] == 1 and g["misses_needed"] == 2
        await age_misses(db)
        g = await no_ad({"ymid": await start(db, ep), "code": "timeout"}, current_user=U())
        assert g["ok"] and g.get("skipped") is True
        assert (await ads.daily_gate(db, "u1"))["ok"]
    run(go())


def test_closing_the_ad_fake_or_repeated_ymids_and_too_fast_tries_do_not_count():
    async def go():
        db, ep = await world()
        no_ad = ep["/api/ads/daily/no-ad"]
        y = await start(db, ep)
        assert not (await no_ad({"ymid": y, "code": "skipped"}, current_user=U()))["counted"]        # closed it
        assert not (await no_ad({"ymid": "u1.fake", "code": "no_fill"}, current_user=U()))["counted"]  # not issued
        assert not (await no_ad({"ymid": "u2.x", "code": "no_fill"}, current_user=U()))["counted"]     # another player
        assert (await no_ad({"ymid": y, "code": "no_fill"}, current_user=U()))["counted"]
        assert not (await no_ad({"ymid": y, "code": "no_fill"}, current_user=U()))["counted"]         # the same show
        g = await no_ad({"ymid": await start(db, ep), "code": "no_fill"}, current_user=U())             # within the gap
        assert not g["counted"] and not g["ok"]
    run(go())


def test_switch_off_keeps_the_old_rule():
    async def go():
        db, ep = await world(no_ad_skip=False)
        no_ad = ep["/api/ads/daily/no-ad"]
        for _ in range(3):
            g = await no_ad({"ymid": await start(db, ep), "code": "no_fill"}, current_user=U())
            await age_misses(db)
        assert not g["ok"] and "misses" not in g
    run(go())



def test_old_setting_is_moved_to_one_try_and_one_miss_opens_the_bonus():
    async def go():
        db, ep = await world(no_ad_rev=None, no_ad_attempts=2)       # saved before rev 2 (the old default 2)
        g = await ep["/api/ads/daily/no-ad"]({"ymid": await start(db, ep), "code": "no_fill"}, current_user=U())
        doc = await db.admin_settings.find_one({"type": "ads"})
        return g, doc
    g, doc = run(go())
    assert g["ok"] and g["skipped"] and g["misses_needed"] == 1
    assert doc["no_ad_attempts"] == 1 and doc["no_ad_rev"] == 2


def test_stuck_counts_only_after_the_ad_was_started_12_s_ago():
    async def go():
        db, ep = await world(no_ad_attempts=1)
        no_ad = ep["/api/ads/daily/no-ad"]
        y = await start(db, ep)
        g1 = await no_ad({"ymid": y, "code": "stuck"}, current_user=U())          # pressed at once: not counted
        await db.ad_sessions.update_one({"ymid": y}, {"$set": {
            "created_at": (datetime.now(timezone.utc) - timedelta(seconds=15)).isoformat()}})
        g2 = await no_ad({"ymid": y, "code": "stuck"}, current_user=U())
        return g1, g2
    g1, g2 = run(go())
    assert not g1["counted"] and not g1["ok"]
    assert g2["counted"] and g2["ok"]
