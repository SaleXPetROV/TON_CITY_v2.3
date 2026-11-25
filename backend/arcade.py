"""GRAM City — «Аркада»: small games for City Pass XP, the reward is unlocked by watching rewarded ads.

Games (the frontend draws them, src/arcade/): shooter · racer · basket · snake · tower · g2048 · memory · math · tictac.
Every game has, set by the admin («Аркада» tab): on/off, attempts per day, MAX XP per game and the score that gives
the maximum (target). Difficulty (easy / normal / hard) pays a share of the maximum (default 50 / 75 / 100 %).

  XP of a game = floor(max_xp × difficulty share × min(1, score / target)) (+ Founder Pass «+XP %» perk).
  The GAME score itself has no maximum: shooter / racer / snake / tower / 2048 are endless, «Память» is limited by
  time (boards are dealt again), «Крестики-нолики» by 3 losses and 120 s.

Flow
  GET  /api/arcade                               hub: games, attempts left, XP today, unclaimed rewards
  POST /api/arcade/{game}/start                  {difficulty, preview?} → session {id, seed, …}; uses one attempt
  POST /api/arcade/session/{sid}/finish          {score, duration_ms, stats} → the server checks it, makes a reward
  GET  /api/arcade/reward/{rid}                  the reward: XP total / unlocked / credited, ads confirmed / pending
  POST /api/arcade/reward/{rid}/ad/start         a fresh Monetag ymid for the next ad of this reward
  POST /api/arcade/reward/{rid}/ad/watched       the app reports the ad (Monetag promise resolved)
  GET  /api/arcade/{game}/top                    top 5 of today by the best single game + my place
  POST /api/arcade/session/{sid}/revive/start    «Продолжить?» after losing — a ymid for one ad (once per game)
  GET/PUT /api/admin/arcade                      settings + today's numbers (admin, Russian)

Reward by ads: a game worth up to `one_ad_max_xp` XP needs ONE ad for everything. Otherwise its XP is split by `ad_shares_pct` (default [50, 25, 25] = 2/4 + 1/4 + 1/4): the first watched
ad unlocks 2/4 (the game part plus the first ad's part), every next ad +1/4, three ads = the full XP. The XP of each
unlocked part goes to City Pass at once (city_pass.add_xp "arcade"). Counted like the daily-bonus ads: by Monetag's
postback when «verify_postback» is on (ads.py), otherwise by the app's report with a minimum gap. When ads are off
(admin → Monetag), the whole XP is credited right after the game. Arcade XP per day is limited by `daily_xp_cap`.

Anti-cheat: the score is checked against the time of the session (server clock), a per-game maximum rate, and
game-specific stats; «Быстрый счёт» is replayed on the server from the seed (same generator as the app).

Before a new game, a previous game's reward that has no watched ad yet must get at least one ad (409 arcade_watch_first).

Preview: while the arcade is switched off, players don't see it; admins always do. A game started with
`preview: true` by an admin uses no attempt and credits no XP; its ads may be simulated.
"""
from __future__ import annotations

import logging
import math
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

GAMES = ["shooter", "racer", "basket", "snake", "tower", "g2048", "memory", "math", "tictac"]
DIFFS = ("easy", "normal", "hard")

# per-game anti-cheat limits (not in the admin): max score per second of play, min seconds of a counted game
LIMITS = {
    "shooter": {"rate": 600, "min_sec": 5},           # late waves with a ×3 combo score a lot — never cut a real run
    "racer":   {"rate": 90,  "min_sec": 5},
    "basket":  {"rate": 4,   "min_sec": 5},
    "snake":   {"rate": 40,  "min_sec": 4},
    "tower":   {"rate": 30,  "min_sec": 3},
    "g2048":   {"rate": 450, "min_sec": 5},
    "memory":  {"rate": 260, "min_sec": 6},
    "math":    {"rate": 40,  "min_sec": 3},
    "tictac":  {"rate": 120, "min_sec": 3},
}
# admin defaults per game: target score (score that gives the full XP of a difficulty) and XP per difficulty
_BASE = {
    "shooter": (2500, 30), "racer": (3000, 25), "basket": (60, 20), "snake": (300, 20), "tower": (400, 20),
    "g2048": (5000, 30), "memory": (1000, 15), "math": (250, 20), "tictac": (400, 15),
}
HAS_LIVES = {"shooter": {"easy": 5, "normal": 3, "hard": 2}, "racer": {"easy": 5, "normal": 3, "hard": 2}}


def _game_default(g: str) -> Dict[str, Any]:
    target, mx = _BASE[g]
    diffs = {}
    for d, k in (("easy", 0.5), ("normal", 0.75), ("hard", 1.0)):
        diffs[d] = {"xp": int(mx * k), "speed": 100}
        if g in HAS_LIVES:
            diffs[d]["lives"] = HAS_LIVES[g][d]
    return {"enabled": True, "free_play": True, "attempts_max": 4, "regen_minutes": 120, "target_score": target, "diffs": diffs}


GAME_DEFAULTS = {g: _game_default(g) for g in GAMES}
DEFAULTS: Dict[str, Any] = {
    "enabled": False,                       # off = players don't see the arcade (admins always do)
    "daily_xp_cap": 150,                    # arcade XP a player can get per MSK day, all games (0 = no limit)
    "ads_per_reward": 3,
    "ad_shares_pct": [50, 25, 25],          # share of the game's XP unlocked by the 1st / 2nd / 3rd ad
    "one_ad_max_xp": 15,                    # a game worth up to this XP needs ONE ad for all of it (0 = always the chain)
    "reward_ttl_hours": 24,                 # an unclaimed reward can be finished with ads within this time
    "games": GAME_DEFAULTS,
}
SESSION_TTL_MIN = 30
MATH_SECONDS = 60
TICTAC_ROUNDS = 400                     # no fixed number of rounds: until 3 losses or TICTAC_SECONDS (frontend clock)
TICTAC_LIVES = 3
TICTAC_SECONDS = 120
MEMORY_PAIRS = {"easy": 6, "normal": 8, "hard": 10}          # pairs on one board; a cleared board is dealt again
MEMORY_SECONDS = {"easy": 90, "normal": 75, "hard": 60}      # «Память» is limited by time, not by score


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day() -> str:
    from core.timeutil import msk_today_str
    return msk_today_str()


def _int(v, lo, hi, default=0) -> int:
    try:
        return max(lo, min(hi, int(float(v))))
    except (TypeError, ValueError):
        return default


# ───────────────────────────── settings ─────────────────────────────
def _clean(doc: Dict[str, Any]) -> Dict[str, Any]:
    cfg = {**DEFAULTS, **{k: v for k, v in (doc or {}).items() if k in DEFAULTS}}
    cfg["enabled"] = bool(cfg.get("enabled"))
    cfg["daily_xp_cap"] = _int(cfg.get("daily_xp_cap"), 0, 100000, DEFAULTS["daily_xp_cap"])
    n = _int(cfg.get("ads_per_reward"), 1, 5, 3)
    shares = [_int(x, 0, 100, 0) for x in (cfg.get("ad_shares_pct") or [])][:n]
    shares += [0] * (n - len(shares))
    if sum(shares) <= 0:
        shares = [100 // n] * n
    # the shares always add up to 100 % (the last one takes the rest)
    tot = sum(shares)
    shares = [int(round(x * 100 / tot)) for x in shares]
    shares[-1] += 100 - sum(shares)
    cfg["ads_per_reward"], cfg["ad_shares_pct"] = n, shares
    cfg["reward_ttl_hours"] = _int(cfg.get("reward_ttl_hours"), 1, 168, 24)
    cfg["one_ad_max_xp"] = _int(cfg.get("one_ad_max_xp"), 0, 100000, DEFAULTS["one_ad_max_xp"])
    old_pct = (doc or {}).get("diff_xp_pct") or {"easy": 50, "normal": 75, "hard": 100}
    games = {}
    src = cfg.get("games") or {}
    for g in GAMES:
        dflt = GAME_DEFAULTS[g]
        s_ = {**dflt, **(src.get(g) or {})}
        if "diffs" not in (src.get(g) or {}) and (src.get(g) or {}).get("max_xp") is not None:   # settings of the 1st version
            mx = _int(src[g]["max_xp"], 0, 10000, 0)
            s_["diffs"] = {d: {**dflt["diffs"][d], "xp": int(mx * _int(old_pct.get(d), 0, 300, 75) / 100)} for d in DIFFS}
        diffs = {}
        for d in DIFFS:
            x = {**dflt["diffs"][d], **((s_.get("diffs") or {}).get(d) or {})}
            diffs[d] = {"xp": _int(x.get("xp"), 0, 10000, dflt["diffs"][d]["xp"]), "speed": _int(x.get("speed"), 50, 200, 100)}
            if g in HAS_LIVES:
                diffs[d]["lives"] = _int(x.get("lives"), 1, 9, HAS_LIVES[g][d])
        games[g] = {"enabled": bool(s_.get("enabled")), "free_play": bool(s_.get("free_play", True)),
                    "attempts_max": _int(s_.get("attempts_max", s_.get("attempts_per_day")), 0, 100, 4),
                    "regen_minutes": _int(s_.get("regen_minutes"), 0, 7 * 24 * 60, 120),
                    "target_score": _int(s_.get("target_score"), 1, 10_000_000, dflt["target_score"]),
                    "diffs": diffs}
        games[g]["max_xp"] = max(v["xp"] for v in diffs.values())
    cfg["games"] = games
    return cfg


async def get_config(db) -> Dict[str, Any]:
    return _clean(await db.admin_settings.find_one({"type": "arcade"}, {"_id": 0}) or {})


async def _perks(db, uid: str) -> Dict[str, Any]:
    try:
        import founder_pass
        return await founder_pass.user_perks(db, uid) or {}
    except Exception:
        return {}


def game_xp(cfg, game: str, difficulty: str, score: float, bonus_pct: float = 0) -> int:
    g = cfg["games"][game]
    frac = max(0.0, min(1.0, float(score) / max(1, g["target_score"])))   # XP is capped: full XP at target_score
    xp = math.floor(g["diffs"].get(difficulty, g["diffs"]["normal"])["xp"] * frac + 1e-9)
    if xp > 0 and bonus_pct:
        xp = math.floor(xp * (1 + float(bonus_pct) / 100.0) + 1e-9)
    return max(0, int(xp))


def shares_for(cfg, xp: int) -> List[int]:
    """Few XP → one ad for all of it; more → the admin's chain (default 2/4 + 1/4 + 1/4)."""
    if cfg.get("one_ad_max_xp") and xp <= cfg["one_ad_max_xp"]:
        return [100]
    return list(cfg["ad_shares_pct"])


def unlocked_xp(total: int, shares: List[int], ads: int) -> int:
    """XP unlocked after `ads` confirmed ads (the last ad always unlocks the rest)."""
    if ads <= 0:
        return 0
    if ads >= len(shares):
        return int(total)
    return min(int(total), int(math.floor(total * sum(shares[:ads]) / 100.0 + 1e-9)))


# ───────────────────────────── «Быстрый счёт» generator (same as src/arcade/rng.js) ─────────────────────────────
def _imul(a: int, b: int) -> int:
    return (a * b) & 0xFFFFFFFF


def mulberry32(seed: int):
    state = [seed & 0xFFFFFFFF]

    def nxt() -> float:
        state[0] = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        a = state[0]
        t = _imul(a ^ (a >> 15), a | 1)
        t = ((t + _imul(t ^ (t >> 7), t | 61)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return nxt


def math_questions(seed: int, difficulty: str, n: int) -> List[Dict[str, Any]]:
    r = mulberry32(seed)
    ops = {"easy": ["+", "-"], "normal": ["+", "-", "*"], "hard": ["+", "-", "*", "/"]}[difficulty]
    top = {"easy": 20, "normal": 50, "hard": 99}[difficulty]
    out = []
    for _ in range(n):
        op = ops[int(r() * len(ops))]
        a = 1 + int(r() * top)
        b = 1 + int(r() * top)
        if op == "*":
            a, b = 2 + int(r() * 11), 2 + int(r() * (9 if difficulty == "normal" else 14))
            ans = a * b
        elif op == "/":
            b = 2 + int(r() * 11)
            ans = 2 + int(r() * 11)
            a = ans * b
        elif op == "-":
            if b > a:
                a, b = b, a
            ans = a - b
        else:
            ans = a + b
        out.append({"a": a, "b": b, "op": op, "ans": ans})
    return out


def _math_score(seed: int, difficulty: str, answers) -> Optional[int]:
    """Replays the answers: [{a: number, t: ms since start}] in order. None = impossible input."""
    answers = list(answers or [])[:400]
    qs = math_questions(seed, difficulty, len(answers))
    score, last_t, streak = 0, -1000.0, 0
    for i, a in enumerate(answers):
        try:
            v, t = int(a.get("a")), float(a.get("t"))
        except (TypeError, ValueError, AttributeError):
            return None
        if t < last_t + 250 or t > MATH_SECONDS * 1000 + 1500:
            return None
        last_t = t
        if v == qs[i]["ans"]:
            streak += 1
            score += 10 + min(5, streak // 3) * 2
        else:
            streak = 0
            score = max(0, score - 5)
    return score


# ───────────────────────────── tic-tac-toe check ─────────────────────────────
_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def _ttt_result(moves, first: str, allow_open: bool = False) -> Optional[str]:
    """moves: cells 0..8 alternating, `first` = 'p' (player = X) or 'ai'. → 'win' | 'loss' | 'draw' | 'open'
    (unfinished, only when `allow_open` — the last round cut by the clock) | None (illegal)."""
    board = [""] * 9
    who = first
    mv = list(moves or [])
    for k, m in enumerate(mv):
        try:
            m = int(m)
        except (TypeError, ValueError):
            return None
        if not 0 <= m <= 8 or board[m]:
            return None
        board[m] = who
        for a, b, c in _LINES:
            if board[a] and board[a] == board[b] == board[c]:
                return ("win" if board[a] == "p" else "loss") if k == len(mv) - 1 else None
        who = "ai" if who == "p" else "p"
    if all(board):
        return "draw"
    return "open" if allow_open else None


def tictac_points(res: str, win_streak: int) -> int:
    """Same as the frontend (core.tictacPoints): win 100 + 25 per win in a row (up to +100), draw 30, loss 0."""
    if res == "win":
        return 100 + 25 * min(4, max(0, win_streak - 1))
    return 30 if res == "draw" else 0


def _tictac_score(rounds) -> Optional[int]:
    """No maximum: rounds go on until 3 losses (or the clock). Every round is replayed; only the LAST round may be
    unfinished (cut by the time limit) and gives 0."""
    rounds = list(rounds or [])
    if len(rounds) > TICTAC_ROUNDS:
        return None
    score, streak, losses = 0, 0, 0
    for i, rd in enumerate(rounds):
        if losses >= TICTAC_LIVES:                 # nothing can be played after the 3rd loss
            return None
        first = "p" if i % 2 == 0 else "ai"
        res = _ttt_result((rd or {}).get("moves"), first, allow_open=(i == len(rounds) - 1))
        if res is None:
            return None
        if res == "open":
            continue
        streak = streak + 1 if res == "win" else 0
        losses += 1 if res == "loss" else 0
        score += tictac_points(res, streak)
    return score


def memory_points(pairs: int, boards: int, combo_bonus: int) -> int:
    return pairs * 50 + boards * 100 + combo_bonus


# ───────────────────────────── score check ─────────────────────────────
def check_score(game: str, difficulty: str, seed: int, body: Dict[str, Any], elapsed_s: float, speed_pct: int = 100) -> Dict[str, Any]:
    """→ {ok, score, reason}. The score is recomputed from stats where the game allows it."""
    lim = dict(LIMITS[game])
    lim["rate"] = lim["rate"] * max(1.0, speed_pct / 100.0)
    dur = _int(body.get("duration_ms"), 0, 3_600_000, 0) / 1000.0
    st = body.get("stats") or {}
    if dur > elapsed_s + 3:                                   # longer than the session lasted on the server clock
        return {"ok": False, "score": 0, "reason": "time"}
    dur = min(dur, elapsed_s + 3)
    if game == "math":
        sc = _math_score(seed, difficulty, st.get("answers"))
        if sc is None:
            return {"ok": False, "score": 0, "reason": "replay"}
        score = sc
    elif game == "tictac":
        sc = _tictac_score(st.get("rounds"))
        if sc is None:
            return {"ok": False, "score": 0, "reason": "replay"}
        score = sc
    elif game == "memory":
        # no score limit — the limit is the time: boards are dealt again until the clock runs out
        per = MEMORY_PAIRS.get(difficulty, 8)
        pairs = _int(st.get("pairs"), 0, 100000)
        moves = _int(st.get("moves"), 0, 1000000)
        boards = _int(st.get("boards"), 0, 100000)
        combo = _int(st.get("combo_bonus"), 0, 10_000_000)
        if (moves < pairs or boards > pairs // max(1, per) or combo > pairs * 50
                or pairs > dur * 1.6 + 2):
            return {"ok": False, "score": 0, "reason": "stats"}
        score = memory_points(pairs, boards, combo)
    elif game == "tower":
        floors, perfect = _int(st.get("floors"), 0, 10000), _int(st.get("perfect"), 0, 10000)
        if perfect > floors or floors > dur * 2 + 2:
            return {"ok": False, "score": 0, "reason": "stats"}
        score = floors * 10 + perfect * 5
    elif game == "snake":
        food = _int(st.get("food"), 0, 10000)
        if food > dur * 4 + 2:
            return {"ok": False, "score": 0, "reason": "stats"}
        score = food * 10
    elif game == "basket":
        made, shots = _int(st.get("made"), 0, 10000), _int(st.get("shots"), 0, 10000)
        score = _int(body.get("score"), 0, 10_000_000)
        if made > shots or shots > dur * 2 + 2 or score > made * 4:
            return {"ok": False, "score": 0, "reason": "stats"}
    else:                                                     # shooter / racer / g2048: rate check
        score = _int(body.get("score"), 0, 10_000_000)
    if score > 0 and dur < lim["min_sec"]:
        return {"ok": False, "score": 0, "reason": "short"}
    if score > lim["rate"] * max(dur, 1) + lim["rate"] * 2:
        return {"ok": False, "score": 0, "reason": "rate"}
    return {"ok": True, "score": int(score), "reason": ""}


# ───────────────────────────── rewards ─────────────────────────────
async def _xp_today(db, uid: str) -> int:
    rows = await db.arcade_rewards.find({"user_id": uid, "day": _day(), "preview": {"$ne": True}},
                                        {"_id": 0, "xp_credited": 1}).to_list(500)
    return sum(int(r.get("xp_credited") or 0) for r in rows)


async def _confirmed_ads(db, rid: str, ads_cfg: Dict[str, Any], preview: bool) -> Dict[str, int]:
    base: Dict[str, Any] = {"purpose": "arcade", "ref": rid}
    client = await db.ad_views.count_documents({**base, "source": "client"})
    if preview or not ads_cfg.get("verify_postback"):
        q = {**base, "source": "client"}
    else:
        q = {**base, "source": "postback"}
    if ads_cfg.get("require_valued") and not preview:
        q["reward"] = {"$ne": "non_valued"}
    conf = await db.ad_views.count_documents(q)
    return {"confirmed": conf, "reported": client, "pending": max(0, client - conf) if q["source"] == "postback" else 0}


async def _sync(db, rid: str) -> Optional[Dict[str, Any]]:
    """Unlock and credit what the confirmed ads allow. Safe to call any number of times."""
    import ads as _ads
    rw = await db.arcade_rewards.find_one({"id": rid}, {"_id": 0})
    if not rw or rw.get("status") == "done":
        return rw
    ads_cfg = await _ads.get_config(db)
    preview = bool(rw.get("preview"))
    if not _ads.ads_active(ads_cfg) and not preview:
        n = len(rw["shares"])                                 # ads are off → the whole reward
        cnt = {"confirmed": n, "reported": n, "pending": 0}
    else:
        cnt = await _confirmed_ads(db, rid, ads_cfg, preview)
    ads_n = min(len(rw["shares"]), cnt["confirmed"])
    target = unlocked_xp(rw["xp_total"], rw["shares"], ads_n)
    delta = target - int(rw.get("xp_unlocked") or 0)
    upd: Dict[str, Any] = {"ads_confirmed": ads_n, "ads_pending": cnt["pending"]}
    if ads_n >= len(rw["shares"]):
        upd["status"] = "done"
    if delta > 0:
        # claim the delta atomically (two polls at once must not credit twice)
        res = await db.arcade_rewards.update_one({"id": rid, "xp_unlocked": rw.get("xp_unlocked") or 0},
                                                 {"$set": {**upd, "xp_unlocked": target}})
        if not res.modified_count:
            return await db.arcade_rewards.find_one({"id": rid}, {"_id": 0})
        credited = 0
        if not preview:
            cfg = await get_config(db)
            give = delta
            if cfg["daily_xp_cap"] > 0:
                left = max(0, cfg["daily_xp_cap"] - await _xp_today(db, rw["user_id"]))
                give = min(give, left)
            if give > 0:
                try:
                    import city_pass
                    credited = await city_pass.add_xp(db, rw["user_id"], "arcade", give)
                except Exception as e:                        # never lose the claim because of the pass
                    logger.warning(f"arcade xp: {e}")
            await db.arcade_rewards.update_one({"id": rid}, {"$inc": {"xp_credited": int(credited or 0),
                                                                       "xp_capped": int(delta - give)}})
    else:
        await db.arcade_rewards.update_one({"id": rid}, {"$set": upd})
    rw = await db.arcade_rewards.find_one({"id": rid}, {"_id": 0})
    if rw and rw.get("status") == "done" and (rw.get("chest") or {}).get("state") == "pending":
        try:                                                 # the last ad → the chest of the good game (games_hub)
            import games_hub
            if await games_hub.chest_after_ads(db, rw):
                rw = await db.arcade_rewards.find_one({"id": rid}, {"_id": 0})
        except Exception as e:
            logger.warning(f"arcade chest after ads: {e}")
    return rw


def _pub_reward(rw: Dict[str, Any]) -> Dict[str, Any]:
    if not rw:
        return {}
    shares = rw.get("shares") or []
    return {k: rw.get(k) for k in ("id", "game", "difficulty", "score", "xp_total", "xp_unlocked", "xp_credited",
                                   "xp_capped", "ads_confirmed", "ads_pending", "status", "preview", "created_at",
                                   "expires_at", "no_ads", "chest")} | {
        "shares": shares, "ads_total": len(shares),
        "next_xp": (unlocked_xp(rw.get("xp_total", 0), shares, (rw.get("ads_confirmed") or 0) + 1)
                    - int(rw.get("xp_unlocked") or 0)) if (rw.get("ads_confirmed") or 0) < len(shares) else 0}


async def ensure_indexes(db) -> None:
    for coll, keys, unique in (("arcade_sessions", [("id", 1)], True),
                               ("arcade_sessions", [("user_id", 1), ("game", 1), ("day", 1)], False),
                               ("arcade_rewards", [("id", 1)], True),
                               ("arcade_rewards", [("user_id", 1), ("status", 1)], False),
                               ("arcade_rewards", [("user_id", 1), ("day", 1)], False),
                               ("ad_views", [("purpose", 1), ("ref", 1), ("source", 1)], False)):
        try:
            await db[coll].create_index(keys, unique=unique)
        except Exception as e:
            logger.warning("arcade index %s %s: %s", coll, keys, e)


# ───────────────────────────── paid attempts (regenerate one by one) ─────────────────────────────
def _parse(iso: str) -> datetime:
    d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def attempts_view(doc: Optional[Dict[str, Any]], mx: int, regen_min: int, now: Optional[datetime] = None) -> Dict[str, Any]:
    """{left, max, at, next_at}: `left` paid attempts now; one comes back every `regen_min` minutes up to `mx`
    (regen_min 0 → all come back at 00:00 MSK)."""
    now = now or _now()
    if not doc:
        return {"left": mx, "max": mx, "at": now, "next_at": None}
    left, at = int(doc.get("left", mx)), _parse(doc.get("at") or now.isoformat())
    if regen_min > 0:
        step = regen_min * 60
        if left < mx:
            n = int((now - at).total_seconds() // step)
            if n > 0:
                left = min(mx, left + n)
                at = at + timedelta(seconds=n * step)
    elif doc.get("day") != _day():
        left = mx
    left = max(0, min(left, mx))
    nxt = None
    if left < mx:
        if regen_min > 0:
            nxt = at + timedelta(seconds=regen_min * 60)
        else:
            msk = timezone(timedelta(hours=3))
            nxt = (now.astimezone(msk).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).astimezone(timezone.utc)
    return {"left": left, "max": mx, "at": now if left >= mx else at, "next_at": nxt}


async def get_attempts(db, uid: str, game: str, gc: Dict[str, Any], extra: int = 0) -> Dict[str, Any]:
    doc = await db.arcade_attempts.find_one({"user_id": uid, "game": game}, {"_id": 0})
    return attempts_view(doc, gc["attempts_max"] + extra, gc["regen_minutes"])


async def use_attempt(db, uid: str, game: str, gc: Dict[str, Any], extra: int = 0) -> bool:
    v = await get_attempts(db, uid, game, gc, extra)
    if v["left"] <= 0:
        return False
    at = _now() if v["left"] >= v["max"] else v["at"]          # the regen clock starts when the first attempt is spent
    await db.arcade_attempts.update_one({"user_id": uid, "game": game},
                                        {"$set": {"left": v["left"] - 1, "at": at.isoformat(), "day": _day()}}, upsert=True)
    return True


def _iso(d: Optional[datetime]) -> Optional[str]:
    return d.isoformat() if d else None


# ───────────────────────────── router ─────────────────────────────
def create_arcade_router(db, get_current_user, get_current_admin) -> APIRouter:
    r = APIRouter()

    async def _hub(user, preview: bool) -> Dict[str, Any]:
        import ads as _ads
        cfg = await get_config(db)
        is_admin = bool(getattr(user, "is_admin", False))
        if not cfg["enabled"] and not is_admin:
            return {"visible": False}
        uid = user.id
        perks = await _perks(db, uid)
        extra = int(perks.get("arcade_extra_attempts") or 0) if perks.get("active") else 0
        bonus = float(perks.get("arcade_xp_bonus_pct") or 0) if perks.get("active") else 0
        games = []
        for g in GAMES:
            gc = cfg["games"][g]
            if not gc["enabled"] and not is_admin:
                continue
            av = await get_attempts(db, uid, g, gc, extra)
            best = await db.arcade_sessions.find({"user_id": uid, "game": g, "day": _day(), "status": "finished"},
                                                 {"_id": 0, "score": 1}).sort("score", -1).limit(1).to_list(1)
            games.append({"id": g, "enabled": gc["enabled"], "free_play": gc["free_play"],
                          "attempts_per_day": av["max"], "attempts_max": av["max"], "attempts_left": av["left"],
                          "next_attempt_at": _iso(av["next_at"]), "regen_minutes": gc["regen_minutes"],
                          "max_xp": game_xp(cfg, g, "hard", gc["target_score"], bonus), "target_score": gc["target_score"],
                          "tuning": gc["diffs"],
                          "xp_by_difficulty": {d: game_xp(cfg, g, d, gc["target_score"], bonus) for d in DIFFS},
                          "ads_by_difficulty": {d: len(shares_for(cfg, game_xp(cfg, g, d, gc["target_score"], bonus))) for d in DIFFS},
                          "best_today": (best[0].get("score") if best else 0)})
        now_iso = _now().isoformat()
        pend = await db.arcade_rewards.find({"user_id": uid, "status": "pending", "expires_at": {"$gt": now_iso},
                                             "preview": bool(preview)}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)
        ads_cfg = await _ads.get_config(db)
        return {"visible": True, "enabled": cfg["enabled"], "preview_only": not cfg["enabled"], "games": games,
                "xp_today": await _xp_today(db, uid), "daily_xp_cap": cfg["daily_xp_cap"],
                "ads": {"active": _ads.ads_active(ads_cfg), "per_reward": cfg["ads_per_reward"], "shares": cfg["ad_shares_pct"],
                        "one_ad_max_xp": cfg["one_ad_max_xp"]},
                "server_time": _now().isoformat(), "xp_bonus_pct": bonus, "extra_attempts": extra,
                "pending_rewards": [_pub_reward(x) for x in pend]}

    @r.get("/api/arcade")
    async def hub(preview: bool = False, current_user=Depends(get_current_user)):
        return await _hub(current_user, preview and bool(getattr(current_user, "is_admin", False)))

    @r.post("/api/arcade/{game}/start")
    async def start(game: str, body: Dict[str, Any] = None, current_user=Depends(get_current_user)):
        body = body or {}
        if game not in GAMES:
            raise HTTPException(status_code=404, detail="arcade_no_game")
        cfg = await get_config(db)
        is_admin = bool(getattr(current_user, "is_admin", False))
        preview = bool(body.get("preview")) and is_admin
        if not preview and (not cfg["enabled"] or not cfg["games"][game]["enabled"]) and not is_admin:
            raise HTTPException(status_code=403, detail="arcade_closed")
        diff = body.get("difficulty") if body.get("difficulty") in DIFFS else "normal"
        uid = current_user.id
        gc = cfg["games"][game]
        free = bool(body.get("free")) and not preview
        if free and not gc["free_play"]:
            raise HTTPException(status_code=403, detail="arcade_no_free")
        perks = await _perks(db, uid)
        extra = int(perks.get("arcade_extra_attempts") or 0) if perks.get("active") else 0
        if not preview and not free:
            if (await get_attempts(db, uid, game, gc, extra))["left"] <= 0:
                raise HTTPException(status_code=429, detail="arcade_no_attempts")
            # the reward of a previous game must be "opened" by an ad before the next game (the player can't skip ads)
            owe = await db.arcade_rewards.find_one({"user_id": uid, "status": "pending", "preview": {"$ne": True},
                                                    "ads_confirmed": 0, "ads_pending": {"$in": [0, None]},
                                                    "expires_at": {"$gt": _now().isoformat()}},
                                                   {"_id": 0, "id": 1}, sort=[("created_at", -1)])
            if owe:
                import ads as _ads
                if _ads.ads_active(await _ads.get_config(db)):
                    raise HTTPException(status_code=409, detail={"code": "arcade_watch_first", "reward_id": owe["id"]})
            if not await use_attempt(db, uid, game, gc, extra):
                raise HTTPException(status_code=429, detail="arcade_no_attempts")
        if not preview:
            # a game left unfinished stays counted (it was an attempt); close stale ones
            await db.arcade_sessions.update_many({"user_id": uid, "status": "playing",
                                                  "created_at": {"$lt": (_now() - timedelta(minutes=SESSION_TTL_MIN)).isoformat()}},
                                                 {"$set": {"status": "expired"}})
        sid = str(uuid.uuid4())
        seed = secrets.randbits(31)
        await db.arcade_sessions.insert_one({"id": sid, "user_id": uid, "game": game, "difficulty": diff, "seed": seed,
                                             "day": _day(), "status": "playing", "preview": preview, "free": free,
                                             "tuning": gc["diffs"][diff], "created_at": _now().isoformat()})
        return {"session_id": sid, "seed": seed, "game": game, "difficulty": diff, "preview": preview, "free": free,
                "tuning": gc["diffs"][diff], "max_xp": gc["diffs"][diff]["xp"], "target_score": gc["target_score"],
                "math_seconds": MATH_SECONDS, "tictac_seconds": TICTAC_SECONDS, "tictac_lives": TICTAC_LIVES,
                "memory_pairs": MEMORY_PAIRS[diff], "memory_seconds": MEMORY_SECONDS[diff]}

    @r.post("/api/arcade/session/{sid}/finish")
    async def finish(sid: str, body: Dict[str, Any] = None, current_user=Depends(get_current_user)):
        body = body or {}
        s = await db.arcade_sessions.find_one_and_update({"id": sid, "user_id": current_user.id, "status": "playing"},
                                                        {"$set": {"status": "finishing"}})
        if not s:
            raise HTTPException(status_code=404, detail="arcade_no_session")
        cfg = await get_config(db)
        started = datetime.fromisoformat(s["created_at"])
        elapsed = (_now() - started).total_seconds()
        if elapsed > SESSION_TTL_MIN * 60:
            await db.arcade_sessions.update_one({"id": sid}, {"$set": {"status": "expired"}})
            raise HTTPException(status_code=410, detail="arcade_expired")
        if body.get("abandoned"):                              # «Выйти»: the run does not count (the attempt is used)
            await db.arcade_sessions.update_one({"id": sid}, {"$set": {"status": "abandoned", "score": 0, "xp": 0,
                                                                     "finished_at": _now().isoformat()}})
            return {"ok": True, "abandoned": True, "score": 0, "xp": 0, "reward": None}
        speed = int((s.get("tuning") or {}).get("speed") or 100)
        chk = check_score(s["game"], s["difficulty"], int(s["seed"]), body, elapsed, speed_pct=speed)
        perks = await _perks(db, current_user.id)
        bonus = float(perks.get("arcade_xp_bonus_pct") or 0) if perks.get("active") else 0
        extra = int(perks.get("arcade_extra_attempts") or 0) if perks.get("active") else 0
        xp = game_xp(cfg, s["game"], s["difficulty"], chk["score"], bonus) if chk["ok"] and not s.get("free") else 0
        await db.arcade_sessions.update_one({"id": sid}, {"$set": {
            "status": "finished" if chk["ok"] else "rejected", "score": chk["score"], "reject": chk["reason"],
            "duration_ms": _int(body.get("duration_ms"), 0, 3_600_000), "xp": xp, "finished_at": _now().isoformat()}})
        if not chk["ok"]:
            logger.info(f"arcade reject {s['game']} {current_user.id}: {chk['reason']}")
        reward = None
        if xp > 0:
            import ads as _ads
            ads_cfg = await _ads.get_config(db)
            rid = str(uuid.uuid4())
            rw = {"id": rid, "user_id": current_user.id, "session_id": sid, "game": s["game"], "difficulty": s["difficulty"],
                  "score": chk["score"], "xp_total": xp, "xp_unlocked": 0, "xp_credited": 0, "xp_capped": 0,
                  "shares": shares_for(cfg, xp), "ads_confirmed": 0, "ads_pending": 0, "status": "pending",
                  "preview": bool(s.get("preview")), "no_ads": not _ads.ads_active(ads_cfg) and not s.get("preview"),
                  "day": _day(), "created_at": _now().isoformat(),
                  "expires_at": (_now() + timedelta(hours=cfg["reward_ttl_hours"])).isoformat()}
            await db.arcade_rewards.insert_one(rw)
            reward = _pub_reward(await _sync(db, rid))
        av = await get_attempts(db, current_user.id, s["game"], cfg["games"][s["game"]], extra)
        # «Игры»: the same game also plays into the mini-games promotion (points of its own list of leaders,
        # a chest for a good game, threshold rewards) — games_hub.py; a failure there never loses the XP above
        try:
            import games_hub
            rw_doc = await db.arcade_rewards.find_one({"id": reward["id"]}, {"_id": 0}) if reward else None
            promo = await games_hub.on_arcade_finish(db, current_user.id, s["game"], int(chk["score"] or 0), sid,
                                                     bool(chk["ok"]), bool(s.get("preview")), rw_doc)
            if reward and rw_doc and (promo or {}).get("chest", {}).get("pending"):
                reward["chest"] = {"state": "pending", "game": s["game"]}
        except Exception as e:
            logger.warning(f"arcade promo rewards failed: {e}")
            promo = None
        return {"ok": chk["ok"], "score": chk["score"], "xp": xp, "reason": chk["reason"], "reward": reward,
                "free": bool(s.get("free")), "attempts_left": av["left"], "next_attempt_at": _iso(av["next_at"]),
                "promo": promo}

    async def _own_reward(rid: str, uid: str) -> Dict[str, Any]:
        rw = await db.arcade_rewards.find_one({"id": rid, "user_id": uid}, {"_id": 0})
        if not rw:
            raise HTTPException(status_code=404, detail="arcade_no_reward")
        return rw

    @r.get("/api/arcade/reward/{rid}")
    async def reward(rid: str, current_user=Depends(get_current_user)):
        await _own_reward(rid, current_user.id)
        return _pub_reward(await _sync(db, rid))

    @r.post("/api/arcade/reward/{rid}/ad/start")
    async def ad_start(rid: str, current_user=Depends(get_current_user)):
        rw = await _own_reward(rid, current_user.id)
        if rw["status"] != "pending":
            raise HTTPException(status_code=409, detail="arcade_reward_done")
        if rw.get("expires_at", "") < _now().isoformat():
            raise HTTPException(status_code=410, detail="arcade_reward_expired")
        ymid = f"{current_user.id}.a{secrets.token_hex(5)}"
        await db.ad_sessions.insert_one({"ymid": ymid, "user_id": current_user.id, "day": _day(), "purpose": "arcade",
                                         "ref": rid, "created_at": _now().isoformat()})
        return {"ymid": ymid, "request_var": f"arcade_{rw['game']}"}

    @r.post("/api/arcade/reward/{rid}/ad/watched")
    async def ad_watched(rid: str, body: Dict[str, Any] = None, current_user=Depends(get_current_user)):
        import ads as _ads
        body = body or {}
        rw = await _own_reward(rid, current_user.id)
        if rw["status"] != "pending":
            return _pub_reward(rw)
        uid = current_user.id
        ymid = str(body.get("ymid") or "")
        sess = await db.ad_sessions.find_one({"ymid": ymid, "user_id": uid, "purpose": "arcade", "ref": rid}, {"_id": 0, "ymid": 1})
        simulate = bool(body.get("simulate")) and bool(rw.get("preview"))
        if not sess and not simulate:
            raise HTTPException(status_code=400, detail="arcade_bad_ad")
        if simulate and not sess:
            ymid = f"{uid}.sim{secrets.token_hex(4)}"
        if await db.ad_views.find_one({"ymid": ymid, "source": "client"}, {"_id": 0, "id": 1}):
            return _pub_reward(await _sync(db, rid))
        if await db.ad_views.count_documents({"purpose": "arcade", "ref": rid, "source": "client"}) >= len(rw["shares"]) * 2:
            return _pub_reward(await _sync(db, rid))
        ads_cfg = await _ads.get_config(db)
        if not rw.get("preview"):
            last = await db.ad_views.find({"user_id": uid, "source": "client"}, {"_id": 0, "created_at": 1}) \
                .sort("created_at", -1).limit(1).to_list(1)
            if last and (_now() - datetime.fromisoformat(last[0]["created_at"])).total_seconds() < int(ads_cfg["min_gap_sec"]):
                raise HTTPException(status_code=429, detail="ad_too_fast")
        reward_t = str(body.get("reward_event_type") or "").lower()
        await db.ad_views.insert_one({"id": str(uuid.uuid4()), "user_id": uid, "day": _day(), "purpose": "arcade", "ref": rid,
                                      "source": "client", "ymid": ymid, "simulated": simulate,
                                      "reward": reward_t if reward_t in ("valued", "non_valued") else "",
                                      "created_at": _now().isoformat()})
        return _pub_reward(await _sync(db, rid))

    @r.get("/api/arcade/{game}/top")
    async def top(game: str, current_user=Depends(get_current_user)):
        """Top 5 of today by the BEST single game of each player (not a sum) + my place (the 6th line)."""
        if game not in GAMES:
            raise HTTPException(status_code=404, detail="arcade_no_game")
        rows = await db.arcade_sessions.find({"game": game, "day": _day(), "status": "finished", "preview": {"$ne": True},
                                              "score": {"$gt": 0}}, {"_id": 0, "user_id": 1, "score": 1, "finished_at": 1}) \
            .sort("score", -1).limit(20000).to_list(20000)
        best: Dict[str, Dict[str, Any]] = {}
        for x in rows:                                       # sorted by score desc → the first one of a player is his best
            if x["user_id"] not in best:
                best[x["user_id"]] = x
        ranked = sorted(best.values(), key=lambda x: (-int(x["score"]), x.get("finished_at") or ""))
        ids = [x["user_id"] for x in ranked[:5]]
        users = {u["id"]: u for u in await db.users.find({"id": {"$in": ids}},
                                                         {"_id": 0, "id": 1, "username": 1, "display_name": 1, "avatar": 1}).to_list(10)}
        out = []
        for i, x in enumerate(ranked[:5]):
            u = users.get(x["user_id"], {})
            out.append({"place": i + 1, "user_id": x["user_id"], "score": int(x["score"]),
                        "name": u.get("display_name") or u.get("username") or "Player", "avatar": u.get("avatar"),
                        "me": x["user_id"] == current_user.id})
        me = None
        for i, x in enumerate(ranked):
            if x["user_id"] == current_user.id:
                me = {"place": i + 1, "score": int(x["score"])}
                break
        return {"rows": out, "me": me, "players": len(ranked)}

    @r.post("/api/arcade/session/{sid}/revive/start")
    async def revive_start(sid: str, current_user=Depends(get_current_user)):
        """«Продолжить?» after losing: a ymid for the ad (one revive per game)."""
        s = await db.arcade_sessions.find_one_and_update({"id": sid, "user_id": current_user.id, "status": "playing",
                                                         "revived": {"$ne": True}}, {"$set": {"revived": True}})
        if not s:
            raise HTTPException(status_code=409, detail="arcade_no_revive")
        ymid = f"{current_user.id}.r{secrets.token_hex(5)}"
        await db.ad_sessions.insert_one({"ymid": ymid, "user_id": current_user.id, "day": _day(), "purpose": "arcade_revive",
                                         "ref": sid, "created_at": _now().isoformat()})
        return {"ymid": ymid, "request_var": f"arcade_revive_{s['game']}"}

    # ─────────── admin ───────────
    @r.get("/api/admin/arcade")
    async def a_get(_=Depends(get_current_admin)):
        cfg = await get_config(db)
        day = _day()
        stats = {}
        for g in GAMES:
            q = {"game": g, "day": day, "preview": {"$ne": True}}
            stats[g] = {"games": await db.arcade_sessions.count_documents(q),
                        "rejected": await db.arcade_sessions.count_documents({**q, "status": "rejected"}),
                        "players": len(await db.arcade_sessions.distinct("user_id", q))}
        rws = await db.arcade_rewards.find({"day": day, "preview": {"$ne": True}},
                                           {"_id": 0, "xp_total": 1, "xp_credited": 1, "ads_confirmed": 1}).to_list(20000)
        return {**cfg, "games_list": GAMES, "stats": stats,
                "today": {"rewards": len(rws), "xp_total": sum(x.get("xp_total", 0) for x in rws),
                          "xp_credited": sum(x.get("xp_credited", 0) for x in rws),
                          "ads": sum(x.get("ads_confirmed", 0) for x in rws),
                          "ad_views": await db.ad_views.count_documents({"day": day, "purpose": "arcade", "source": "client",
                                                                         "simulated": {"$ne": True}})}}

    @r.put("/api/admin/arcade")
    async def a_put(body: Dict[str, Any], _=Depends(get_current_admin)):
        cur = await get_config(db)
        upd = {k: v for k, v in (body or {}).items() if k in DEFAULTS}
        if "games" in upd:
            merged = {}
            for g in GAMES:
                new = (upd["games"] or {}).get(g) or {}
                m = {**cur["games"][g], **new}
                m["diffs"] = {d: {**cur["games"][g]["diffs"][d], **((new.get("diffs") or {}).get(d) or {})} for d in DIFFS}
                merged[g] = m
            upd["games"] = merged
        clean = _clean({**cur, **upd})
        await db.admin_settings.update_one({"type": "arcade"}, {"$set": {"type": "arcade", **clean}}, upsert=True)
        return await a_get()

    return r
