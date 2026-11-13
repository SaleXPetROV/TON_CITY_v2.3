"""Reconcile the per-user tender escrow counter.

`users.frozen_city_for_tenders` is a running counter incremented when a tender
contract becomes active and decremented when it ends. In practice it can DRIFT
(a broken/completed contract whose decrement didn't fully match, or rounding),
leaving a stale positive residue. That residue then shows up in the withdrawal
modal as "Заморожено в контрактах" even when the user has NO active contracts.

`effective_frozen_city` returns the amount that is ACTUALLY frozen: if the user
has no active tender contract holding escrow, the answer is 0 and we self-heal
the stored counter. Otherwise we trust the stored counter (reconstructing exact
per-role reserves from every contract is fragile and unnecessary for the fix).
"""

# Contract statuses that still hold escrow against the user's balance.
ACTIVE_TENDER_STATES = ["ACTIVE", "PENDING_FUNDS", "PENDING_RESOURCES", "PENDING_STORAGE", "PROPOSED"]


# Contract states in which the accepted escrow is really held (frozen at accept, released at break / clear).
HOLDING_STATES = ["ACTIVE", "PENDING_FUNDS", "PENDING_RESOURCES", "PENDING_STORAGE"]


async def actual_frozen_city(db, user_id: str) -> float:
    """What is REALLY frozen for the player: the escrow of every contract that still holds it
    (seller → escrow_deposit, buyer → buyer_escrow_deposit), in $CITY."""
    total = 0.0
    async for c in db.tender_contracts.find(
            {"status": {"$in": HOLDING_STATES}, "$or": [{"seller_id": user_id}, {"buyer_id": user_id}]},
            {"_id": 0, "seller_id": 1, "buyer_id": 1, "escrow_deposit": 1, "buyer_escrow_deposit": 1}):
        if c.get("seller_id") == user_id:
            total += float(c.get("escrow_deposit", 0) or 0)
        if c.get("buyer_id") == user_id:
            total += float(c.get("buyer_escrow_deposit", 0) or 0)
    return max(0.0, round(total, 6))


async def effective_frozen_city(db, user) -> float:
    """The real frozen escrow in $CITY for this player — recomputed from the contracts that hold it.
    A drifted counter (a finished contract that never released its escrow) is healed to the real value:
    such a residue made the money «not there» for purchases while the balance showed it."""
    stored = float((user or {}).get("frozen_city_for_tenders", 0) or 0)
    if stored <= 0:
        return 0.0
    uid = (user or {}).get("id")
    if not uid:
        return stored
    try:
        actual = await actual_frozen_city(db, uid)
    except Exception:
        return stored
    if abs(actual - stored) > 0.001:
        try:
            await db.users.update_one({"id": uid}, {"$set": {"frozen_city_for_tenders": actual}})
        except Exception:
            pass
    return actual


async def heal_all(db) -> int:
    """Startup: fix every player whose frozen counter does not match their contracts."""
    n = 0
    async for u in db.users.find({"frozen_city_for_tenders": {"$gt": 0}}, {"_id": 0, "id": 1, "frozen_city_for_tenders": 1}):
        before = float(u.get("frozen_city_for_tenders") or 0)
        after = await effective_frozen_city(db, u)
        if abs(after - before) > 0.001:
            n += 1
    return n


async def _legacy_effective_frozen_city(db, user) -> float:
    """Return the real frozen escrow in $CITY for this user (0 when no active
    contracts). Self-heals a drifted counter down to 0 in that case."""
    stored = float((user or {}).get("frozen_city_for_tenders", 0) or 0)
    if stored <= 0:
        return 0.0
    ids = [v for v in {user.get("id"), user.get("wallet_address")} if v]
    if not ids:
        return stored
    q = {
        "status": {"$in": ACTIVE_TENDER_STATES},
        "$or": [
            {"seller_id": {"$in": ids}},
            {"buyer_id": {"$in": ids}},
            {"seller_wallet": {"$in": ids}},
            {"buyer_wallet": {"$in": ids}},
        ],
    }
    try:
        cnt = await db.tender_contracts.count_documents(q)
    except Exception:
        return stored
    if cnt == 0:
        try:
            await db.users.update_one(
                {"id": user.get("id")},
                {"$set": {"frozen_city_for_tenders": 0}},
            )
        except Exception:
            pass
        return 0.0
    return stored
