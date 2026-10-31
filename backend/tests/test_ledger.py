"""Platform ledger: entries, real/bonus split, summary per kind and the admin endpoints."""
import os
import sys
import uuid
from functools import partial
from types import SimpleNamespace

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def test_ledger_summary_and_endpoints():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from motor.motor_asyncio import AsyncIOMotorClient
    import ledger
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    app = FastAPI()
    app.include_router(ledger.create_ledger_router(db, lambda: SimpleNamespace(id="adm", is_admin=True)))
    c = TestClient(app)
    uid = f"led-{uuid.uuid4().hex[:8]}"
    assert abs(ledger.real_part(10, 4, 1) - 0.4) < 1e-12 and ledger.real_part(0, 0, 1) == 1
    with c:
        before = c.get("/api/admin/ledger/summary", params={"period": "today"}).json()["totals"]
        try:
            c.portal.call(partial(ledger.record, db, "market_tax", 2.0, real_ton=0.5, user_id=uid))
            c.portal.call(partial(ledger.record, db, "land_sale", 10.0, user_id=uid))
            c.portal.call(partial(ledger.record, db, "founder_payout", 3.0, user_id=uid))
            c.portal.call(partial(ledger.record, db, "repair", 0, user_id=uid))            # ignored
            c.portal.call(partial(ledger.record, db, "unknown_kind", 1.0, user_id=uid))    # → other_in
            t = c.get("/api/admin/ledger/summary", params={"period": "today"}).json()["totals"]
            assert abs((t["income_ton"] - before["income_ton"]) - 13.0) < 1e-6
            assert abs((t["income_real_ton"] - before["income_real_ton"]) - 11.5) < 1e-6
            assert abs((t["expense_ton"] - before["expense_ton"]) - 3.0) < 1e-6
            items = c.get("/api/admin/ledger/entries", params={"limit": 50}).json()["items"]
            mine = [x for x in items if x.get("user_id") == uid]
            assert {x["kind"] for x in mine} == {"market_tax", "land_sale", "founder_payout", "other_in"}
            assert all(x["label"] for x in mine)
        finally:
            c.portal.call(db.platform_ledger.delete_many, {"user_id": uid})
