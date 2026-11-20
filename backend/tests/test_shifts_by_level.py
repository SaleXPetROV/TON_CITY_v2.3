"""Shifts that wear 100% durability can be set for every business level (admin «Экономика бизнесов»)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))


def test_level_value_then_type_value_then_default():
    import business_config as bc
    saved = dict(bc.DURABILITY_OVERRIDES)
    try:
        bc.DURABILITY_OVERRIDES.pop("bio_farm", None)
        assert abs(bc.get_daily_wear("bio_farm", 3) - 3.0 / bc.DEFAULT_SHIFTS_PER_100) < 1e-9
        bc.apply_durability_override("bio_farm", 12, None, None, {"1": 6, "10": 30, "5": ""})
        assert abs(bc.get_daily_wear("bio_farm", 1) - 3.0 / 6) < 1e-9       # its own level value
        assert abs(bc.get_daily_wear("bio_farm", 0) - 3.0 / 6) < 1e-9       # level 0 = level 1
        assert abs(bc.get_daily_wear("bio_farm", 10) - 3.0 / 30) < 1e-9
        assert abs(bc.get_daily_wear("bio_farm", 5) - 3.0 / 12) < 1e-9      # empty level → the type value
        assert bc.get_business_config_entry("bio_farm")["durability"]["shifts_by_level"] == {"1": 6.0, "10": 30.0}
        bc.apply_durability_override("bio_farm", None, None, None, {})       # cleared
        assert abs(bc.get_daily_wear("bio_farm", 1) - 3.0 / bc.DEFAULT_SHIFTS_PER_100) < 1e-9
    finally:
        bc.DURABILITY_OVERRIDES.clear(); bc.DURABILITY_OVERRIDES.update(saved)
