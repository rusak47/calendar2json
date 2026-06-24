# calendar2json

## Commands
- Run: `./calendar2json.py --region LV --year 2026`
- Test: `.venv/bin/python3 -m pytest tests/ -v`
- Integration check: `./calendar2json.py --region LV --year 2025-2030 --offline --pretty`
- Verify against tavirekini.lv manually (static HTML, no API)

## Code structure
- `calendar2json.py` — CLI entry point, arg parsing, orchestrates fetch + rules
- `fetcher.py` — Holiday sources: `holidays` lib (primary, offline) + Tallyfy (fallback, 2026–2030 only)
  - Also `load_memoriam_dates()` — loads `{code}-memoriam.yaml` (or fetches from URL via likumi.lv HTML parser). Floating dates computed via nth-weekday helper.
- `rules.py` — Rules engine: short days, observance shifts, swap inversion/merge, memoriam flagging
- `regions/lv.yaml` — Latvia config (short hours, observance rules, memoriam source URL, annual swap overrides)
- `regions/lv-memoriam.yaml` — Latvia commemorative dates from likumi.lv Article 2
- `tests/` — Pytest suite (70 tests)

## Data flow
`holidays` lib → dict of `{date: HolidayEntry}` → `build_calendar()`: apply_observance() → compute_short_days() → apply_swaps() → sorted JSON.

Memoriam dates from `{code}-memoriam.yaml` merge into calendar at the end of `build_calendar()` via `memoriam_dates` param—independent pipeline from holidays lib.

## Latvia holiday rules
- **Observance shifts**: Only May 4 and Nov 18 get weekend→Monday. Labour Day, Christmas, Easter on weekends do NOT shift.
- **Sandwiched day pattern**: Thu holiday → Fri swap candidate; Tue holiday → Mon swap candidate. Destination Saturday set by MK rīkojums (~June for next year).
- **Short hours propagate** (removed): If a pre-holiday short day is swapped, the swapped-to Saturday would get the same hours per Darba likums 133.pants. Removed when work_hours was cut; re-add if hours are needed later.
- **Pre-holiday short days**: Any workday immediately before a public holiday = 7h. Deterministic from holiday list alone.
- **Swapped days**: holidays lib marks them as "Brīvdiena (pārcelta no DD.MM.YYYY)". Parse via regex for automatic swap inversion.

## API gotchas
- **Tallyfy**: 404 for years < 2026. `observed_date` field parsed correctly (tested via mock).
- **tavirekini.lv**: Best Latvia reference, static HTML per year, no API. Swap data must be extracted manually.
- **Nager.Date**: REST API v3 does NOT expose ObservedDate in JSON. v4 (beta) may add it.
- **KF6Holidays**: `.holiday` files compiled into `libKF6Holidays.so` as Qt resources. Extract via `strings` or link library.

## Edge cases caught
- **Cross-year short days**: A holiday on Jan 1 would make Dec 31 a short day — must filter `prev.year != year`.
- **Holidays as short days**: Jun 23 (Līgo) and Dec 24-25 (Christmas) wrongly flagged as "pre-holiday short" because they sit before another holiday. Fix: check that the previous day is not in `all_holiday_dates` (including swap entries).
- **Swapped day short hours**: Compute raw short days first (swap-independent), then check if the swapped-off day was in that raw set to determine swapped-to hours. Removed when work_hours was cut; re-add if hours are needed later.

## Memoriam
- **`is_memoriam` field convention**: Only present when `true`. Absence means `false` — never emit `is_memoriam: false`.
- **Name injection rules**: Memoriam-only date → set `name` from memoriam. Swap entry (no `name`) → set from memoriam. Holiday already has `name` → append `"; {mem_name}"` only if memoriam name not already in existing string (dedup needed because holidays lib already combines May 1 names).
- **May 1 dual-type**: Only Latvia date that is both holiday (Art. 1) and memoriam (Art. 2). Holidays lib already concatenates both names — dedup prevents double-appending.
- **Memoriam-only types**: Memoriam dates that aren't holidays get `type: workday` or `type: weekend` (no special memoriam type).
- **Swap entries lack `name`**: `swapped_day_off`/`swapped_workday` entries have `type`, `swap_source`, `note` but no `name`. Memoriam overlapping a swap date injects the memoriam `name`.

## Sources
- Latvia holiday law: `likumi.lv/doc.php?id=72608`
- Darba likums 133.panta ceturtā daļa — discretionary swap authority
- Python `holidays` lib: https://github.com/vacanza/holidays
