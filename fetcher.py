import json
import logging
import os
import re
from datetime import date, timedelta
from json import JSONDecodeError
from urllib.request import urlopen
from urllib.error import URLError

import yaml

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGIONS_DIR = os.path.join(SCRIPT_DIR, "regions")

# Parse likumi.lv law text format: "DD. month — name;"
LIKUMI_DATE_RE = re.compile(
    r"(\d{1,2})\.\s*"
    r"(janvāri|februāri|martu|aprīli|maiju|jūniju|jūliju|augustu|septembri|oktobri|novembri|decembri)"
    r"\s*[—–-]\s*(.+?)(?:;|$)"
)

MONTH_MAP = {
    "janvāri": 1, "februāri": 2, "martu": 3, "aprīli": 4,
    "maiju": 5, "jūniju": 6, "jūliju": 7, "augustu": 8,
    "septembri": 9, "oktobri": 10, "novembri": 11, "decembri": 12,
}


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


def _compute_nth_weekday(year, month, weekday, ordinal):
    """Return date of the nth occurrence of a weekday in a month.
    weekday: 0=Monday, 6=Sunday.  ordinal: 1=first, 2=second, etc."""
    d = date(year, month, 1)
    days_ahead = weekday - d.weekday()
    if days_ahead < 0:
        days_ahead += 7
    d += timedelta(days=days_ahead)
    d += timedelta(weeks=ordinal - 1)
    return d


def _parse_likumi_page(html_text):
    """Extract fixed commemorative dates from likumi.lv HTML."""
    dates = {}
    found_article_2 = False
    for line in html_text.splitlines():
        if "Noteikt par atceres un atzīmējamām dienām" in line:
            found_article_2 = True
            continue
        if not found_article_2:
            continue
        if "3." in line and "(" in line:
            break
        for m in LIKUMI_DATE_RE.finditer(line):
            day = int(m.group(1))
            month = MONTH_MAP.get(m.group(2))
            name = m.group(3).strip().rstrip(";")
            if month:
                key = f"{month:02d}-{day:02d}"
                dates[key] = {"name": name}
    return dates


def _fetch_memoriam_from_likumi(url):
    """Fetch and parse commemorative dates from likumi.lv."""
    try:
        with urlopen(url, timeout=15) as resp:
            html = resp.read().decode("utf-8")
        return _parse_likumi_page(html)
    except (URLError, OSError) as e:
        logger.warning("Failed to fetch memoriam dates from %s: %s", url, e)
        return {}


def load_memoriam_dates(region_code, region_config, years):
    """Load commemorative dates for a region.

    Priority:
    1. {code}-memoriam.yaml in regions dir (primary source)
    2. If file missing, fetch from memoriam.source URL in region config
    3. Empty file → no memoriam dates

    Returns dict of {date_str: {name: str}} for all given years,
    including computed floating dates.
    """
    path = os.path.join(REGIONS_DIR, f"{region_code.lower()}-memoriam.yaml")

    memoriam_data = None

    if os.path.exists(path):
        with open(path) as f:
            content = f.read().strip()
        if not content:
            logger.info("%s is empty — no memoriam dates for %s", path, region_code.upper())
            return {}
        memoriam_data = yaml.safe_load(content)
        if not memoriam_data or (not memoriam_data.get("fixed") and not memoriam_data.get("floating")):
            return {}
    else:
        url = region_config.get("memoriam", {}).get("source")
        if not url:
            logger.info("No memoriam file (%s) and no memoriam.source URL — skipping", path)
            return {}
        logger.info("Memoriam file %s not found, fetching from %s", path, url)
        fixed_dates = _fetch_memoriam_from_likumi(url)
        if not fixed_dates:
            return {}
        memoriam_data = {"fixed": fixed_dates, "floating": []}

    results = {}
    for year in years:
        if memoriam_data.get("fixed"):
            for mmdd, info in memoriam_data["fixed"].items():
                parts = mmdd.split("-")
                month, day = int(parts[0]), int(parts[1])
                d = date(year, month, day)
                d_str = d.strftime("%Y-%m-%d")
                results[d_str] = {
                    "name": info["name"],
                    "name_en": info.get("name_en", ""),
                }
        if memoriam_data.get("floating"):
            for rule in memoriam_data["floating"]:
                d = _compute_nth_weekday(year, rule["month"], rule["weekday"], rule["ordinal"])
                d_str = d.strftime("%Y-%m-%d")
                results[d_str] = {
                    "name": rule["name"],
                }

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
