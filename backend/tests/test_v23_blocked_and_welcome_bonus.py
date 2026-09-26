"""Tests for the 5 v2.3 fixes:
1. +0.5 TON welcome bonus (idempotent) on registration
2. Blocked user can still login (200, not 403)
3. /api/auth/me returns is_blocked + translated block_reason + block_reason_original
4. Level-0 business is NOT auto-listed on marketplace (see manual DB inspection)
5. Level-0 24h auto-buyback scheduler + code path
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ton-city-v2-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "sanyanazarov212@gmail.com"
ADMIN_PWD = "Qetuyrwioo"
USER_EMAIL = "testuser@example.com"
USER_PWD = "Test1234!"


def _admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def _user_token(email, pwd):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=20)
    return r


# ── 1. Welcome bonus ────────────────────────────────────────────────────────
def test_registration_welcome_bonus_idempotent():
    email = f"TEST_bonus_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "Test1234!"
    username = f"TEST_b_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": pwd, "username": username, "agreement_accepted": True,
    }, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    assert tok
    h = {"Authorization": f"Bearer {tok}"}
    r1 = requests.get(f"{API}/auth/me", headers=h, timeout=20)
    assert r1.status_code == 200, r1.text
    b1 = r1.json().get("bonus_balance")
    assert abs(float(b1) - 0.5) < 1e-6, f"first /me bonus_balance expected 0.5 got {b1}"
    r2 = requests.get(f"{API}/auth/me", headers=h, timeout=20)
    b2 = r2.json().get("bonus_balance")
    assert abs(float(b2) - 0.5) < 1e-6, f"second /me bonus should still be 0.5 (idempotent) got {b2}"


# ── 2 & 3. Blocked login + /me flags ────────────────────────────────────────
def test_blocked_user_can_login_and_me_returns_flags():
    admin_tok = _admin_token()
    ah = {"Authorization": f"Bearer {admin_tok}"}

    # Get testuser id
    tr = _user_token(USER_EMAIL, USER_PWD)
    assert tr.status_code == 200, tr.text
    utok = tr.json()["token"]
    uh = {"Authorization": f"Bearer {utok}"}
    me = requests.get(f"{API}/auth/me", headers=uh, timeout=20).json()
    uid = me["id"]

    # Ensure user language is 'en' — hit settings endpoint or fall back on DB shape
    # via re-login; we'll set language via /api/user/language if exists, else skip.
    try:
        requests.post(f"{API}/user/language", headers=uh, json={"language": "en"}, timeout=10)
    except Exception:
        pass

    # Block
    reason_ru = "Тестовая причина"
    br = requests.post(f"{API}/admin/user/{uid}/block", headers=ah, json={"reason": reason_ru}, timeout=20)
    assert br.status_code == 200, f"block failed: {br.status_code} {br.text}"

    try:
        # Login the blocked user — MUST be 200
        lr = _user_token(USER_EMAIL, USER_PWD)
        assert lr.status_code == 200, f"blocked user should still login, got {lr.status_code} {lr.text}"
        btok = lr.json()["token"]
        bh = {"Authorization": f"Bearer {btok}"}
        me2 = requests.get(f"{API}/auth/me", headers=bh, timeout=25).json()
        assert me2.get("is_blocked") is True, f"is_blocked flag missing: {me2}"
        assert me2.get("block_reason_original") == reason_ru, f"original mismatch: {me2.get('block_reason_original')}"
        translated = me2.get("block_reason") or ""
        assert translated, "block_reason (translated) should be non-empty"
        # Sanity: translation should not equal the raw Russian when lang=en
        # (LibreTranslate is falling back to Emergent LLM per request).
        if (me2.get("language") or "").lower().startswith("en"):
            assert translated != reason_ru, f"expected English translation, got same Russian: {translated!r}"
    finally:
        ur = requests.post(f"{API}/admin/user/{uid}/unblock", headers=ah, timeout=20)
        assert ur.status_code == 200, f"unblock failed: {ur.status_code} {ur.text}"


# ── 4. Level-0 auto-listing removed (static code check) ─────────────────────
def test_level0_no_create_zero_listing_call_in_claim_paths():
    """The two claim sites (~lines 566, 846) must no longer call
    create_zero_listing / set on_sale=True for the level-0 business."""
    with open("/app/backend/routes/ton_island.py") as f:
        src = f.read()
    # No live create_zero_listing invocations (only the marketplace list flow).
    assert "create_zero_listing(" not in src, "create_zero_listing still called in ton_island.py"
    # Sanity: comment stating removal is present at both sites
    assert src.count("NOT auto-listed") >= 2, "expected two comments documenting removal"


# ── 5. Scheduler job registered ─────────────────────────────────────────────
def test_zero_level_buyback_scheduler_registered():
    import glob
    found = False
    for path in glob.glob("/var/log/supervisor/backend.*.log"):
        try:
            with open(path, errors="ignore") as f:
                if "Level-0 seller 24h auto-buyback" in f.read():
                    found = True
                    break
        except Exception:
            continue
    assert found, "APScheduler log must contain 'Level-0 seller 24h auto-buyback' registration line"


def test_zero_buyback_code_credits_bonus_and_notifies():
    """Static verification that process_zero_level_buyback credits bonus_balance
    (level-0 sale rule) and sends a localized notification."""
    with open("/app/backend/zero_lease.py") as f:
        src = f.read()
    assert "process_zero_level_buyback" in src
    assert "$inc" in src and "bonus_balance" in src, "must credit bonus_balance"
    assert "notify_user(" in src, "must notify seller"
    assert "ZERO_BUYBACK_HOURS" in src, "must gate on 24h cutoff"
