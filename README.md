# calendar2json

Convert public holiday data to JSON for work-time management tools.

Supports any country that the Python `holidays` library covers (250+), with a rules engine for country-specific edge cases: pre-holiday short days, observance shifts, and government-ordered day swaps. Ships with a Latvia configuration.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Single year, stdout
./calendar2json.py --region LV --year 2026

# Year range to file
./calendar2json.py --region LV --year 2026-2028 -o calendar.json

# Pretty-print
./calendar2json.py --year 2026 --pretty

# Offline mode (holidays lib only, no network)
./calendar2json.py --offline --year 2026

# Multiple years
./calendar2json.py --year 2026,2028,2030
```

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--region` / `-r` | `LV` | ISO 3166-1 alpha-2 region code |
| `--year` / `-y` | `2026` | Year, range (`2026-2028`), or list (`2026,2028`) |
| `--source` | `auto` | Data source: `auto`, `holidays`, `tallyfy` |
| `--offline` | off | Skip network — use `holidays` lib only |
| `--output` / `-o` | stdout | Write JSON to file |
| `--pretty` | true | Pretty-print JSON |
| `--single-year` | off | Output separate key per year |

## Output format

Only edge-case days are included (holidays, swaps, short days). Normal workdays and weekends are implicit.

```json
{
  "2026-05-04": {
    "type": "holiday",
    "name": "Latvijas Republikas Neatkarības atjaunošanas diena"
  },
  "2026-11-17": {
    "type": "pre_holiday_short",
    "note": "Pirmssvētku diena"
  },
  "2026-01-17": {
    "type": "swapped_workday",
    "swap_source": "2026-01-02",
    "note": "Pārceltā darba diena no 02.01.2026"
  }
}
```

Entry types: `holiday`, `observed_holiday`, `pre_holiday_short`, `swapped_day_off`, `swapped_workday`.

## Adding a region

Create `regions/{code}.yaml`:

```yaml
pre_holiday_short_hours: 7

observance_shifts:
  - holiday: "05-04"
    label: "Latvijas Republikas Neatkarības atjaunošanas diena"
  - holiday: "11-18"
    label: "Latvijas Republikas Proklamēšanas diena"

swaps:
  "2025":
    "05-02": "05-10"
    "11-17": "11-08"
```

- `pre_holiday_short_hours`: Work hours for the day before a holiday (omit to disable).
- `observance_shifts`: Holidays that get moved to Monday when they fall on a weekend.
- `swaps`: Government-ordered swaps for a given year (`"src": "dst"` within that year).

## How it works

1. **Fetcher** pulls holiday data from the Python `holidays` lib (primary, offline) or Tallyfy API (fallback).
2. **Rules engine** (`rules.py`) computes pre-holiday short days, detects observance shifts from weekend holidays, and extracts government-ordered swaps from holiday names.
3. **Calendar builder** merges everything into a sorted JSON dictionary by date.

## Sources

- [Python holidays](https://github.com/vacanza/holidays)
- [Tallyfy holiday API](https://tallyfy.com/national-holidays/api/)
- Latvijas Vēstnesis — MK rīkojumi par darba dienu pārcelšanu
