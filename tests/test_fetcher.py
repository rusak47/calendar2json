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
