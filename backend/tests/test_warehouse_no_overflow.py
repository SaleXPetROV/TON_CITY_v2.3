"""A warehouse never goes over its capacity: every path that GIVES a player resources respects the free space
(tender deliveries, the level-0 starter grant, quest rewards; contracts in the economic tick)."""
import asyncio
import os
import sys
import uuid

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def _db():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from motor.motor_asyncio import AsyncIOMotorClient
    return AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_room_and_fits():
    from core import warehouse as wh

    async def run():
        db = _db()
        uid = f"wh-{uuid.uuid4().hex[:8]}"
        await db.users.insert_one({"id": uid, "resources": {"energy": 45}})        # no business → 50 slots
        try:
            u = await db.users.find_one({"id": uid}, {"_id": 0})
            assert await wh.room_for(db, u, "energy") == 5
            assert await wh.room_for(db, u, "chips") == 1                         # tier 2 = 5 slots a unit
            assert (await wh.fits(db, u, {"energy": 5}))["ok"]
            f = await wh.fits(db, u, {"energy": 6})
            assert not f["ok"] and f["need"] == 6 and f["free"] == 5
        finally:
            await db.users.delete_many({"id": uid})
    asyncio.run(run())


def test_tender_delivery_waits_for_space(monkeypatch):
    import routes.tenders as tenders

    async def run():
        db = _db()
        monkeypatch.setattr(tenders, "db", db)

        async def _quiet(*a, **k):
            return None
        monkeypatch.setattr(tenders, "_notify_user", _quiet)
        monkeypatch.setattr(tenders, "_emit_ws", _quiet)
        tag = uuid.uuid4().hex[:8]
        seller, buyer, cid = f"ts-{tag}", f"tb-{tag}", f"tc-{tag}"
        await db.users.insert_many([
            {"id": seller, "username": "s", "resources": {"energy": 500}, "balance_ton": 0},
            {"id": buyer, "username": "b", "resources": {"energy": 45}, "balance_ton": 100}])   # 5 slots free
        contract = {"id": cid, "seller_id": seller, "buyer_id": buyer, "resource_type": "energy", "daily_amount": 20,
                    "price_per_unit": 3, "tax_rate": 0.05, "status": "ACTIVE", "seller_username": "s",
                    "buyer_username": "b"}
        await db.tender_contracts.insert_one(dict(contract))
        try:
            await tenders._process_tick(dict(contract))
            c = await db.tender_contracts.find_one({"id": cid}, {"_id": 0})
            assert c["status"] == "PENDING_STORAGE"
            b = await db.users.find_one({"id": buyer}, {"_id": 0})
            assert b["resources"]["energy"] == 45 and b["balance_ton"] == 100        # nothing moved, nothing paid
        finally:
            await db.users.delete_many({"id": {"$in": [seller, buyer]}})
            await db.tender_contracts.delete_many({"id": cid})
    asyncio.run(run())


def test_zero_starter_grant_fits_the_warehouse():
    import zero_business as zb

    async def run():
        db = _db()
        uid = f"wz-{uuid.uuid4().hex[:8]}"
        await db.users.insert_one({"id": uid, "resources": {"energy": 50}})        # full (50 / 50)
        try:
            await zb.grant_zero_consumption(db, uid, "scrap_yard")
            u = await db.users.find_one({"id": uid}, {"_id": 0})
            from core import warehouse as wh
            assert wh.used_by_resources(u.get("resources")) <= 50
        finally:
            await db.users.delete_many({"id": uid})
    asyncio.run(run())
