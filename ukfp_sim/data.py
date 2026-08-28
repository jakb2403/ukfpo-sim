"""Reference data for the UK Foundation Programme (UKFP) allocation simulation.

The real per-year figures live in `foundation_school_data.csv` (one row per
foundation school, with `{year}_places`/`{year}_final_ratio` columns for
each year of published data - see `DATA_SOURCE_URL`). This module loads
that file and reshapes it into one `(foundation_school, places, ratio)`
DataFrame per year, which is what `UKFPSimulator` expects.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

#: Official source for the published first-preference competition ratios,
#: so users of the app can verify the numbers below against the original.
DATA_SOURCE_URL = (
    "https://foundationprogramme.nhs.uk/wp-content/uploads/sites/2/2026/08/"
    "UKFP-First-preference-ratios-2024-%E2%80%93-2026.pdf"
)
DATA_SOURCE_LABEL = "UKFP First Preference Ratios 2024 - 2026 (foundationprogramme.nhs.uk)"

_DATA_CSV_PATH = Path(__file__).parent / "foundation_school_data.csv"
_YEAR_COLUMN_RE = re.compile(r"^(\d{4})_places$")


def _load_deanery_data_by_year(csv_path: Path = _DATA_CSV_PATH) -> dict[int, pd.DataFrame]:
    """Reshape the wide per-year CSV into one long DataFrame per year.

    Returns `{year: DataFrame(foundation_school, places, ratio)}`, for every
    year that has a `{year}_places`/`{year}_final_ratio` column pair in the
    CSV - so adding a new year later is just a matter of adding two columns
    to the CSV, no code change needed here.
    """
    wide = pd.read_csv(csv_path)
    years = sorted(
        int(match.group(1))
        for column in wide.columns
        if (match := _YEAR_COLUMN_RE.match(column))
    )
    return {
        year: pd.DataFrame(
            {
                "foundation_school": wide["foundation_school"],
                "places": wide[f"{year}_places"].astype(int),
                "ratio": wide[f"{year}_final_ratio"].astype(float),
            }
        )
        for year in years
    }


#: Places/ratio data by application year, freshly parsed from
#: `foundation_school_data.csv`. Powers the app's data-year selector.
DEANERY_DATA_BY_YEAR: dict[int, pd.DataFrame] = _load_deanery_data_by_year()

#: Most recent year with published data - used as the app/module default.
LATEST_YEAR: int = max(DEANERY_DATA_BY_YEAR)

#: Kept for backward compatibility with existing notebook/script usage -
#: equivalent to `DEANERY_DATA_BY_YEAR[2026]`.
DEANERY_DATA_2026 = DEANERY_DATA_BY_YEAR[2026]

#: Example personal ranking (1st choice first), matching the notebook's
#: original `my_ranking`. Every foundation school must appear exactly once.
EXAMPLE_PREFERENCES_2026 = [
    "London",
    "Northern Ireland",
    "KSS",
    "Wessex",
    "Yorkshire and Humber",
    "Wales",
    "Northern",
    "East of England",
    "Peninsula",
    "Scotland",
    "Severn",
    "North West of England",
    "Thames Valley Oxford",
    "West Midlands Central",
    "West Midlands North",
    "West Midlands South",
    "LNR",
    "Trent",
]


def default_deanery_data() -> pd.DataFrame:
    """Return a fresh copy of the most recent (`LATEST_YEAR`) deanery dataset.

    Returns a copy so callers can freely mutate `places`/`ratio` (e.g. for
    "what if" scenarios) without affecting the cached per-year data.
    """
    return deanery_data_for_year(LATEST_YEAR)


def deanery_data_for_year(year: int) -> pd.DataFrame:
    """Return a fresh copy of the reference dataset for `year`.

    Raises KeyError if `year` isn't in `DEANERY_DATA_BY_YEAR` - callers
    should catch this and fall back to whichever year *is* available.
    """
    try:
        data = DEANERY_DATA_BY_YEAR[year]
    except KeyError:
        raise KeyError(f"No foundation school data available for {year}.") from None
    return data.copy()
