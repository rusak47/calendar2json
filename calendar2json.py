#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
import yaml

from fetcher import fetch_holidays
from rules import build_calendar

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGIONS_DIR = os.path.join(SCRIPT_DIR, "regions")


def load_region_config(region_code):
    path = os.path.join(REGIONS_DIR, f"{region_code.lower()}.yaml")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f)


def parse_years(year_arg):
    if "-" in year_arg:
        parts = year_arg.split("-")
        return list(range(int(parts[0]), int(parts[1]) + 1))
    if "," in year_arg:
        return [int(y.strip()) for y in year_arg.split(",")]
    return [int(year_arg)]


def main():
    parser = argparse.ArgumentParser(
        description="Generate holiday calendar JSON for work time management"
    )
    parser.add_argument(
        "--region", "-r", default="LV",
        help="ISO 3166-1 alpha-2 region code (default: LV)",
    )
    parser.add_argument(
        "--year", "-y", default="2026",
        help="Year or range (e.g. 2026 or 2026-2028 or 2026,2027)",
    )
    parser.add_argument(
        "--source", choices=["auto", "holidays", "tallyfy"], default="auto",
        help="Data source (default: auto - try holidays lib, fallback Tallyfy)",
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Force offline mode (use holidays lib only, no network requests)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--pretty", action="store_true", default=True,
        help="Pretty-print JSON output (default: true)",
    )
    parser.add_argument(
        "--single-year", action="store_true",
        help="Output separate JSON per year",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    years = parse_years(args.year)
    config = load_region_config(args.region)

    source = args.source
    if args.offline and source == "auto":
        source = "holidays"
    elif args.offline and source == "tallyfy":
        logger.warning("--offline is set but --source=tallyfy requires network; using holidays lib")
        source = "holidays"

    if args.single_year:
        result = {}
        for year in years:
            holidays = fetch_holidays(args.region, [year], source=source)
            result[str(year)] = build_calendar(holidays, config, year)
    else:
        holidays = fetch_holidays(args.region, years, source=source)
        result = {}
        for year in years:
            cal = build_calendar(holidays, config, year)
            result.update(cal)

    result = dict(sorted(result.items()))

    indent = 2 if args.pretty else None
    output = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            f.write("\n")
        logger.info("Written to %s", args.output)
    else:
        sys.stdout.write(output)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
