import re
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

SWAP_PARSE = re.compile(r"pārcelta no (\d{2})\.(\d{2})\.(\d{4})")


def _parse_date(d_str):
    parts = d_str.split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def _fmt(d):
    return d.strftime("%Y-%m-%d")


def _real_holiday_dates(holidays, year):
    """Return set of dates that are actual holidays (not swapped-day entries)."""
    dates = set()
    for d_str, entry in holidays.items():
        if "pārcelta" in entry.name.lower():
            continue
        dt = _parse_date(d_str)
        if dt.year == year:
            dates.add(dt)
    return dates


def compute_short_days(holidays, region_config, year):
    short_hours = region_config.get("pre_holiday_short_hours")
    if not short_hours:
        return {}

    all_holiday_dates = set(
        _parse_date(d) for d, e in holidays.items()
        if _parse_date(d).year == year
    )

    results = {}
    for h_date in sorted(_real_holiday_dates(holidays, year)):
        prev = h_date - timedelta(days=1)
        if prev.year != year:
            continue
        p_fmt = _fmt(prev)
        if prev.weekday() < 5 and prev not in all_holiday_dates:
            results[p_fmt] = {
                "type": "pre_holiday_short",
                "note": "Pirmssvētku diena",
            }

    return results


def extract_swaps_from_holiday_names(holidays, year):
    swaps = {}
    for d_str, entry in holidays.items():
        m = SWAP_PARSE.search(entry.name)
        if m:
            swap_day = int(m.group(1))
            swap_month = int(m.group(2))
            swap_year = int(m.group(3))
            if swap_year == year:
                dst = f"{year}-{swap_month:02d}-{swap_day:02d}"
                swaps[d_str] = dst
    return swaps


def apply_swaps(holidays, region_config, year):
    override_swaps = {}
    year_swaps = region_config.get("swaps", {}).get(str(year), {})
    for src, dst in year_swaps.items():
        src_full = f"{year}-{src}"
        dst_full = f"{year}-{dst}"
        override_swaps[src_full] = dst_full

    detected = extract_swaps_from_holiday_names(holidays, year)

    for src, dst in detected.items():
        if src not in override_swaps:
            override_swaps[src] = dst

    results = {}
    for src, dst in override_swaps.items():
        src_dt = _parse_date(src)
        dst_dt = _parse_date(dst)

        results[src] = {
            "type": "swapped_day_off",
            "swap_source": dst,
            "note": f"Darba diena pārcelta uz {dst_dt.strftime('%d.%m.%Y')}",
        }

        results[dst] = {
            "type": "swapped_workday",
            "swap_source": src,
            "note": f"Pārceltā darba diena no {src_dt.strftime('%d.%m.%Y')}",
        }

    return results


def apply_observance(holidays, region_config, year):
    shifts = region_config.get("observance_shifts", [])
    if not shifts:
        return {}

    results = {}
    for rule in shifts:
        month_day = rule["holiday"]
        parts = month_day.split("-")
        month, day = int(parts[0]), int(parts[1])
        label = rule.get("label", "")

        dt = date(year, month, day)
        d_fmt = _fmt(dt)

        if d_fmt not in holidays:
            continue
        if dt.weekday() < 5:
            continue

        observed = dt + timedelta(days=(7 - dt.weekday()))
        o_fmt = _fmt(observed)

        results[o_fmt] = {
            "type": "observed_holiday",
            "name": f"{label} (brīvdiena)",
            "source_date": d_fmt,
            "note": f"Pārceltā brīvdiena no {dt.strftime('%d.%m.%Y')}",
        }
    return results


def _compute_day_type(dt):
    """Return 'weekend' for Sat/Sun, 'workday' for Mon-Fri."""
    return "weekend" if dt.weekday() >= 5 else "workday"


def build_calendar(holidays, region_config, year, memoriam_dates=None):
    entries = {}

    for d_str, entry in holidays.items():
        dt = _parse_date(d_str)
        if dt.year != year:
            continue
        entries[d_str] = {
            "type": "holiday",
            "name": entry.name,
            "local_name": entry.local_name,
            "observed_date": entry.observed_date,
        }

    obs = apply_observance(holidays, region_config, year)
    entries.update(obs)

    short = compute_short_days(holidays, region_config, year)
    entries.update(short)

    swaps = apply_swaps(holidays, region_config, year)
    entries.update(swaps)

    if memoriam_dates:
        for d_str, info in memoriam_dates.items():
            dt = _parse_date(d_str)
            if dt.year != year:
                continue
            if d_str in entries:
                entries[d_str]["is_memoriam"] = True
                existing = entries[d_str].get("name")
                if existing:
                    if info["name"] not in existing:
                        entries[d_str]["name"] = f"{existing}; {info['name']}"
                else:
                    entries[d_str]["name"] = info["name"]
            else:
                entries[d_str] = {
                    "type": _compute_day_type(dt),
                    "is_memoriam": True,
                    "name": info["name"],
                }

    return entries
