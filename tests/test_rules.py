import pytest
from datetime import date

from rules import (
    _parse_date,
    _fmt,
    _real_holiday_dates,
    compute_short_days,
    extract_swaps_from_holiday_names,
    apply_swaps,
    apply_observance,
    build_calendar,
)
from fetcher import HolidayEntry


def _entry(date_str, name, **kwargs):
    return HolidayEntry(date_str=date_str, name=name, **kwargs)


def _lv_holidays_dict(holidays_lib_items):
    results = {}
    for dt, name in sorted(holidays_lib_items):
        d = str(dt)
        results[d] = HolidayEntry(
            date_str=d,
            name=name,
            local_name=name,
            observed_date=d,
            is_observed_shifted="pārcelta" in name.lower() or "(brīvdiena)" in name.lower(),
        )
    return results


class TestRealHolidayDates:
    def test_excludes_swaps(self):
        holidays = {
            "2026-01-01": _entry("2026-01-01", "Jaungada diena"),
            "2026-01-02": _entry("2026-01-02", "Brīvdiena (pārcelta no 17.01.2026)"),
            "2026-06-23": _entry("2026-06-23", "Līgo diena"),
            "2026-06-24": _entry("2026-06-24", "Jāņu diena"),
        }
        result = _real_holiday_dates(holidays, 2026)
        assert date(2026, 1, 1) in result
        assert date(2026, 1, 2) not in result
        assert date(2026, 6, 23) in result
        assert date(2026, 6, 24) in result
        assert len(result) == 3

    def test_filters_by_year(self):
        holidays = {
            "2025-12-31": _entry("2025-12-31", "Vecgada diena"),
            "2026-01-01": _entry("2026-01-01", "Jaungada diena"),
        }
        result = _real_holiday_dates(holidays, 2026)
        assert date(2026, 1, 1) in result
        assert date(2025, 12, 31) not in result
        assert len(result) == 1


class TestComputeShortDays:
    def test_no_short_hours_returns_empty(self):
        holidays = {"2026-04-03": _entry("2026-04-03", "Lielā Piektdiena")}
        config = {}
        assert compute_short_days(holidays, config, 2026) == {}

    def test_workday_before_holiday_is_short(self):
        holidays = {
            "2026-04-03": _entry("2026-04-03", "Lielā Piektdiena"),
        }
        config = {"pre_holiday_short_hours": 7}
        result = compute_short_days(holidays, config, 2026)
        assert _parse_date("2026-04-02").weekday() < 5
        assert "2026-04-02" in result
        assert result["2026-04-02"]["type"] == "pre_holiday_short"
        assert result["2026-04-02"]["note"] == "Pirmssvētku diena"

    def test_holiday_itself_not_short(self):
        holidays = {
            "2026-06-23": _entry("2026-06-23", "Līgo diena"),
            "2026-06-24": _entry("2026-06-24", "Jāņu diena"),
        }
        config = {"pre_holiday_short_hours": 7}
        result = compute_short_days(holidays, config, 2026)
        assert "2026-06-23" not in result
        assert "2026-06-24" not in result

    def test_swapped_day_off_not_short(self):
        holidays = {
            "2026-06-22": _entry("2026-06-22", "Brīvdiena (pārcelta no 27.06.2026)"),
            "2026-06-23": _entry("2026-06-23", "Līgo diena"),
            "2026-06-24": _entry("2026-06-24", "Jāņu diena"),
        }
        config = {"pre_holiday_short_hours": 7}
        result = compute_short_days(holidays, config, 2026)
        assert "2026-06-22" not in result

    def test_cross_year_short_day_excluded(self):
        holidays = {
            "2026-01-01": _entry("2026-01-01", "Jaungada diena"),
            "2025-12-31": _entry("2025-12-31", "Vecgada diena"),
        }
        config = {"pre_holiday_short_hours": 7}
        result = compute_short_days(holidays, config, 2026)
        assert "2025-12-31" not in result

    def test_multiple_short_days(self):
        holidays = {
            "2026-04-03": _entry("2026-04-03", "Lielā Piektdiena"),
            "2026-05-01": _entry("2026-05-01", "Darba svētki"),
            "2026-11-18": _entry("2026-11-18", "Proklamēšanas diena"),
        }
        config = {"pre_holiday_short_hours": 7}
        result = compute_short_days(holidays, config, 2026)
        assert "2026-04-02" in result
        assert "2026-04-30" in result
        assert "2026-11-17" in result

    def test_weekend_before_holiday_not_short(self):
        holidays = {
            "2026-05-04": _entry("2026-05-04", "Neatkarības atjaunošanas diena"),
        }
        config = {"pre_holiday_short_hours": 7}
        result = compute_short_days(holidays, config, 2026)
        day = _parse_date("2026-05-03")
        assert day.weekday() >= 5
        assert "2026-05-03" not in result


class TestExtractSwapsFromHolidayNames:
    def test_detects_swap(self):
        holidays = {
            "2026-01-02": _entry("2026-01-02", "Brīvdiena (pārcelta no 17.01.2026)"),
        }
        swaps = extract_swaps_from_holiday_names(holidays, 2026)
        assert swaps == {"2026-01-02": "2026-01-17"}

    def test_skips_non_swap_holidays(self):
        holidays = {
            "2026-01-01": _entry("2026-01-01", "Jaungada diena"),
            "2026-06-23": _entry("2026-06-23", "Līgo diena"),
        }
        swaps = extract_swaps_from_holiday_names(holidays, 2026)
        assert swaps == {}

    def test_filters_by_swap_year(self):
        holidays = {
            "2025-01-02": _entry("2025-01-02", "Brīvdiena (pārcelta no 10.05.2025)"),
            "2026-01-02": _entry("2026-01-02", "Brīvdiena (pārcelta no 17.01.2026)"),
        }
        swaps = extract_swaps_from_holiday_names(holidays, 2026)
        assert "2025-01-02" not in swaps
        assert swaps["2026-01-02"] == "2026-01-17"

    def test_cross_year_swap(self):
        holidays = {
            "2026-01-02": _entry("2026-01-02", "Brīvdiena (pārcelta no 17.01.2026)"),
        }
        swaps = extract_swaps_from_holiday_names(holidays, 2026)
        assert swaps["2026-01-02"] == "2026-01-17"


class TestApplySwaps:
    def test_yaml_override(self):
        holidays = {}
        config = {"swaps": {"2026": {"01-02": "01-17"}}}
        result = apply_swaps(holidays, config, 2026)
        assert "2026-01-02" in result
        assert result["2026-01-02"]["type"] == "swapped_day_off"
        assert "2026-01-17" in result
        assert result["2026-01-17"]["type"] == "swapped_workday"

    def test_detected_from_holiday_name(self):
        holidays = {
            "2026-01-02": _entry("2026-01-02", "Brīvdiena (pārcelta no 17.01.2026)"),
        }
        config = {"swaps": {}}
        result = apply_swaps(holidays, config, 2026)
        assert "2026-01-02" in result
        assert "2026-01-17" in result

    def test_yaml_overrides_detected(self):
        holidays = {
            "2026-01-02": _entry("2026-01-02", "Brīvdiena (pārcelta no 17.01.2026)"),
        }
        config = {"swaps": {"2026": {"01-02": "01-24"}}}
        result = apply_swaps(holidays, config, 2026)
        assert "2026-01-17" not in result
        assert result["2026-01-02"]["swap_source"] == "2026-01-24"
        assert result["2026-01-24"]["swap_source"] == "2026-01-02"

    def test_empty_config_no_swaps(self):
        config = {"swaps": {}}
        result = apply_swaps({}, config, 2026)
        assert result == {}

    def test_no_swaps_for_year(self):
        config = {"swaps": {"2025": {"05-02": "05-10"}}}
        result = apply_swaps({}, config, 2026)
        assert result == {}


class TestApplyObservance:
    def test_weekday_holiday_no_shift(self):
        holidays = {
            "2026-05-04": _entry("2026-05-04", "Neatkarības atjaunošanas diena"),
        }
        config = {
            "observance_shifts": [
                {"holiday": "05-04", "label": "Neatkarības atjaunošanas diena"},
            ]
        }
        result = apply_observance(holidays, config, 2026)
        assert result == {}

    def test_weekend_holiday_shifts_to_monday(self):
        holidays = {
            "2030-05-04": _entry("2030-05-04", "Neatkarības atjaunošanas diena"),
        }
        config = {
            "observance_shifts": [
                {"holiday": "05-04", "label": "Neatkarības atjaunošanas diena"},
            ]
        }
        result = apply_observance(holidays, config, 2030)
        assert "2030-05-06" in result
        assert result["2030-05-06"]["type"] == "observed_holiday"
        assert result["2030-05-06"]["source_date"] == "2030-05-04"

    def test_sunday_holiday_shifts_to_monday(self):
        holidays = {
            "2031-05-04": _entry("2031-05-04", "Neatkarības atjaunošanas diena"),
        }
        config = {
            "observance_shifts": [
                {"holiday": "05-04", "label": "Neatkarības atjaunošanas diena"},
            ]
        }
        result = apply_observance(holidays, config, 2031)
        day = _parse_date("2031-05-04")
        assert day.weekday() == 6
        assert "2031-05-05" in result
        assert result["2031-05-05"]["type"] == "observed_holiday"

    def test_no_shifts_if_not_in_holidays(self):
        config = {
            "observance_shifts": [
                {"holiday": "05-04", "label": "Neatkarības atjaunošanas diena"},
            ]
        }
        result = apply_observance({}, config, 2026)
        assert result == {}

    def test_empty_config_no_shifts(self):
        config = {"observance_shifts": []}
        result = apply_observance({}, config, 2026)
        assert result == {}


class TestBuildCalendarIntegration:
    def test_2026_full_calendar(self):
        import holidays as hlib
        lv = hlib.country_holidays("LV", years=2026)
        holidays = _lv_holidays_dict(lv.items())
        config = {
            "pre_holiday_short_hours": 7,
            "swaps": {"2026": {"01-02": "01-17", "06-22": "06-27"}},
            "observance_shifts": [
                {"holiday": "05-04", "label": "Latvijas Republikas Neatkarības atjaunošanas diena"},
                {"holiday": "11-18", "label": "Latvijas Republikas Proklamēšanas diena"},
            ],
        }
        cal = build_calendar(holidays, config, 2026)

        assert "2026-01-01" in cal
        assert cal["2026-01-01"]["type"] == "holiday"

        assert "2026-01-02" in cal
        assert cal["2026-01-02"]["type"] == "swapped_day_off"
        assert "2026-01-17" in cal
        assert cal["2026-01-17"]["type"] == "swapped_workday"

        for d in ["2026-04-02", "2026-04-30", "2026-11-17", "2026-12-23", "2026-12-30"]:
            assert d in cal, f"missing short day {d}"
            assert cal[d]["type"] == "pre_holiday_short"

        for d in ["2026-06-23", "2026-06-24"]:
            assert "pre_holiday_short" != cal.get(d, {}).get("type")

        assert "work_hours" not in cal["2026-01-01"]

    def test_2025_full_calendar_with_observance(self):
        import holidays as hlib
        lv = hlib.country_holidays("LV", years=2025)
        holidays = _lv_holidays_dict(lv.items())
        config = {
            "pre_holiday_short_hours": 7,
            "swaps": {"2025": {"05-02": "05-10", "11-17": "11-08"}},
            "observance_shifts": [
                {"holiday": "05-04", "label": "Latvijas Republikas Neatkarības atjaunošanas diena"},
                {"holiday": "11-18", "label": "Latvijas Republikas Proklamēšanas diena"},
            ],
        }
        cal = build_calendar(holidays, config, 2025)

        assert "2025-05-04" in cal
        assert "2025-05-05" in cal
        assert cal["2025-05-05"]["type"] == "observed_holiday"

        assert "2025-11-17" in cal
        assert cal["2025-11-17"]["type"] == "swapped_day_off"
        assert "2025-11-08" in cal
        assert cal["2025-11-08"]["type"] == "swapped_workday"

    def test_2030_observance_on_weekend(self):
        import holidays as hlib
        lv = hlib.country_holidays("LV", years=2030)
        holidays = _lv_holidays_dict(lv.items())
        config = {
            "pre_holiday_short_hours": 7,
            "swaps": {},
            "observance_shifts": [
                {"holiday": "05-04", "label": "Latvijas Republikas Neatkarības atjaunošanas diena"},
                {"holiday": "11-18", "label": "Latvijas Republikas Proklamēšanas diena"},
            ],
        }
        cal = build_calendar(holidays, config, 2030)

        assert "2030-05-04" in cal
        assert cal["2030-05-04"]["type"] == "holiday"
        assert "2030-05-06" in cal
        assert cal["2030-05-06"]["type"] == "observed_holiday"

        assert "work_hours" not in cal["2030-05-04"]

    def test_2028_observance_on_saturday(self):
        import holidays as hlib
        lv = hlib.country_holidays("LV", years=2028)
        holidays = _lv_holidays_dict(lv.items())
        config = {
            "pre_holiday_short_hours": 7,
            "swaps": {},
            "observance_shifts": [
                {"holiday": "05-04", "label": "Latvijas Republikas Neatkarības atjaunošanas diena"},
                {"holiday": "11-18", "label": "Latvijas Republikas Proklamēšanas diena"},
            ],
        }
        cal = build_calendar(holidays, config, 2028)

        assert "2028-11-18" in cal
        assert cal["2028-11-18"]["type"] == "holiday"
        assert "2028-11-20" in cal
        assert cal["2028-11-20"]["type"] == "observed_holiday"

    def test_no_work_hours_in_any_entry(self):
        import holidays as hlib
        lv = hlib.country_holidays("LV", years=[2025, 2026, 2028, 2030])
        holidays = _lv_holidays_dict(lv.items())
        config = {
            "pre_holiday_short_hours": 7,
            "swaps": {"2025": {"05-02": "05-10", "11-17": "11-08"},
                       "2026": {"01-02": "01-17", "06-22": "06-27"}},
            "observance_shifts": [
                {"holiday": "05-04", "label": "Neatkarības atjaunošanas diena"},
                {"holiday": "11-18", "label": "Proklamēšanas diena"},
            ],
        }
        for year in [2025, 2026, 2028, 2030]:
            cal = build_calendar(holidays, config, year)
            for d, entry in cal.items():
                assert "work_hours" not in entry, f"{d}: work_hours still present"
