from unittest.mock import patch

import pytest

from fetcher import HolidayEntry, fetch_from_holidays_lib


class TestHolidayEntry:
    def test_defaults(self):
        e = HolidayEntry(date_str="2026-01-01", name="Jaungada diena")
        assert e.date == "2026-01-01"
        assert e.name == "Jaungada diena"
        assert e.local_name == "Jaungada diena"
        assert e.observed_date == "2026-01-01"
        assert e.is_observed_shifted is False
        assert e.type == "national"

    def test_explicit_local_name(self):
        e = HolidayEntry(
            date_str="2026-01-01",
            name="New Year's Day",
            local_name="Jaungada diena",
            observed_date="2026-01-01",
            is_observed_shifted=False,
            holiday_type="public",
        )
        assert e.local_name == "Jaungada diena"
        assert e.type == "public"

    def test_to_dict(self):
        e = HolidayEntry(date_str="2026-01-01", name="Jaungada diena")
        d = e.to_dict()
        assert d["date"] == "2026-01-01"
        assert d["name"] == "Jaungada diena"
        assert d["local_name"] == "Jaungada diena"
        assert d["observed_date"] == "2026-01-01"
        assert d["is_observed_shifted"] is False


class TestFetchFromHolidaysLib:
    def test_returns_dict(self):
        result = fetch_from_holidays_lib("LV", [2026])
        assert isinstance(result, dict)

    def test_all_entries_are_holidayentry(self):
        result = fetch_from_holidays_lib("LV", [2026])
        for v in result.values():
            assert isinstance(v, HolidayEntry)

    def test_contains_key_holidays(self):
        result = fetch_from_holidays_lib("LV", [2026])
        assert "2026-01-01" in result
        assert "2026-06-23" in result
        assert "2026-06-24" in result
        assert "2026-12-31" in result

    def test_swap_entries_present(self):
        result = fetch_from_holidays_lib("LV", [2026])
        assert "2026-01-02" in result
        assert "pārcelta" in result["2026-01-02"].name.lower()

    def test_multi_year(self):
        result = fetch_from_holidays_lib("LV", [2025, 2026])
        years = {int(d[:4]) for d in result}
        assert 2025 in years
        assert 2026 in years
        assert len(years) == 2

    def test_different_region(self):
        result = fetch_from_holidays_lib("DE", [2026])
        assert "2026-01-01" in result
        assert "2026-10-03" in result


class TestComputeNthWeekday:
    def test_first_sunday_of_december_2026(self):
        from fetcher import _compute_nth_weekday
        d = _compute_nth_weekday(2026, 12, 6, 1)
        assert d.weekday() == 6
        assert d.month == 12
        assert d.day == 6
        assert str(d) == "2026-12-06"

    def test_third_sunday_of_june_2026(self):
        from fetcher import _compute_nth_weekday
        d = _compute_nth_weekday(2026, 6, 6, 3)
        assert d.weekday() == 6
        assert d.month == 6
        assert 14 <= d.day <= 21
        assert str(d) == "2026-06-21"

    def test_second_saturday_of_july_2026(self):
        from fetcher import _compute_nth_weekday
        d = _compute_nth_weekday(2026, 7, 5, 2)
        assert d.weekday() == 5
        assert d.month == 7
        assert 8 <= d.day <= 14
        assert str(d) == "2026-07-11"

    def test_second_sunday_of_september_2026(self):
        from fetcher import _compute_nth_weekday
        d = _compute_nth_weekday(2026, 9, 6, 2)
        assert d.weekday() == 6
        assert d.month == 9
        assert 8 <= d.day <= 14
        assert str(d) == "2026-09-13"


class TestLoadMemoriamDates:
    def test_loads_from_yaml(self):
        from fetcher import load_memoriam_dates
        region_config = {"memoriam": {"source": "https://likumi.lv/ta/id/72608"}}
        result = load_memoriam_dates("LV", region_config, [2026])
        assert isinstance(result, dict)
        assert "2026-01-20" in result
        assert result["2026-01-20"]["name"] == "1991. gada barikāžu aizstāvju atceres diena"

    def test_includes_floating_dates(self):
        from fetcher import load_memoriam_dates
        region_config = {"memoriam": {"source": "https://likumi.lv/ta/id/72608"}}
        result = load_memoriam_dates("LV", region_config, [2026])
        assert "2026-06-21" in result
        assert result["2026-06-21"]["name"] == "Medicīnas darbinieku diena"
        assert "2026-07-11" in result
        assert "2026-09-13" in result
        assert "2026-12-06" in result

    def test_multi_year(self):
        from fetcher import load_memoriam_dates
        region_config = {"memoriam": {"source": "https://likumi.lv/ta/id/72608"}}
        result = load_memoriam_dates("LV", region_config, [2025, 2026, 2027])
        years = {int(d[:4]) for d in result}
        assert 2025 in years
        assert 2026 in years
        assert 2027 in years
        assert len(years) == 3

    def test_2026_count(self):
        from fetcher import load_memoriam_dates
        region_config = {"memoriam": {"source": "https://likumi.lv/ta/id/72608"}}
        result = load_memoriam_dates("LV", region_config, [2026])
        assert len(result) == 34

    def test_empty_yaml_returns_empty(self, tmp_path):
        from fetcher import load_memoriam_dates
        import os
        empty_path = tmp_path / "de-memoriam.yaml"
        empty_path.write_text("")
        region_config = {"memoriam": {"source": "https://example.com"}}
        with patch("fetcher.REGIONS_DIR", str(tmp_path)):
            result = load_memoriam_dates("DE", region_config, [2026])
        assert result == {}

    def test_no_file_no_url_returns_empty(self, tmp_path):
        from fetcher import load_memoriam_dates
        region_config = {}
        with patch("fetcher.REGIONS_DIR", str(tmp_path)):
            result = load_memoriam_dates("XX", region_config, [2026])
        assert result == {}

    def test_fixed_date_differs_by_year(self):
        from fetcher import load_memoriam_dates
        region_config = {"memoriam": {"source": "https://likumi.lv/ta/id/72608"}}
        result_2025 = load_memoriam_dates("LV", region_config, [2025])
        result_2026 = load_memoriam_dates("LV", region_config, [2026])
        assert "2025-01-20" in result_2025
        assert "2026-01-20" in result_2026
        assert "2025-01-20" not in result_2026

    def test_floating_date_differs_by_year(self):
        from fetcher import load_memoriam_dates
        region_config = {"memoriam": {"source": "https://likumi.lv/ta/id/72608"}}
        result_2025 = load_memoriam_dates("LV", region_config, [2025])
        result_2026 = load_memoriam_dates("LV", region_config, [2026])
        assert result_2025["2025-12-07"]["name"] == result_2026["2026-12-06"]["name"]

    def test_memoriam_only_days_have_correct_type(self):
        import holidays as hlib
        from fetcher import load_memoriam_dates, fetch_from_holidays_lib
        from rules import build_calendar
        lv = fetch_from_holidays_lib("LV", [2026])
        config = {
            "pre_holiday_short_hours": 7,
            "swaps": {"2026": {"01-02": "01-17", "06-22": "06-27"}},
            "observance_shifts": [
                {"holiday": "05-04", "label": "Latvijas Republikas Neatkarības atjaunošanas diena"},
                {"holiday": "11-18", "label": "Latvijas Republikas Proklamēšanas diena"},
            ],
            "memoriam": {"source": "https://likumi.lv/ta/id/72608"},
        }
        region_config = config
        mem = load_memoriam_dates("LV", region_config, [2026])
        cal = build_calendar(lv, config, 2026, memoriam_dates=mem)
        jan20 = cal.get("2026-01-20")
        assert jan20 is not None
        assert jan20.get("is_memoriam") is True

    def test_no_is_memoriam_field_on_non_memoriam(self):
        import holidays as hlib
        from fetcher import load_memoriam_dates, fetch_from_holidays_lib
        from rules import build_calendar
        lv = fetch_from_holidays_lib("LV", [2026])
        config = {
            "pre_holiday_short_hours": 7,
            "swaps": {"2026": {"01-02": "01-17", "06-22": "06-27"}},
            "observance_shifts": [
                {"holiday": "05-04", "label": "Neatkarības atjaunošanas diena"},
                {"holiday": "11-18", "label": "Proklamēšanas diena"},
            ],
            "memoriam": {"source": "https://likumi.lv/ta/id/72608"},
        }
        mem = load_memoriam_dates("LV", config, [2026])
        cal = build_calendar(lv, config, 2026, memoriam_dates=mem)
        assert "is_memoriam" not in cal["2026-01-01"]
        assert "is_memoriam" not in cal["2026-04-02"]
