"""Arcade: attempts per day, server score checks, XP by difficulty, reward unlocked by ads 2/4 + 1/4 + 1/4, preview."""
import os
import sys
import time
import uuid
from types import SimpleNamespace

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)

import arcade  # noqa: E402


def test_pure_helpers():
    cfg = arcade._clean({})
    assert cfg["ad_shares_pct"] == [50, 25, 25]
    assert arcade.unlocked_xp(20, [50, 25, 25], 0) == 0
    assert arcade.unlocked_xp(20, [50, 25, 25], 1) == 10
    assert arcade.unlocked_xp(20, [50, 25, 25], 2) == 15
    assert arcade.unlocked_xp(21, [50, 25, 25], 3) == 21
    # XP of the difficulty × score / target, capped at the target (the game score itself has no maximum)
    g = cfg["games"]["shooter"]
    assert arcade.game_xp(cfg, "shooter", "hard", g["target_score"] * 5) == g["diffs"]["hard"]["xp"]
    assert arcade.game_xp(cfg, "shooter", "hard", g["target_score"] // 2) == g["diffs"]["hard"]["xp"] // 2
    assert arcade.game_xp(cfg, "shooter", "easy", g["target_score"]) == g["diffs"]["easy"]["xp"]
    assert arcade.game_xp(cfg, "shooter", "hard", g["target_score"], bonus_pct=10) == int(g["diffs"]["hard"]["xp"] * 1.1)
    # paid attempts come back one by one
    from datetime import timedelta
    now = arcade._now()
    v = arcade.attempts_view({"left": 0, "at": (now - timedelta(minutes=250)).isoformat()}, 4, 120, now)
    assert v["left"] == 2 and v["next_at"] is not None
    assert abs((v["next_at"] - now).total_seconds() - 110 * 60) < 2
    assert arcade.attempts_view({"left": 1, "at": (now - timedelta(days=2)).isoformat()}, 4, 120, now)["left"] == 4
    assert arcade.attempts_view(None, 4, 120, now) == {"left": 4, "max": 4, "at": now, "next_at": None}
    # shares always add up to 100
    assert sum(arcade._clean({"ad_shares_pct": [10, 10, 10]})["ad_shares_pct"]) == 100
    # tic-tac-toe replay
    assert arcade._ttt_result([0, 3, 1, 4, 2], "p") == "win"
    assert arcade._ttt_result([0, 0], "p") is None
    assert arcade._ttt_result([4, 0, 1, 7, 2, 6, 3, 5, 8], "ai") == "draw"
    assert arcade._ttt_result([0, 3, 1, 4, 2, 5], "p") is None                 # a move after the win
    assert arcade._ttt_result([0, 3], "p", allow_open=True) == "open"
    # tic-tac-toe has no round limit: until 3 losses; a streak of wins pays more; the last round may be cut by the clock
    win_p = {"moves": [0, 3, 1, 4, 2]}                 # player starts and wins
    win_ai_first = {"moves": [8, 0, 4, 1, 6, 2]}       # ai starts at 8 … then the player completes 0,1,2
    assert arcade._ttt_result(win_ai_first["moves"], "ai") == "win"
    rounds = [win_p, win_ai_first, win_p, win_ai_first, win_p, win_ai_first, {"moves": [4]}]
    # 100 + 125 + 150 + 175 + 200 + 200, the 7th round is unfinished
    assert arcade._tictac_score(rounds) == 950
    loss_p = {"moves": [0, 3, 1, 4, 8, 5]}             # player starts, ai completes 3,4,5
    loss_ai = {"moves": [3, 0, 4, 1, 5]}               # ai starts and completes 3,4,5
    assert arcade._tictac_score([loss_p, loss_ai, loss_p]) == 0
    assert arcade._tictac_score([loss_p, loss_ai, loss_p, win_ai_first]) is None   # nothing after the 3rd loss
    assert arcade._tictac_score([win_p, {"moves": [4]}, win_p]) is None              # only the last round may be open


def test_math_replay():
    qs = arcade.math_questions(4242, "normal", 30)
    answers = [{"a": q["ans"], "t": 600 * (i + 1)} for i, q in enumerate(qs)]
    s = arcade._math_score(4242, "normal", answers)
    assert s and s > 300
    wrong = [{"a": q["ans"] + 1, "t": 600 * (i + 1)} for i, q in enumerate(qs)]
    assert arcade._math_score(4242, "normal", wrong) == 0
    too_fast = [{"a": q["ans"], "t": 10 * (i + 1)} for i, q in enumerate(qs)]
    assert arcade._math_score(4242, "normal", too_fast) is None


def test_score_checks():
    ok = arcade.check_score("shooter", "normal", 1, {"score": 1500, "duration_ms": 30000}, 31)
    assert ok["ok"] and ok["score"] == 1500
    assert arcade.check_score("shooter", "normal", 1, {"score": 1500, "duration_ms": 30000}, 10)["reason"] == "time"
    assert arcade.check_score("shooter", "normal", 1, {"score": 900000, "duration_ms": 30000}, 31)["reason"] == "rate"
    assert arcade.check_score("snake", "normal", 1, {"duration_ms": 20000, "stats": {"food": 12}}, 21)["score"] == 120
    assert not arcade.check_score("memory", "normal", 1, {"duration_ms": 20000, "stats": {"pairs": 99, "moves": 99}}, 21)["ok"]
    # «Память»: no score limit — 2 full boards of 8 pairs + 3 more pairs in 60 s
    m = arcade.check_score("memory", "normal", 1, {"duration_ms": 60000, "stats": {"pairs": 19, "moves": 25, "boards": 2,
                                                                                  "combo_bonus": 300}}, 61)
    assert m["ok"] and m["score"] == 19 * 50 + 2 * 100 + 300
    assert not arcade.check_score("memory", "normal", 1, {"duration_ms": 60000, "stats": {"pairs": 10, "moves": 12, "boards": 2,
                                                                                         "combo_bonus": 0}}, 61)["ok"]


def _setup():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from motor.motor_asyncio import AsyncIOMotorClient
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    state = {"user": None}
    admin = SimpleNamespace(id="arc-test-admin", username="arcadmin", is_admin=True)
    app = FastAPI()
    app.include_router(arcade.create_arcade_router(db, lambda: state["user"], lambda: admin))
    return TestClient(app), db, state


def test_arcade_flow():
    c, db, state = _setup()
    uid = f"arc-test-{uuid.uuid4().hex[:8]}"
    with c:
        orig_arc = c.portal.call(db.admin_settings.find_one, {"type": "arcade"}, {"_id": 0})
        orig_ads = c.portal.call(db.admin_settings.find_one, {"type": "ads"}, {"_id": 0})
        try:
            c.portal.call(db.users.insert_one, {"id": uid, "username": "arcuser"})
            player = SimpleNamespace(id=uid, username="arcuser", is_admin=False)
            state["user"] = player

            # switched off → players don't see it, admins do (preview)
            c.put("/api/admin/arcade", json={"enabled": False})
            assert c.get("/api/arcade").json() == {"visible": False}
            assert c.post("/api/arcade/shooter/start", json={}).status_code == 403
            state["user"] = SimpleNamespace(id=uid, username="arcuser", is_admin=True)
            hub = c.get("/api/arcade?preview=true").json()
            assert hub["visible"] and hub["preview_only"] and len(hub["games"]) == len(arcade.GAMES)
            s = c.post("/api/arcade/snake/start", json={"preview": True, "difficulty": "hard"}).json()
            assert s["preview"] is True
            state["user"] = player

            # on, 2 attempts of shooter; ads on with three ads per reward
            c.put("/api/admin/arcade", json={"enabled": True, "one_ad_max_xp": 10,
                                             "games": {"shooter": {"attempts_max": 2, "regen_minutes": 120, "target_score": 1000,
                                                                   "diffs": {"hard": {"xp": 20}}}}})
            c.portal.call(db.admin_settings.update_one, {"type": "ads"},
                          {"$set": {"type": "ads", "enabled": True, "monetag_zone_id": "123", "daily_ads_required": 1,
                                    "min_gap_sec": 0, "verify_postback": False, "require_valued": False}}, True)
            s = c.post("/api/arcade/shooter/start", json={"difficulty": "hard"}).json()
            c.portal.call(db.arcade_sessions.update_one, {"id": s["session_id"]},
                          {"$set": {"created_at": arcade._now().replace(microsecond=0).isoformat()}})
            time.sleep(0.01)
            # pretend the game lasted 20 s on the server clock
            from datetime import timedelta
            c.portal.call(db.arcade_sessions.update_one, {"id": s["session_id"]},
                          {"$set": {"created_at": (arcade._now() - timedelta(seconds=21)).isoformat()}})
            r = c.post(f"/api/arcade/session/{s['session_id']}/finish", json={"score": 1000, "duration_ms": 20000}).json()
            assert r["ok"] and r["xp"] == 20 and r["attempts_left"] == 1
            rw = r["reward"]
            assert rw["xp_unlocked"] == 0 and rw["ads_total"] == 3 and rw["next_xp"] == 10
            # a finished session can't be sent twice
            assert c.post(f"/api/arcade/session/{s['session_id']}/finish", json={"score": 1}).status_code == 404

            # no ad watched for the last game → the next game can't start
            blocked = c.post("/api/arcade/shooter/start", json={})
            assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "arcade_watch_first"
            assert blocked.json()["detail"]["reward_id"] == rw["id"]

            got = []
            for _ in range(3):
                a = c.post(f"/api/arcade/reward/{rw['id']}/ad/start").json()
                x = c.post(f"/api/arcade/reward/{rw['id']}/ad/watched", json={"ymid": a["ymid"]}).json()
                got.append(x["xp_unlocked"])
            assert got == [10, 15, 20]
            assert x["status"] == "done"
            # foreign / reused ymid is ignored, simulate is only for previews
            assert c.post(f"/api/arcade/reward/{rw['id']}/ad/start").status_code == 409

            # top 5 by the best single game; my place
            top = c.get("/api/arcade/shooter/top").json()
            assert top["me"]["score"] == 1000 and any(x["me"] for x in top["rows"])

            # second attempt: a small result → one ad for everything; then no attempts left
            s2 = c.post("/api/arcade/shooter/start", json={"difficulty": "hard"}).json()
            c.portal.call(db.arcade_sessions.update_one, {"id": s2["session_id"]},
                          {"$set": {"created_at": (arcade._now() - timedelta(seconds=21)).isoformat()}})
            r2 = c.post(f"/api/arcade/session/{s2['session_id']}/finish", json={"score": 300, "duration_ms": 20000}).json()
            assert r2["xp"] == 6 and r2["reward"]["ads_total"] == 1 and r2["reward"]["next_xp"] == 6
            a2 = c.post(f"/api/arcade/reward/{r2['reward']['id']}/ad/start").json()
            assert c.post(f"/api/arcade/reward/{r2['reward']['id']}/ad/watched", json={"ymid": a2["ymid"]}).json()["xp_unlocked"] == 6
            assert c.post("/api/arcade/shooter/start", json={}).json()["detail"] == "arcade_no_attempts"
            hub = c.get("/api/arcade").json()
            sh = next(x for x in hub["games"] if x["id"] == "shooter")
            assert sh["attempts_left"] == 0 and sh["next_attempt_at"]
            # «Играть просто так»: no reward, but the record counts
            sf = c.post("/api/arcade/shooter/start", json={"free": True, "difficulty": "hard"}).json()
            assert sf["free"] is True
            c.portal.call(db.arcade_sessions.update_one, {"id": sf["session_id"]},
                          {"$set": {"created_at": (arcade._now() - timedelta(seconds=40)).isoformat()}})
            rf = c.post(f"/api/arcade/session/{sf['session_id']}/finish", json={"score": 5000, "duration_ms": 39000}).json()
            assert rf["ok"] and rf["xp"] == 0 and rf["reward"] is None and rf["free"]
            assert c.get("/api/arcade/shooter/top").json()["me"]["score"] == 5000

            # «Выйти» → the run does not count
            c.put("/api/admin/arcade", json={"games": {"snake": {"attempts_max": 5}}})
            s4 = c.post("/api/arcade/snake/start", json={}).json()
            assert c.post(f"/api/arcade/session/{s4['session_id']}/revive/start").status_code == 200
            assert c.post(f"/api/arcade/session/{s4['session_id']}/revive/start").status_code == 409
            r4 = c.post(f"/api/arcade/session/{s4['session_id']}/finish", json={"abandoned": True, "score": 999}).json()
            assert r4["abandoned"] and r4["xp"] == 0 and r4["reward"] is None

            # ads off → the whole reward right after the game
            c.portal.call(db.admin_settings.update_one, {"type": "ads"}, {"$set": {"enabled": False}})
            s3 = c.post("/api/arcade/snake/start", json={"difficulty": "normal"}).json()
            c.portal.call(db.arcade_sessions.update_one, {"id": s3["session_id"]},
                          {"$set": {"created_at": (arcade._now() - timedelta(seconds=30)).isoformat()}})
            r3 = c.post(f"/api/arcade/session/{s3['session_id']}/finish", json={"duration_ms": 29000, "stats": {"food": 30}}).json()
            assert r3["ok"] and r3["score"] == 300 and r3["reward"]["status"] == "done" and r3["reward"]["no_ads"]
            assert r3["reward"]["xp_unlocked"] == r3["xp"]
        finally:
            c.portal.call(db.users.delete_one, {"id": uid})
            c.portal.call(db.arcade_sessions.delete_many, {"user_id": uid})
            c.portal.call(db.arcade_rewards.delete_many, {"user_id": uid})
            c.portal.call(db.ad_views.delete_many, {"user_id": uid})
            c.portal.call(db.ad_sessions.delete_many, {"user_id": uid})
            c.portal.call(db.city_pass_progress.delete_many, {"user_id": uid})
            for typ, orig in (("arcade", orig_arc), ("ads", orig_ads)):
                c.portal.call(db.admin_settings.delete_one, {"type": typ})
                if orig:
                    c.portal.call(db.admin_settings.insert_one, orig)
