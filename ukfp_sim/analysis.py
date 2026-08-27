"""Shared, chart-library-agnostic computations over a `SimulationResult`."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .results import SimulationResult


def rank_bracket_pivot(result: SimulationResult, n_bins: int = 10) -> pd.DataFrame:
    """Percentage of runs landing each choice, per random-rank-percentile bracket.

    Rank positions are bucketed into `n_bins` equal-width percentile brackets
    (0-10%, 10-20%, ...). Returns a DataFrame indexed by bracket label, one
    column per choice number (sorted ascending), values are the percentage
    of runs *within that bracket* that landed that choice (each row sums to
    100, or to 0 for a bracket with no runs in it).
    """
    df = result.raw.copy()

    bin_edges = np.linspace(0, 100, n_bins + 1)
    bin_labels = [
        f"{int(bin_edges[i])}–{int(bin_edges[i + 1])}%" for i in range(n_bins)
    ]
    df["rank_bracket"] = pd.cut(
        df["rank_percentile"],
        bins=bin_edges,
        labels=bin_labels,
        include_lowest=True,
    )

    # Pivot by choice_num (not the school name) to guarantee strict
    # numerical ordering (1, 2, 3, ...) regardless of label text.
    pivot_counts = (
        df.groupby(["rank_bracket", "choice_num"], observed=False)
        .size()
        .unstack(fill_value=0)
    )
    pivot_counts = pivot_counts.reindex(columns=sorted(pivot_counts.columns))
    bracket_totals = pivot_counts.sum(axis=1)

    # Percentage per bracket; brackets with zero runs (possible with a
    # small n_runs) become 0 rather than NaN.
    pivot_pct = pivot_counts.div(bracket_totals.replace(0, np.nan), axis=0) * 100
    pivot_pct = pivot_pct.fillna(0)
    pivot_pct.attrs["bracket_totals"] = bracket_totals
    return pivot_pct


def legend_label(result: SimulationResult, choice_num: int, counts: pd.Series) -> str:
    """"Choice N: School Name (overall %)" label used by both chart types' legends."""
    school_name = result.preferences[choice_num - 1]
    overall_pct = counts.get(choice_num, 0) / result.n_runs * 100
    return f"Choice {choice_num}: {school_name} ({overall_pct:.1f}%)"
