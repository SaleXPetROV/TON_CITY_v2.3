"""A drifted tender-escrow counter must not make money «not there»: the frozen part is recomputed from the
contracts that really hold escrow (189 $CITY on the balance, 173.77 «frozen» with no contract → «доступно 15.23»)."""
import asyncio
import os
import sys

import pytest

mongomock_motor = pytest.importorskip("mongomock_motor")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import frozen_tenders as ft  # noqa: E402
from core import balance  # noqa: E402


def run(c):
    return asyncio.run(c)


def test_drifted_frozen_is_healed_on_purchase():
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["fz"]
        await db.users.insert_one({"id": "u1", "balance_ton": 0.189, "bonus_balance": 0.0, "frozen_city_for_tenders": 173.77})
        # a proposal does not hold escrow
        await db.tender_contracts.insert_one({"id": "c0", "status": "PROPOSED", "buyer_id": "u1", "seller_id": "x",
                                              "buyer_escrow_deposit": 100})
        u = await db.users.find_one({"id": "u1"}, {"_id": 0})
        assert balance.total_available_ton(u) == pytest.approx(0.01523, abs=1e-6)          # the old, wrong answer
        assert await balance.total_available_ton_live(db, u) == pytest.approx(0.189)
        r = await balance.debit_user_split(db, {"id": "u1"}, 0.0289)
        assert r["ok"], r
        u = await db.users.find_one({"id": "u1"}, {"_id": 0})
        assert u["frozen_city_for_tenders"] == 0 and u["balance_ton"] == pytest.approx(0.1601)
    run(go())


def test_real_escrow_stays_frozen():
    async def go():
        db = mongomock_motor.AsyncMongoMockClient()["fz2"]
        await db.users.insert_one({"id": "u1", "balance_ton": 0.2, "frozen_city_for_tenders": 173.77})
        await db.tender_contracts.insert_many([
            {"id": "c1", "status": "ACTIVE", "seller_id": "u1", "buyer_id": "b", "escrow_deposit": 50.0},
            {"id": "c2", "status": "PENDING_FUNDS", "seller_id": "s", "buyer_id": "u1", "buyer_escrow_deposit": 30.0},
            {"id": "c3", "status": "BROKEN", "seller_id": "u1", "buyer_id": "b", "escrow_deposit": 999.0},
        ])
        u = await db.users.find_one({"id": "u1"}, {"_id": 0})
        assert await ft.effective_frozen_city(db, u) == pytest.approx(80.0)
        assert (await db.users.find_one({"id": "u1"}))["frozen_city_for_tenders"] == pytest.approx(80.0)
        assert await ft.heal_all(db) == 0
    run(go())
