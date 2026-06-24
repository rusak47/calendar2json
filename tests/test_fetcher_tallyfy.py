import json
import logging
from unittest.mock import patch, MagicMock

import pytest
from urllib.error import URLError

from fetcher import fetch_from_tallyfy, fetch_holidays, HolidayEntry


def _mock_urlopen_response(data, status=200):
    resp = MagicMock()
    resp.__enter__.return_value = resp
    resp.read.return_value = json.dumps(data).encode()
    resp.status = status
    return resp


TALLYFY_HOLIDAYS_2026 = {
    "holidays": [
        {
            "date": "2026-01-01",
            "name": "New Year's Day",
            "local_name": "Jaungada diena",
            "type": "national",
        },
        {
            "date": "2026-06-23",
            "name": "Midsummer Eve",
            "local_name": "Līgo diena",
            "type": "national",
        },
    ]
}

TALLYFY_HOLIDAYS_2026_NO_OPTIONALS = {
    "holidays": [
        {
            "date": "2026-01-01",
            "name": "Jaungada diena",
        },
    ]
}

TALLYFY_HOLIDAYS_2026_WITH_OBSERVED = {
    "holidays": [
        {
            "date": "2030-05-04",
            "name": "Restoration of Independence day",
            "local_name": "Latvijas Republikas Neatkarības atjaunošanas diena",
            "observed_date": "2030-05-06",
            "is_observed_shifted": True,
            "type": "national",
        },
    ]
}


class TestFetchFromTallyfy:
    @patch("fetcher.urlopen")
    def test_returns_holiday_entries(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_response(TALLYFY_HOLIDAYS_2026)
        result = fetch_from_tallyfy("LV", [2026])

        assert len(result) == 2
        assert "2026-01-01" in result
        assert "2026-06-23" in result

        e = result["2026-01-01"]
        assert isinstance(e, HolidayEntry)
        assert e.name == "New Year's Day"
        assert e.local_name == "Jaungada diena"
        assert e.observed_date == "2026-01-01"
        assert e.type == "national"

    @patch("fetcher.urlopen")
    def test_handles_404_gracefully(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Not Found")
        result = fetch_from_tallyfy("LV", [2025])
        assert result == {}

    @patch("fetcher.urlopen")
    def test_handles_404_continues_to_next_year(self, mock_urlopen):
        mock_404 = URLError("Not Found")
        mock_ok = _mock_urlopen_response(TALLYFY_HOLIDAYS_2026)
        mock_urlopen.side_effect = [mock_404, mock_ok]

        result = fetch_from_tallyfy("LV", [2025, 2026])
        assert "2026-01-01" in result
        assert len(result) == 2

    @patch("fetcher.urlopen")
    def test_observed_date_field(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_response(TALLYFY_HOLIDAYS_2026_WITH_OBSERVED)
        result = fetch_from_tallyfy("LV", [2030])
        e = result["2030-05-04"]
        assert e.observed_date == "2030-05-06"
        assert e.is_observed_shifted is True

    @patch("fetcher.urlopen")
    def test_missing_optional_fields(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_response(TALLYFY_HOLIDAYS_2026_NO_OPTIONALS)
        result = fetch_from_tallyfy("LV", [2026])
        e = result["2026-01-01"]
        assert e.local_name == "Jaungada diena"
        assert e.observed_date == "2026-01-01"
        assert e.is_observed_shifted is False
        assert e.type == "national"

    @patch("fetcher.urlopen")
    def test_empty_holidays_list(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_response({"holidays": []})
        result = fetch_from_tallyfy("LV", [2026])
        assert result == {}

    @patch("fetcher.urlopen")
    def test_malformed_json(self, mock_urlopen):
        resp = MagicMock()
        resp.__enter__.return_value = resp
        resp.read.return_value = b"not json"
        mock_urlopen.return_value = resp

        result = fetch_from_tallyfy("LV", [2026])
        assert result == {}
        assert len(result) == 0


class TestFetchHolidaysFallback:
    @patch("fetcher.fetch_from_holidays_lib")
    @patch("fetcher.fetch_from_tallyfy")
    def test_auto_tries_holidays_first(self, mock_tallyfy, mock_holidays):
        mock_holidays.return_value = {"2026-01-01": HolidayEntry("2026-01-01", "Test")}
        result = fetch_holidays("LV", [2026], source="auto")
        mock_holidays.assert_called_once()
        mock_tallyfy.assert_not_called()
        assert "2026-01-01" in result

    @patch("fetcher.fetch_from_holidays_lib")
    @patch("fetcher.fetch_from_tallyfy")
    def test_falls_back_to_tallyfy(self, mock_tallyfy, mock_holidays):
        mock_holidays.side_effect = Exception("no data")
        mock_tallyfy.return_value = {"2026-01-01": HolidayEntry("2026-01-01", "Test")}
        result = fetch_holidays("LV", [2026], source="auto")
        mock_holidays.assert_called_once()
        mock_tallyfy.assert_called_once()
        assert "2026-01-01" in result

    @patch("fetcher.fetch_from_holidays_lib")
    @patch("fetcher.fetch_from_tallyfy")
    def test_explicit_tallyfy_source(self, mock_tallyfy, mock_holidays):
        mock_tallyfy.return_value = {"2026-01-01": HolidayEntry("2026-01-01", "Tallyfy")}
        result = fetch_holidays("LV", [2026], source="tallyfy")
        mock_holidays.assert_not_called()
        mock_tallyfy.assert_called_once()
        assert result["2026-01-01"].name == "Tallyfy"

    @patch("fetcher.fetch_from_holidays_lib")
    @patch("fetcher.fetch_from_tallyfy")
    def test_explicit_holidays_source(self, mock_tallyfy, mock_holidays):
        mock_holidays.return_value = {"2026-01-01": HolidayEntry("2026-01-01", "Holidays Lib")}
        result = fetch_holidays("LV", [2026], source="holidays")
        mock_holidays.assert_called_once()
        mock_tallyfy.assert_not_called()
        assert result["2026-01-01"].name == "Holidays Lib"
