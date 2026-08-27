"""Reference data for the UK Foundation Programme (UKFP) allocation simulation.

This module holds example inputs only. A future UI is expected to let users
supply their own `deanery_data` / `user_preferences` interactively - the
values here just give the simulator something sensible to run with out of
the box, and match the numbers originally hard-coded in the notebook.
"""

from __future__ import annotations

import pandas as pd

#: 2026 foundation school places and competition ratios.
#: `ratio` is the applicants-per-place style demand weighting used to derive
#: each school's share of first-choice demand (see UKFPSimulator for how it
#: is used).
DEANERY_DATA_2026 = pd.DataFrame(
    [
        {"foundation_school": "East of England", "places": 921, "ratio": 0.69},
        {"foundation_school": "KSS", "places": 703, "ratio": 0.84},
        {"foundation_school": "LNR", "places": 330, "ratio": 0.74},
        {"foundation_school": "London", "places": 1216, "ratio": 2.31},
        {"foundation_school": "North West of England", "places": 1081, "ratio": 1.16},
        {"foundation_school": "Northern", "places": 568, "ratio": 0.74},
        {"foundation_school": "Northern Ireland", "places": 387, "ratio": 0.78},
        {"foundation_school": "Peninsula", "places": 319, "ratio": 0.87},
        {"foundation_school": "Scotland", "places": 1237, "ratio": 1.09},
        {"foundation_school": "Severn", "places": 421, "ratio": 1.33},
        {"foundation_school": "Thames Valley Oxford", "places": 342, "ratio": 1.30},
        {"foundation_school": "Trent", "places": 474, "ratio": 0.51},
        {"foundation_school": "Wales", "places": 460, "ratio": 0.65},
        {"foundation_school": "Wessex", "places": 437, "ratio": 0.58},
        {"foundation_school": "West Midlands Central", "places": 286, "ratio": 1.51},
        {"foundation_school": "West Midlands North", "places": 436, "ratio": 0.39},
        {"foundation_school": "West Midlands South", "places": 294, "ratio": 0.50},
        {"foundation_school": "Yorkshire and Humber", "places": 898, "ratio": 0.76},
    ]
)

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
    """Return a fresh copy of the 2026 reference deanery dataset.

    Returns a copy so callers can freely mutate `places`/`ratio` (e.g. for
    "what if" scenarios) without affecting the module-level constant.
    """
    return DEANERY_DATA_2026.copy()
