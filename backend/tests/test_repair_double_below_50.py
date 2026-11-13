"""Repair price: every percent below 50 % durability costs ×2 (business_config.repair_cost_breakdown)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from business_config import repair_cost_breakdown  # noqa: E402


def test_example_from_the_spec():
    # 1 $CITY per 1 %: from 46 % → 50 (100..50) + 4 × 2 (50..46) = 58
    r = repair_cost_breakdown(1, 46)
    assert r["cost"] == 58 and r["base_pct"] == 50 and r["double_pct"] == 4


def test_at_or_above_50_is_linear():
    assert repair_cost_breakdown(1, 50)["cost"] == 50
    assert repair_cost_breakdown(0.3, 80)["cost"] == 0.3 * 20
    assert repair_cost_breakdown(5, 100)["cost"] == 0


def test_from_zero():
    assert repair_cost_breakdown(1, 0)["cost"] == 50 + 50 * 2
