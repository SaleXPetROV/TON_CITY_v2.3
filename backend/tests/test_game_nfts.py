"""NFT of every game: off by default (points only); the admin adds NFTs to a game (picture / GIF / video, quantity
+/−); the chest of a good game comes only after EVERY ad of the game's reward and then holds a 1/9 piece for sure."""
import io
import os
import sys
import uuid
from datetime import timedelta
from types import SimpleNamespace

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, _BACKEND_DIR)

import arcade  # noqa: E402
import game_nfts  # noqa: E402
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
    admin = SimpleNamespace(id="gn-test-admin", username="gnadmin", is_admin=True)
    app = FastAPI()
    app.include_router(arcade.create_arcade_router(db, lambda: state["user"], lambda: admin))
    app.include_router(games_hub.create_games_hub_router(db, lambda: state["user"]))
    app.include_router(mg.create_minigames_router(db, lambda: state["user"], lambda: admin, None))
    app.include_router(mrr.create_minigame_rewards_router(db, lambda: state["user"], lambda: admin, mg.get_config))
    app.include_router(game_nfts.create_game_nfts_router(db, lambda: state["user"], lambda: admin))
    return TestClient(app), db, state


def _png():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (300, 300), (200, 120, 40)).save(b, "PNG")
    return b.getvalue()


def test_game_nft_flow():
    c, db, state = _setup()
    uid = f"gn-test-{uuid.uuid4().hex[:8]}"
    with c:
        call = c.portal.call
        orig = {t: call(db.admin_settings.find_one, {"type": t}, {"_id": 0}) for t in ("arcade", "ads", "minigame_event", "game_nfts")}
        made_nfts = []
        try:
            call(mr.seed_defaults, db)
            call(db.users.insert_one, {"id": uid, "username": "gnuser", "wallet_address": "EQ_test"})
            state["user"] = SimpleNamespace(id=uid, username="gnuser", is_admin=False)
            call(db.admin_settings.update_one, {"type": "ads"}, {"$set": {"type": "ads", "enabled": False}}, True)
            call(db.admin_settings.update_one, {"type": "minigame_event"},
                 {"$set": {"type": "minigame_event", "chests_per_day": 50, "chest_container_id": "c_sorter",
                           "arcade_chest_score": {"snake": 100}}}, True)
            call(db.admin_settings.delete_one, {"type": "game_nfts"})
            c.put("/api/admin/arcade", json={"enabled": True, "one_ad_max_xp": 0, "games": {"snake": {"enabled": True, "attempts_max": 20, "target_score": 400}}})

            def play(score):
                s = c.post("/api/arcade/snake/start", json={"difficulty": "normal"}).json()
                call(db.arcade_sessions.update_one, {"id": s["session_id"]},
                     {"$set": {"created_at": (arcade._now() - timedelta(seconds=40)).isoformat()}})
                return c.post(f"/api/arcade/session/{s['session_id']}/finish",
                              json={"score": score, "duration_ms": 39000, "stats": {"food": score // 10}}).json()

            # NFT off (the default), ads off: points only — the chest at once, no piece
            r = play(150)
            assert r["promo"]["total_points"] == 150 and r["promo"]["chest"]["given"] and not r["promo"]["chest"].get("nft_piece")
            t = c.get("/api/games/snake/nft-track").json()
            assert t["enabled"] is False and t["total_points"] == 150 and "milestones" not in t

            # the admin: two NFTs in «Змейка» (picture cut into 9), quantity 3 each
            up = c.post("/api/admin/game-nfts/upload", files={"file": ("a.png", _png(), "image/png")}).json()
            assert up["media_type"] == "image" and up["media_url"] == up["image_url"]
            v = c.post("/api/admin/game-nfts/snake/nfts", json={"name": "Змея", **up, "supply_total": 3}).json()
            v = c.post("/api/admin/game-nfts/snake/nfts", json={"name": "Удав", **up, "supply_total": 3}).json()
            g = next(x for x in v["games"] if x["game"] == "snake")
            assert len(g["nfts"]) == 2 and all(n["supply_total"] == 3 for n in g["nfts"])
            made_nfts = [(n["puzzle_id"], n["nft_id"]) for n in g["nfts"]]
            c.put("/api/admin/game-nfts/snake", json={"enabled": True})

            # ads off: the reward is done at once → the chest at once, with a piece (100 %)
            r = play(200)
            p = r["promo"]
            assert p["chest"]["given"] and p["chest"]["nft_piece"]
            assert any(x.get("kind") == "puzzle" for x in (p["chest"].get("chest") or {}).get("results") or [])

            # ads on: a good game → the chest waits; one ad → still no chest; every ad → the chest with a piece
            call(db.admin_settings.update_one, {"type": "ads"}, {"$set": {"enabled": True, "monetag_zone_id": "123",
                                                                         "daily_ads_required": 2, "min_gap_sec": 0,
                                                                         "verify_postback": False, "ads_order": "monetag"}})
            r = play(400)
            rw = r["reward"]
            assert r["promo"]["chest"]["reason"] == "watch_ads" and not r["promo"]["chest"]["given"]
            assert rw["ads_total"] >= 2 and rw["chest"]["state"] == "pending"

            def watch():
                s_ = c.post(f"/api/arcade/reward/{rw['id']}/ad/start").json()
                return c.post(f"/api/arcade/reward/{rw['id']}/ad/watched", json={"ymid": s_["ymid"]}).json()
            x = watch()
            assert x["status"] == "pending" and x["chest"]["state"] == "pending"
            for _ in range(rw["ads_total"] - 1):
                x = watch()
            assert x["status"] == "done" and x["chest"]["state"] == "given" and x["chest"]["nft_piece"]
            assert x["chest"]["chest"]["results"]
            again = c.get(f"/api/arcade/reward/{rw['id']}").json()        # given once
            assert again["chest"]["state"] == "given"
            assert call(db.mg_user_containers.count_documents, {"user_id": uid, "source": "game"}) == 3
            t = c.get("/api/games/snake/nft-track").json()
            assert t["enabled"] and sum(n["have"] for n in t["nfts"]) == 2
            assert t["nfts"][0]["ghost_url"] and t["nfts"][0]["image_url"] and t["nfts"][0]["media_type"] == "image"
            assert t["chests"]["after_ads"] is True
            hub = c.get("/api/games/hub").json()
            assert next(x for x in hub["games"] if x["id"] == "snake")["nft"] == {"have": 2, "total": 18}

            # a low score: no chest, the reward has none waiting
            r = play(10)
            assert r["promo"]["chest"]["reason"] == "low_score"

            # quantity +/−: never below what players already collect
            nid = made_nfts[0][1]
            started = next(n for n in t["nfts"] if n["nft_id"] == nid)["collecting"]
            if started:
                assert c.put(f"/api/admin/game-nfts/supply/{nid}", json={"supply_total": started - 1 if started > 1 else 0}).status_code == 400
            assert c.put(f"/api/admin/game-nfts/supply/{nid}", json={"supply_total": 10}).status_code == 200
            # take an NFT out of the game
            v = c.delete(f"/api/admin/game-nfts/snake/nfts/{made_nfts[1][0]}").json()
            assert len(next(x for x in v["games"] if x["game"] == "snake")["nfts"]) == 1
        finally:
            for t, d in orig.items():
                call(db.admin_settings.delete_one, {"type": t})
                if d:
                    call(db.admin_settings.insert_one, {**d, "type": t})
            for pid, nid in made_nfts:
                call(db.mg_puzzles.delete_many, {"id": pid})
                call(db.mg_nfts.delete_many, {"id": nid})
                call(db.mg_user_puzzles.delete_many, {"puzzle_id": pid})
            call(db.users.delete_many, {"id": uid})
            for coll in ("arcade_sessions", "arcade_rewards", "arcade_attempts", "mg_user_containers", "mg_user_rewards",
                         "mg_chest_days", "mg_user_puzzles", "mg_user_boosters", "transactions"):
                call(db[coll].delete_many, {"user_id": uid})
            call(db.minigame_points.delete_many, {"user_id": uid})
            call(db.city_pass_progress.delete_many, {"user_id": uid})


def test_nft_media_upload(tmp_path):
    """A picture, an animated GIF, a video (mp4: a poster by ffmpeg or the admin's frame) — and what is refused."""
    import shutil
    import subprocess
    from PIL import Image
    c, db, state = _setup()
    made = []
    with c:
        try:
            frames = [Image.new("RGB", (120, 120), col) for col in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
            b = io.BytesIO()
            frames[0].save(b, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
            r = c.post("/api/admin/game-nfts/upload", files={"file": ("a.gif", b.getvalue(), "image/gif")}).json()
            made += [r["media_url"], r["image_url"]]
            assert r["media_type"] == "gif" and r["media_url"].endswith(".gif") and r["image_url"].endswith(".webp")
            assert c.get(r["media_url"]).status_code == 200
            if shutil.which("ffmpeg"):
                mp4 = tmp_path / "v.mp4"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x160:rate=10",
                                "-t", "1", "-pix_fmt", "yuv420p", str(mp4)], check=True)
                r = c.post("/api/admin/game-nfts/upload", files={"file": ("v.mp4", mp4.read_bytes(), "video/mp4")}).json()
                made += [r["media_url"], r["image_url"]]
                assert r["media_type"] == "video" and r["media_url"].endswith(".mp4") and r["image_url"].endswith(".webp")
                rg = c.get(r["media_url"], headers={"Range": "bytes=0-99"})
                assert rg.status_code == 206 and len(rg.content) == 100          # iOS plays only with Range
                r = c.post("/api/admin/game-nfts/upload", files={"file": ("v.mp4", mp4.read_bytes(), "video/mp4"),
                                                                 "poster": ("p.png", _png(), "image/png")}).json()
                made += [r["media_url"], r["image_url"]]
                assert r["media_type"] == "video"
            assert c.post("/api/admin/game-nfts/upload", files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 400
        finally:
            for u in made:
                (mrr.img_dir() / u.rsplit("/", 1)[-1]).unlink(missing_ok=True)
