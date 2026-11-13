"""Credit collateral seizure rule (core.seizure.credit_in_default) — pure logic, no server needed.

A credit is seized only when it is «overdue» for 7 days and NOTHING was paid since; any payment brings it
back to «active». Before the fix every credit older than ~8 days was seized (a never-updated next_payment_due).
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.seizure import credit_in_default, credit_payment_clears_overdue, CREDIT_DEFAULT_GRACE_DAYS  # noqa: E402

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
iso = lambda d: (NOW - timedelta(days=d)).isoformat()


def test_active_credit_that_is_being_repaid_is_never_seized():
    c = {"status": "active", "remaining": 5.0, "created_at": iso(40), "last_payment": iso(0),
         "next_payment_due": iso(39)}   # the old field: set once at issuance, never moved
    assert credit_in_default(c, NOW) is False


def test_overdue_with_no_payment_for_the_grace_period_is_seized():
    c = {"status": "overdue", "remaining": 5.0, "overdue_since": iso(CREDIT_DEFAULT_GRACE_DAYS), "last_payment": None}
    assert credit_in_default(c, NOW) is True


def test_overdue_but_not_long_enough_is_kept():
    c = {"status": "overdue", "remaining": 5.0, "overdue_since": iso(CREDIT_DEFAULT_GRACE_DAYS - 1)}
    assert credit_in_default(c, NOW) is False


def test_any_payment_after_becoming_overdue_prevents_seizure():
    c = {"status": "overdue", "remaining": 5.0, "overdue_since": iso(10), "last_payment": iso(2)}
    assert credit_in_default(c, NOW) is False


def test_paid_off_credit_is_not_seized():
    c = {"status": "overdue", "remaining": 0.0, "overdue_since": iso(10)}
    assert credit_in_default(c, NOW) is False


def test_payment_clears_overdue_state():
    assert credit_payment_clears_overdue({"status": "overdue"}, 3.0) == {
        "status": "active", "overdue_since": None, "is_doubled_rate": False}
    assert credit_payment_clears_overdue({"status": "active"}, 3.0) == {}
    assert credit_payment_clears_overdue({"status": "overdue"}, 0.0) == {}


def test_seizure_debt_is_principal_plus_double_interest_minus_payments():
    from core.seizure import default_debt
    # borrowed 10 at 15 %: normal debt 11.5, at default 10 × 1.30 = 13
    d = default_debt({"amount": 10, "interest_rate": 0.15, "total_debt": 11.5, "remaining": 11.5})
    assert d == {"total": 13.0, "remaining": 13.0, "penalty": 1.5}
    # 4 already paid → 13 − 4 = 9 left to take from the sale
    d = default_debt({"amount": 10, "interest_rate": 0.15, "total_debt": 11.5, "remaining": 7.5, "paid": 4})
    assert d["remaining"] == 9.0 and d["penalty"] == 1.5
