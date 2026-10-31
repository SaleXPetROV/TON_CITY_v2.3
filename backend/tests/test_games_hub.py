"""«Игры» (no promotion): an Arcade game gives the mini-games rewards — its own weekly list of leaders, a chest for a
good game (the daily chest limit is shared with the Sorter), threshold rewards of that game, prizes when the week ends."""
import os
import sys
import uuid
from datetime import timedelta
from types import SimpleNamespace

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)

import arcade  # noqa: E402
import games_hub  # noqa: E402
import minigame_rewards as mr  # noqa: E402
import minigame_rewards_routes as mrr  # noqa: E402
import minigames as mg  # noqa: E402


def _setup():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from motor.motor_asyncio import AsyncIOMotorClient
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    state = {"user": None}
    admin = SimpleNamespace(id="gh-test-admin", username="ghadmin", is_admin=True)
    app = FastAPI()
    app.include_router(arcade.create_arcade_router(db, lambda: state["user"], lambda: admin))
    app.include_router(games_hub.create_games_hub_router(db, lambda: state["user"]))
    app.include_router(mg.create_minigames_router(db, lambda: state["user"], lambda: admin, None))
    app.include_router(mrr.create_minigame_rewards_router(db, lambda: state["user"], lambda: admin, mg.get_config))
    return TestClient(app), db, state


def test_board_ids_and_prizes():
    from datetime import datetime, timezone
    now = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)                     # a Wednesday
    assert games_hub.week_id(now) == "w2026-10-26"
    assert games_hub.week_ends_at(now).startswith("2026-11-02T00:00:00")
    assert games_hub.board_id("snake", "w2026-10-26") == "w2026-10-26:snake"
    assert games_hub.week_id(datetime(2026, 11, 1, 21, 30, tzinfo=timezone.utc)) == "w2026-11-02"   # Monday 00:30 MSK
    cfg = {"leaderboard_prizes": [{"from": 1, "to": 1, "kind": "city", "city": 1}], "arcade_prizes": {"snake": []}}
    assert games_hub.prizes_for(cfg, "sorter") == cfg["leaderboard_prizes"]
    assert games_hub.prizes_for(cfg, "snake") == []
    assert games_hub.prizes_for(cfg, "shooter") == games_hub.DEFAULT_ARCADE_PRIZES
    acfg = arcade._clean({})
    assert games_hub.chest_score({}, acfg, "snake") == acfg["games"]["snake"]["target_score"]
    assert games_hub.chest_score({"arcade_chest_score": {"snake": 77}}, acfg, "snake") == 77
    assert set(games_hub.all_games()) == {"sorter", *arcade.GAMES}


def test_arcade_game_feeds_promotion():
    c, db, state = _setup()
    uid = f"gh-test-{uuid.uuid4().hex[:8]}"
    rival = f"gh-test-{uuid.uuid4().hex[:8]}"
    with c:
        call = c.portal.call
        orig = {t: call(db.admin_settings.find_one, {"type": t}, {"_id": 0}) for t in ("arcade", "ads", "minigame_event")}
        ev = f"gh_ev_{uuid.uuid4().hex[:6]}"
        try:
            call(mr.seed_defaults, db)
            call(db.users.insert_many, [{"id": uid, "username": "ghuser"}, {"id": rival, "username": "ghrival"}])
            state["user"] = SimpleNamespace(id=uid, username="ghuser", is_admin=False)
            # games on; ads off (XP credited at once); snake: chest from 300 points
            call(db.admin_settings.update_one, {"type": "minigame_event"},
                 {"$set": {"type": "minigame_event", "chests_per_day": 4, "chest_container_id": "c_sorter",
                           "arcade_chest_score": {"snake": 300},
                           "arcade_prizes": {"snake": [{"from": 1, "to": 1, "kind": "city", "city": 2000}]}}}, True)
            call(db.minigame_points.delete_many, {"campaign_id": games_hub.board_id("snake")})
            call(db.admin_settings.update_one, {"type": "ads"}, {"$set": {"type": "ads", "enabled": False}}, True)
            c.put("/api/admin/arcade", json={"enabled": True, "games": {"snake": {"enabled": True, "attempts_max": 5,
                                                                                    "target_score": 400}}})
            call(db.mg_rewards.delete_many, {"game": "snake", "code": {"$regex": "^ghtest"}})
            call(db.mg_rewards.insert_one, {"id": f"r_ghtest_{ev}", "code": f"ghtest_{ev}", "game": "snake", "category": "points",
                                            "threshold": 500, "type": "container", "container_id": "c_sorter", "name": "t",
                                            "is_active": True})

            def play(score):
                s = c.post("/api/arcade/snake/start", json={"difficulty": "normal"}).json()
                call(db.arcade_sessions.update_one, {"id": s["session_id"]},
                     {"$set": {"created_at": (arcade._now() - timedelta(seconds=40)).isoformat()}})
                return c.post(f"/api/arcade/session/{s['session_id']}/finish",
                              json={"score": score, "duration_ms": 39000, "stats": {"food": score // 10}}).json()

            r1 = play(200)
            assert r1["ok"], r1
            p = r1["promo"]
            assert p["counted"] and p["campaign_points"] == 200 and p["chest"]["reason"] == "low_score" and p["place"] == 1
            r2 = play(350)
            p = r2["promo"]
            assert p["campaign_points"] == 550 and p["chest"]["given"] and len(p["opened_chests"]) == 2   # game chest + 500-points reward
            assert [n["id"] for n in p["new_rewards"]] == [f"r_ghtest_{ev}"]
            # the board is the game's own, the Sorter's is untouched
            lb = c.get("/api/minigames/leaderboard?game=snake").json()
            assert lb["game"] == "snake" and lb["rows"][0]["user_id"] == uid and lb["rows"][0]["points"] == 550
            assert lb["prizes"][0]["city"] == 2000
            assert all(r["user_id"] != uid for r in c.get("/api/minigames/leaderboard").json()["rows"])
            # the hub shows my place and record per game
            assert c.get("/api/games/config").json() == {"button_enabled": True}
            hub = c.get("/api/games/hub").json()
            snake = next(g for g in hub["games"] if g["id"] == "snake")
            assert snake["points"] == 550 and snake["place"] == 1 and snake["best"] == 350 and snake["chest_score"] == 300
            assert hub["games"][0]["id"] == "sorter" and hub["chests_today"] >= 1
            # rewards page of the game
            me = c.get("/api/minigames/rewards/me?game=snake").json()
            assert me["game"] == "snake" and me["campaign_points"] == 550 and me["best_score"] == 350
            assert any(r["id"] == f"r_ghtest_{ev}" and r["given"] for r in me["rewards"])
            assert all(r["game"] == "snake" for r in me["rewards"])
            # a rival with more points; when the week is over the snake prize goes to the rival only, once
            call(mr.add_points, db, rival, games_hub.board_id("snake"), 900)
            bal = float((call(db.users.find_one, {"id": rival}, {"_id": 0, "bonus_balance": 1}) or {}).get("bonus_balance") or 0)
            later = arcade._now() + timedelta(days=8)
            week = games_hub.week_id()
            call(db.mg_campaigns.delete_many, {"id": f"week:{week}"})
            res = call(games_hub.finalize_weeks, db, later)
            assert res["awarded"] >= 1
            rec = call(db.mg_campaigns.find_one, {"id": f"week:{week}"}, {"_id": 0})
            got = [x for x in rec["prizes_given"] if x["game"] == "snake"]
            assert [x["user_id"] for x in got] == [rival]
            nb = float(call(db.users.find_one, {"id": rival}, {"_id": 0, "bonus_balance": 1})["bonus_balance"])
            assert abs(nb - bal - 2.0) < 1e-6
            assert call(games_hub.finalize_weeks, db, later)["awarded"] == 0          # only once
            call(db.mg_campaigns.delete_many, {"id": f"week:{week}"})
            # the games switched off → no points / chests
            c.put("/api/admin/arcade", json={"enabled": False})
            assert c.get("/api/games/config").json() == {"button_enabled": False}
        finally:
            for t, d in orig.items():
                call(db.admin_settings.delete_one, {"type": t})
                if d:
                    call(db.admin_settings.insert_one, {**d, "type": t})
            for coll in ("users",):
                call(db[coll].delete_many, {"id": {"$in": [uid, rival]}})
            for coll in ("arcade_sessions", "arcade_rewards", "arcade_attempts", "mg_user_containers", "mg_user_rewards",
                         "mg_chest_days", "mg_user_puzzles", "mg_user_boosters"):
                call(db[coll].delete_many, {"user_id": {"$in": [uid, rival]}})
            call(db.minigame_points.delete_many, {"user_id": {"$in": [uid, rival]}})
            call(db.city_pass_progress.delete_many, {"user_id": {"$in": [uid, rival]}})
            call(db.mg_rewards.delete_many, {"code": {"$regex": "^ghtest"}})
            call(db.minigame_points.delete_many, {"campaign_id": games_hub.board_id("snake")})
            call(db.transactions.delete_many, {"user_id": {"$in": [uid, rival]}})
