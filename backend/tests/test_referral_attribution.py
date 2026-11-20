"""Referrals: players attributed only via ref_by / partner_ref_id get referrerId (list + 5 % income agree),
the player never counts as his own referral, «ref_<id>» / «p_<id>» start params resolve."""
import asyncio
import os
import sys
import uuid

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


async def _run():
    from dotenv import load_dotenv
    from motor.motor_asyncio import AsyncIOMotorClient
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    import server as srv
    import auth_handler
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    orig = srv.db
    srv.db = client[os.environ["DB_NAME"]]
    db = srv.db
    ref, tg, selfu = (f"rt-{uuid.uuid4().hex[:8]}" for _ in range(3))
    try:
        await db.users.insert_many([
            {"id": ref, "username": "ref_owner", "balance_ton": 0.0},
            {"id": tg, "username": "tg_friend", "ref_by": f"p_{ref}", "referrerId": None},        # Telegram signup
            {"id": selfu, "username": "self", "ref_by": selfu},                                    # opened own link
        ])
        assert await auth_handler.resolve_referrer_id(db, f"ref_{ref}") == ref
        assert await auth_handler.resolve_referrer_id(db, f"https://x/?startapp=p_{ref}") == ref
        await srv.repair_referrer_ids()
        assert (await db.users.find_one({"id": tg}))["referrerId"] == ref
        assert not (await db.users.find_one({"id": selfu})).get("referrerId")
        n, _earned, _rows = await srv._build_referral_list(selfu)
        assert n == 0                                                     # not his own referral
        # the 5 % split now reaches the referrer
        await db.users.update_one({"id": tg}, {"$set": {"referrerId": None}})
        admin_tax, amount, rid, _bonus = await srv.apply_referral_tax_split({"id": tg}, 1.0, 0.1, None)
        assert rid == ref and amount > 0
    finally:
        await db.users.delete_many({"id": {"$in": [ref, tg, selfu]}})
        srv.db = orig


def test_referral_attribution():
    asyncio.run(_run())
