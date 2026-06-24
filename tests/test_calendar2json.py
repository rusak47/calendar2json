import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calendar2json import parse_years, load_region_config


class TestParseYears:
    def test_single_year(self):
        assert parse_years("2026") == [2026]

    def test_range(self):
        assert parse_years("2025-2027") == [2025, 2026, 2027]

    def test_single_year_range(self):
        assert parse_years("2026-2026") == [2026]

    def test_comma_separated(self):
        assert parse_years("2026,2028,2030") == [2026, 2028, 2030]

    def test_comma_with_spaces(self):
        assert parse_years("2026, 2028, 2030") == [2026, 2028, 2030]


class TestLoadRegionConfig:
    def test_loads_lv(self):
        config = load_region_config("LV")
        assert config["code"] == "LV"
        assert "pre_holiday_short_hours" in config
        assert "swaps" in config

    def test_loads_lowercase(self):
        config = load_region_config("lv")
        assert config["code"] == "LV"

    def test_missing_region_returns_empty(self):
        config = load_region_config("XX")
        assert config == {}
