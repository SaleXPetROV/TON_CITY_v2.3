"""Founder Pass: visibility, direct purchase from the real balance, perks while founder, payouts to the real balance."""
import os
import sys
import uuid
from types import SimpleNamespace

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)


def _setup():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from motor.motor_asyncio import AsyncIOMotorClient
    import founder_pass
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    state = {"user": None}
    admin = SimpleNamespace(id="fp-test-admin", username="fpadmin", is_admin=True)
    app = FastAPI()
    app.include_router(founder_pass.create_founder_pass_router(db, lambda: state["user"], lambda: admin))
    return TestClient(app), db, state


def test_founder_pass_flow():
    c, db, state = _setup()
    uid = f"fp-test-{uuid.uuid4().hex[:8]}"
    uname = f"fpuser{uuid.uuid4().hex[:6]}"
    with c:
        orig = c.get("/api/admin/founder-pass/settings").json()
        try:
            c.portal.call(db.users.insert_one, {"id": uid, "username": uname, "balance_ton": 1.0})
            state["user"] = SimpleNamespace(id=uid, username=uname, is_admin=False)

            # off by default for players → not visible, profile card hides the entry
            c.put("/api/admin/founder-pass/settings", json={"enabled": False})
            assert c.get("/api/founder-pass").json() == {"visible": False}
            assert c.get("/api/profile/card").json()["founder_pass"] is False

            # on, whitelist without the player → still hidden; add him → visible
            tiers = [{"id": "t1", "name": "TEST PASS", "price": 200, "share_pct": 0.5, "slots_total": 1, "badge": "vip",
                      "perks": {"sale_tax_discount_pct": 20, "withdraw_fee_discount_pct": 30, "repair_discount_pct": 10,
                                "welcome_bonus_city": 2000, "city_pass_premium": True, "arcade_extra_attempts": 2,
                                "arcade_xp_bonus_pct": 15, "badge": True}}]
            c.put("/api/admin/founder-pass/settings", json={"enabled": True, "visibility": "whitelist", "allowed": "",
                                                           "tiers": tiers, "cap_pct": 300, "contact": "@mgr"})
            assert c.get("/api/founder-pass").json()["visible"] is False
            c.put("/api/admin/founder-pass/settings", json={"allowed": f"@{uname.upper()}\nsomeone"})
            v = c.get("/api/founder-pass").json()
            assert v["visible"] is True and v["contact_url"] == "https://t.me/mgr"
            assert v["tiers"][0]["max_payout"] == 600 and v["tiers"][0]["slots_left"] == 1
            assert v["currency"] == "TON" and v["tiers"][0]["perks"]["withdraw_fee_discount_pct"] == 30
            assert not v.get("my_perks")

            # not enough REAL money (the bonus balance does not count) → 402 with the missing amount
            c.portal.call(db.users.update_one, {"id": uid}, {"$set": {"bonus_balance": 500.0}})
            r = c.post("/api/founder-pass/buy", json={"tier_id": "t1"})
            assert r.status_code == 402, r.text
            d = r.json()["detail"]
            assert d["code"] == "fp_insufficient" and abs(d["missing"] - 199.0) < 1e-9
            c.portal.call(db.users.update_one, {"id": uid}, {"$set": {"bonus_balance": 0.0, "balance_ton": 250.0}})

            # buy → paid from the real balance, share with frozen terms, the plan is sold out
            r = c.post("/api/founder-pass/buy", json={"tier_id": "t1"})
            assert r.status_code == 200, r.text
            hid = r.json()["holding"]["id"]
            u = c.portal.call(db.users.find_one, {"id": uid})
            assert abs(float(u["balance_ton"]) - 50.0) < 1e-9 and u["investor"]["active"] is True and not u.get("fp_buying")
            assert c.post("/api/founder-pass/buy", json={"tier_id": "t1"}).status_code == 400
            v = c.get("/api/founder-pass").json()
            assert v["tiers"][0]["sold_out"] is True and v["holdings"][0]["max_payout"] == 600
            tx = c.portal.call(db.transactions.find_one, {"user_id": uid, "tx_type": "founder_pass_purchase"})
            assert tx and tx["amount_ton"] == 200
            led = c.portal.call(db.platform_ledger.find_one, {"user_id": uid, "kind": "founder_pass_sale"})
            assert led and led["real_ton"] == 200 and led["external"] is False

            # perks: active right away, welcome bonus paid once, investor badge, buffs for tax / withdrawal / repair
            import founder_pass
            v = c.get("/api/founder-pass").json()
            assert v["my_perks"]["active"] is True and v["my_perks"]["sale_tax_discount_pct"] == 20
            u = c.portal.call(db.users.find_one, {"id": uid})
            assert abs(float(u.get("bonus_balance", 0)) - 2.0) < 1e-9
            assert c.get("/api/profile/card").json()["investor"] is True
            buffs = {b["effect"]["type"]: b["effect"]["value"] for b in founder_pass.perk_buffs(v["my_perks"])}
            assert abs(buffs["trade_fee_multiplier"] - 0.8) < 1e-9
            assert abs(buffs["withdrawal_fee_multiplier"] - 0.7) < 1e-9
            assert abs(buffs["repair_cost_multiplier"] - 0.9) < 1e-9

            # changing the plan later does not change the share (price), perks follow the live plan
            c.put("/api/admin/founder-pass/settings", json={"tiers": [{**tiers[0], "price": 999}]})
            assert c.get("/api/founder-pass").json()["holdings"][0]["price"] == 200

            # payouts go to the REAL balance + history entry «from the administration»; never above the cap
            r = c.post(f"/api/admin/founder-pass/holdings/{hid}/payout", json={"amount": 250, "note": "Q1"})
            assert r.status_code == 200, r.text
            u = c.portal.call(db.users.find_one, {"id": uid})
            assert abs(float(u["balance_ton"]) - 300.0) < 1e-9
            tx = c.portal.call(db.transactions.find_one, {"user_id": uid, "tx_type": "founder_payout"})
            assert tx["amount_ton"] == 250 and tx["from_address"] == "Администрация" and "администрации" in tx["description"]
            assert c.post(f"/api/admin/founder-pass/holdings/{hid}/payout", json={"amount": 351}).status_code == 400
            r = c.post(f"/api/admin/founder-pass/holdings/{hid}/payout", json={"amount": 350}).json()
            assert r["paid_total"] == 600 and r["status"] == "completed"
            out = c.portal.call(lambda: db.platform_ledger.find({"user_id": uid, "kind": "founder_payout"}).to_list(10))
            assert round(sum(x["ton"] for x in out), 6) == 600
            # cap reached → still a founder, every perk keeps working
            v = c.get("/api/founder-pass").json()
            assert v["my_perks"]["active"] is True and v["my_perks"]["arcade_extra_attempts"] == 2
            assert c.get("/api/profile/card").json()["investor"] is True

            # admin list of investors + full card
            lst = c.get("/api/admin/founder-pass/investors", params={"q": uname}).json()
            assert lst["count"] == 1 and lst["items"][0]["founder"] is True and lst["items"][0]["invested"] == 200
            card = c.get(f"/api/admin/founder-pass/investors/{uid}").json()
            assert card["summary"]["paid"] == 600 and "hashed_password" not in card["user"]
            assert any(t["tx_type"] == "founder_payout" for t in card["transactions"])

            # bought back → no longer a founder → perks stop
            c.post(f"/api/admin/founder-pass/holdings/{hid}/status", json={"status": "bought_out"})
            assert not c.get("/api/founder-pass").json().get("my_perks")
            assert c.get("/api/profile/card").json()["investor"] is False
            assert c.portal.call(db.users.find_one, {"id": uid})["investor"]["active"] is False

            # a player with a share keeps seeing the pool even when it is switched off
            c.put("/api/admin/founder-pass/settings", json={"enabled": False})
            assert c.get("/api/founder-pass").json()["visible"] is True
        finally:
            c.portal.call(db.users.delete_one, {"id": uid})
            c.portal.call(db.founder_pass_applications.delete_many, {"user_id": uid})
            c.portal.call(db.founder_pass_holdings.delete_many, {"user_id": uid})
            c.portal.call(db.transactions.delete_many, {"user_id": uid})
            c.portal.call(db.platform_ledger.delete_many, {"user_id": uid})
            keep = {k: orig[k] for k in ("enabled", "visibility", "allowed", "contact", "currency", "cap_pct", "note", "tiers")}
            keep["tiers"] = [{k: t[k] for k in ("id", "name", "price", "share_pct", "slots_total", "slots_taken_manual", "badge", "active", "perks") if k in t} for t in keep["tiers"]]
            c.put("/api/admin/founder-pass/settings", json=keep)
