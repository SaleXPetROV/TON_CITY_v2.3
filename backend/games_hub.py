"""«Игры» — the Arcade games and the «Сортировщик» in ONE place, with the rewards of the mini-games. No promotion:
the games work whenever the admin has switched «Игры» on (admin → «Аркада», the main switch = arcade.enabled).

Every game gives (minigame_rewards.py): points of the game's WEEKLY rating, a chest for a good game (the daily chest
limit is shared by all games), threshold rewards of that game (for points of the week / for the record), puzzles,
boosters, NFT. Every game has its own list of leaders and prizes (scores of different games can't be compared):
board = `w<monday MSK>:<game>`; when the week ends (Monday 00:00 MSK) the prizes of every board are given once
(finalize_weeks, every 10 minutes). Arcade games also keep their City Pass XP unlocked by ads (arcade.py).

  GET /api/games/config                 {button_enabled} — the side button «Игры» on «Бизнесы»
  GET /api/games/hub                    the «Игры» page: week, chests today, every game with my points / place / record
  GET /api/minigames/leaderboard?game=  list of leaders of one game this week (minigames.py)
  GET /api/minigames/rewards/me?game=   rewards of one game + shared chests / puzzles (minigame_rewards_routes.py)

Admin (one tab «Аркада»): `game_prizes` {game: prizes of its weekly list of leaders} (the Sorter keeps
`leaderboard_prizes`), `arcade_chest_score` {game: score of one game for a chest; 0 = «score for max XP»}.
"""
from __future__ import annotations

import copy
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

import minigame_rewards as mr

logger = logging.getLogger(__name__)

# the top five of the week in every game (the admin can change it per game)
DEFAULT_ARCADE_PRIZES = [{"from": 1, "to": 1, "kind": "city", "city": 3000.0},
                         {"from": 2, "to": 2, "kind": "city", "city": 2000.0},
                         {"from": 3, "to": 3, "kind": "city", "city": 1500.0},
                         {"from": 4, "to": 5, "kind": "city", "city": 750.0}]


def arcade_games() -> List[str]:
    import arcade
    return list(arcade.GAMES)


def all_games() -> List[str]:
    return ["sorter", *arcade_games()]


def week_id(now=None) -> str:
    """The current rating week: «w» + the Monday (MSK) it started on."""
    from core.timeutil import msk_now, MSK
    d = (now.astimezone(MSK) if now else msk_now()).date()
    return "w" + (d - timedelta(days=d.weekday())).isoformat()


def week_ends_at(now=None) -> str:
    from datetime import datetime
    from core.timeutil import MSK
    monday = datetime.fromisoformat(week_id(now)[1:]).replace(tzinfo=MSK)
    return (monday + timedelta(days=7)).isoformat()


def board_id(game: str, week: Optional[str] = None) -> str:
    return f"{week or week_id()}:{game}"


def prizes_for(cfg: Dict[str, Any], game: str) -> List[Dict[str, Any]]:
    if game == "sorter":
        return list(cfg.get("leaderboard_prizes") or [])
    per = cfg.get("arcade_prizes") or {}
    return list(per[game]) if game in per else copy.deepcopy(DEFAULT_ARCADE_PRIZES)


def chest_score(cfg: Dict[str, Any], arcade_cfg: Dict[str, Any], game: str) -> int:
    v = int((cfg.get("arcade_chest_score") or {}).get(game) or 0)
    return v if v > 0 else int(((arcade_cfg.get("games") or {}).get(game) or {}).get("target_score") or 1000)


async def games_on(db) -> bool:
    """The main switch «Игры» (admin → «Аркада»): the button on «Бизнесы», the page and every game."""
    import arcade
    return bool((await arcade.get_config(db)).get("enabled"))


async def sorter_on(db, cfg: Optional[Dict[str, Any]] = None) -> bool:
    import minigames as mg
    cfg = cfg or await mg.get_config(db)
    return cfg.get("sorter_enabled", True) is not False and await games_on(db)


async def my_board(db, uid: str, bid: str) -> Dict[str, Any]:
    mine = await db.minigame_points.find_one({"campaign_id": bid, "user_id": uid}, {"_id": 0})
    pts = int((mine or {}).get("points") or 0)
    if pts <= 0:
        return {"points": 0, "place": None}
    ahead = await db.minigame_points.count_documents({"campaign_id": bid, "points": {"$gt": pts}})
    ties = await db.minigame_points.count_documents({"campaign_id": bid, "points": pts,
                                                     "updated_at": {"$lt": (mine or {}).get("updated_at") or ""}})
    return {"points": pts, "place": ahead + ties + 1}


async def on_arcade_finish(db, uid: str, game: str, score: int, session_id: str, ok: bool, preview: bool,
                           reward: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Mini-games rewards for one finished Arcade game (called by arcade.py after the anti-cheat check).
    The chest of a good game is NOT given here: it waits for the last ad of the game's XP reward
    (`reward` = arcade_rewards doc) — chest_after_ads. Ads off → the reward is done at once → the chest now."""
    import arcade
    import minigames as mg
    out: Dict[str, Any] = {"counted": False, "campaign_points": 0, "chest": None, "opened_chests": [], "new_rewards": []}
    if preview or not ok or score <= 0:
        return out
    cfg = await mg.get_config(db)
    best, new_best = await mr.update_game_best(db, uid, game, int(score))
    bid = board_id(game)
    pts = await mr.add_points(db, uid, bid, int(score))
    new = await mr.check_thresholds(db, uid, bid, pts, best, notify="app", game=game)
    need = chest_score(cfg, await arcade.get_config(db), game)
    nft: Dict[str, Any] = {}
    try:
        import game_nfts
        nft = await game_nfts.after_game(db, uid, game, int(score))
    except Exception as e:
        logger.warning(f"game nft after game: {e}")
    if score < need:
        chest: Dict[str, Any] = {"given": False, "reason": "low_score"}
    elif reward and reward.get("status") == "done":
        chest = await give_game_chest(db, uid, game, session_id, cfg)          # no ads to watch → at once
    elif reward:
        await db.arcade_rewards.update_one({"id": reward["id"], "chest": {"$exists": False}},
                                           {"$set": {"chest": {"state": "pending", "game": game, "score": int(score)}}})
        chest = {"given": False, "reason": "watch_ads", "pending": True, "reward_id": reward["id"]}
    else:
        import ads as _ads
        if _ads.ads_active(await _ads.get_config(db)):
            chest = {"given": False, "reason": "no_reward"}                    # a game without XP (free round) has no ads
        else:
            chest = await give_game_chest(db, uid, game, session_id, cfg)
    chest["chests_today"] = await mr.chests_today(db, uid)
    chest["chests_per_day"] = int(cfg.get("chests_per_day") or 0)
    chest["min_score"] = need
    out.update(counted=True, campaign_points=pts, best_score=best, new_best=new_best, chest=chest,
               place=(await my_board(db, uid, bid))["place"],
               opened_chests=([chest["chest"]] if chest.get("chest") else []) + [n["chest"] for n in new if n.get("chest")],
               new_rewards=[{"id": n["reward"]["id"], "type": n["reward"]["type"], "name": n["reward"]["name"],
                             "name_i18n": n["reward"].get("name_i18n")} for n in new],
               total_points=nft.get("total_points"), nft_enabled=bool(nft.get("enabled")))
    return out


async def give_game_chest(db, uid: str, game: str, session_id: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The chest of a good game (daily limit of minigame_rewards) + with NFT on — a piece of the game's NFT in it."""
    import minigames as mg
    cfg = cfg or await mg.get_config(db)
    chest = await mr.game_chest(db, uid, session_id, 99, cfg, notify="app")   # «stars» are the Sorter's: the score decided
    try:
        import game_nfts
        await game_nfts.chest_piece(db, uid, game, chest)
    except Exception as e:
        logger.warning(f"game nft chest piece: {e}")
    return chest


async def chest_after_ads(db, rw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Every ad of the reward watched → the chest that waited for it (once: claimed atomically)."""
    ch = rw.get("chest") or {}
    if ch.get("state") != "pending" or rw.get("preview"):
        return None
    res = await db.arcade_rewards.update_one({"id": rw["id"], "chest.state": "pending"}, {"$set": {"chest.state": "giving"}})
    if not res.modified_count:
        return None
    try:
        chest = await give_game_chest(db, rw["user_id"], ch.get("game") or rw.get("game"), rw.get("session_id") or rw["id"])
    except Exception as e:
        logger.warning(f"chest after ads: {e}")
        await db.arcade_rewards.update_one({"id": rw["id"]}, {"$set": {"chest.state": "pending"}})
        return None
    pub = {"state": "given" if chest.get("given") else "none", "game": ch.get("game"), "reason": chest.get("reason"),
           "chest": chest.get("chest"), "nft_piece": chest.get("nft_piece"),
           "chests_today": chest.get("chests_today"), "chests_per_day": chest.get("chests_per_day")}
    await db.arcade_rewards.update_one({"id": rw["id"]}, {"$set": {"chest": pub}})
    return pub


async def finalize_weeks(db, now=None) -> Dict[str, int]:
    """When a week is over: the prizes of every game's list of leaders, once (scheduled every 10 minutes)."""
    import minigames as mg
    cur = week_id(now)
    weeks = sorted({str(c).split(":", 1)[0] for c in await db.minigame_points.distinct("campaign_id")
                    if str(c).startswith("w") and ":" in str(c)})
    awarded = 0
    cfg = await mg.get_config(db)
    for w in weeks:
        if w >= cur:
            continue
        # claim the week atomically: prizes are given exactly once (an existing record = already done)
        try:
            claim = await db.mg_campaigns.update_one({"id": f"week:{w}"},
                                                     {"$setOnInsert": {"id": f"week:{w}", "week": w, "started_at": _now_iso()}},
                                                     upsert=True)
        except Exception:
            continue
        if not claim.upserted_id:
            continue
        given = []
        for g in all_games():
            prizes = prizes_for(cfg, g)
            last = max([int(p.get("to", 0)) for p in prizes] or [0])
            if last <= 0:
                continue
            bid = board_id(g, w)
            lb = await mr.leaderboard(db, bid, limit=last, prizes=prizes)
            for row in lb["rows"]:
                p = mr.prize_for(row["place"], prizes)
                if not p:
                    continue
                res = await mr.give_prize(db, row["user_id"], p, bid, row["place"])
                given.append({"game": g, "place": row["place"], "user_id": row["user_id"], "username": row["username"],
                              "points": row["points"], **res})
                awarded += 1
                try:
                    from core.notify import notify_user
                    await notify_user(db, row["user_id"], f"🏆 {row['place']} место в рейтинге недели!",
                                      "Приз зачислен — откройте «Игры» → «Награды».", type_key="minigame_prize")
                except Exception:
                    pass
        await db.mg_campaigns.update_one({"id": f"week:{w}"}, {"$set": {"prizes_given": given, "finished_at": _now_iso()}})
    return {"awarded": awarded}


def _now_iso() -> str:
    return mr._iso()


async def week_winners(db, cfg: Dict[str, Any], week: Optional[str] = None) -> List[Dict[str, Any]]:
    """Who would get a prize if the week ended now (admin)."""
    out = []
    for g in all_games():
        prizes = prizes_for(cfg, g)
        last = max([int(p.get("to", 0)) for p in prizes] or [0])
        if last <= 0:
            continue
        lb = await mr.leaderboard(db, board_id(g, week), limit=last, prizes=prizes)
        out += [{**row, "game": g} for row in lb["rows"] if row["prize"]]
    return out


def _arcade_seed_names(game: str) -> Dict[str, str]:
    return mr._i18n("Game chest", "Игровой сундук", "Cofre de juego", "游戏宝箱", "Coffre de jeu", "Spieltruhe",
                    "ゲームの宝箱", "게임 상자", "Peti permainan")


async def seed_arcade_rewards(db) -> int:
    """Starting threshold rewards for every Arcade game (a chest for promotion points and one for the record) —
    only for a game that has no rewards yet, so admin edits are never overwritten."""
    import arcade
    acfg = await arcade.get_config(db)
    chest = "c_sorter" if await db.mg_containers.find_one({"id": "c_sorter"}) else None
    if not chest:
        return 0
    made = 0
    for g in arcade_games():
        if await db.mg_rewards.find_one({"game": g}):
            continue
        target = int(acfg["games"][g]["target_score"] or 1000)
        names = _arcade_seed_names(g)
        now = mr._iso()
        for code, cat, th in ((f"{g}_pts_chest", "points", target * 10), (f"{g}_best_chest", "best", target * 2)):
            await db.mg_rewards.insert_one({"id": f"r_{code}", "code": code, "game": g, "category": cat, "threshold": th,
                                            "type": "container", "container_id": chest, "name": names["ru"], "name_i18n": names,
                                            "description": "", "image_url": "", "is_active": True, "created_at": now,
                                            "booster_id": None, "frame_code": None, "nft_id": None})
            made += 1
    return made


def create_games_hub_router(db, get_current_user, get_current_admin=None) -> APIRouter:
    r = APIRouter()

    @r.get("/api/games/config")
    async def public_config():
        """The side button «Игры» is shown only when the admin switched the games on («Аркада» → main switch)."""
        return {"button_enabled": await games_on(db)}

    @r.get("/api/games/hub")
    async def hub(current_user=Depends(get_current_user)):
        import arcade
        import minigames as mg
        uid = current_user.id
        is_admin = bool(getattr(current_user, "is_admin", False))
        cfg = await mg.get_config(db)
        acfg = await arcade.get_config(db)
        on = bool(acfg.get("enabled"))
        games: List[Dict[str, Any]] = []
        if on or is_admin:
            sorter_enabled = cfg.get("sorter_enabled", True) is not False
            if sorter_enabled or is_admin:
                sb = await my_board(db, uid, board_id("sorter"))
                games.append({"id": "sorter", "kind": "sorter", "playable": sorter_enabled and on,
                              "enabled": sorter_enabled, "points": sb["points"], "place": sb["place"],
                              "best": await mr.game_best(db, uid, "sorter")})
            for g in arcade_games():
                gc = acfg["games"][g]
                if not gc["enabled"] and not is_admin:
                    continue
                b = await my_board(db, uid, board_id(g))
                games.append({"id": g, "kind": "arcade", "playable": True, "enabled": gc["enabled"],
                              "points": b["points"], "place": b["place"], "best": await mr.game_best(db, uid, g),
                              "chest_score": chest_score(cfg, acfg, g)})
        try:
            import game_nfts
            nft = await game_nfts.hub_summary(db, uid)
            for g in games:
                if g["id"] in nft:
                    g["nft"] = nft[g["id"]]
        except Exception as e:
            logger.debug(f"hub nft: {e}")
        return {"enabled": on, "week": {"id": week_id(), "ends_at": week_ends_at()},
                "chests_today": await mr.chests_today(db, uid), "chests_per_day": int(cfg.get("chests_per_day") or 0),
                "games": games, "user_id": uid}

    return r


async def clean_admin_patch(db, upd: Dict[str, Any], clean_prizes) -> None:
    """Validates the Arcade part of the games settings (in place). `clean_prizes(list) -> list` is minigames.py's prize check."""
    games = set(arcade_games())
    if "arcade_rewards_enabled" in upd:
        upd["arcade_rewards_enabled"] = bool(upd["arcade_rewards_enabled"])
    if "sorter_enabled" in upd:
        upd["sorter_enabled"] = bool(upd["sorter_enabled"])
    if "arcade_chest_score" in upd:
        upd["arcade_chest_score"] = {g: max(0, int(float(v or 0))) for g, v in dict(upd["arcade_chest_score"] or {}).items() if g in games}
    if "arcade_prizes" in upd:
        out = {}
        for g, prizes in dict(upd["arcade_prizes"] or {}).items():
            if g in games:
                out[g] = await clean_prizes(prizes or [])
        upd["arcade_prizes"] = out
