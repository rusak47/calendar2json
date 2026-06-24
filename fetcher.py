import json
import logging
from datetime import date
from json import JSONDecodeError
from urllib.request import urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


class HolidayEntry:
    def __init__(self, date_str, name, local_name=None, observed_date=None,
                 is_observed_shifted=False, holiday_type="national"):
        self.date = date_str
        self.name = name
        self.local_name = local_name or name
        self.observed_date = observed_date or date_str
        self.is_observed_shifted = is_observed_shifted
        self.type = holiday_type

    def to_dict(self):
        return {
            "date": self.date,
            "name": self.name,
            "local_name": self.local_name,
            "observed_date": self.observed_date,
            "is_observed_shifted": self.is_observed_shifted,
            "type": self.type,
        }


def fetch_from_holidays_lib(region, years):
    import holidays

    lv = holidays.country_holidays(region, years=years)
    results = {}
    for dt, name in sorted(lv.items()):
        d = str(dt)
        # Check if it's a swapped day (pārcelta)
        is_swapped = "pārcelta" in name.lower()
        is_observed = "(brīvdiena)" in name.lower()
        entry = HolidayEntry(
            date_str=d,
            name=name,
            local_name=name,
            observed_date=d,
            is_observed_shifted=is_observed or is_swapped,
        )
        results[d] = entry
    return results


def fetch_from_tallyfy(region, years):
    results = {}
    for year in years:
        url = f"https://tallyfy.com/national-holidays/api/{region.upper()}/{year}.json"
        try:
            with urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
        except (URLError, JSONDecodeError) as e:
            logger.warning("Tallyfy fetch failed for %s %s: %s", region, year, e)
            continue

        for h in data.get("holidays", []):
            d = h["date"]
            entry = HolidayEntry(
                date_str=d,
                name=h["name"],
                local_name=h.get("local_name", h["name"]),
                observed_date=h.get("observed_date", d),
                is_observed_shifted=h.get("is_observed_shifted", False),
                holiday_type=h.get("type", "national"),
            )
            results[d] = entry
    return results


def fetch_holidays(region, years, source="auto"):
    if source == "tallyfy":
        return fetch_from_tallyfy(region, years)
    if source == "holidays":
        return fetch_from_holidays_lib(region, years)

    try:
        return fetch_from_holidays_lib(region, years)
    except Exception as e:
        logger.warning("holidays lib failed, falling back to Tallyfy: %s", e)
        return fetch_from_tallyfy(region, years)
