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


def compare_results(result_a: SimulationResult, result_b: SimulationResult) -> pd.DataFrame:
    """Per-school comparison of two `SimulationResult`s (e.g. two ranking scenarios).

    Matches rows by `foundation_school` name, NOT `choice_num` - the same
    school can sit at a different position in each ranking (e.g. 1st in A,
    2nd in B), so comparing "your Nth choice in A" against "your Nth choice
    in B" would silently compare two different schools. Matching by name
    instead answers "how did *this school's* odds change between the two
    rankings?".

    Returns one row per school that appears in either result's `.preferences`
    (normally identical sets - a mismatch only happens if the underlying
    school data was edited between saving the two scenarios, in which case
    the missing side gets `NaN`/0 rather than raising), sorted by
    `probability_pct_delta` magnitude descending so the biggest movers - the
    schools most affected by however you reordered your list - surface
    first.

    Columns: foundation_school, choice_num_a, probability_pct_a,
    choice_num_b, probability_pct_b, probability_pct_delta (b - a),
    choice_num_delta (b - a; negative = ranked higher, i.e. better, in B).
    """
    summary_a = result_a.summary().set_index("foundation_school")
    summary_b = result_b.summary().set_index("foundation_school")

    merged = summary_a[["choice_num", "probability_pct"]].join(
        summary_b[["choice_num", "probability_pct"]],
        how="outer",
        lsuffix="_a",
        rsuffix="_b",
    )
    merged["probability_pct_delta"] = (
        merged["probability_pct_b"] - merged["probability_pct_a"]
    )
    merged["choice_num_delta"] = merged["choice_num_b"] - merged["choice_num_a"]

    merged = merged.sort_values(
        "probability_pct_delta", key=lambda s: s.abs(), ascending=False
    )
    return merged.reset_index()[
        [
            "foundation_school",
            "choice_num_a",
            "probability_pct_a",
            "choice_num_b",
            "probability_pct_b",
            "probability_pct_delta",
            "choice_num_delta",
        ]
    ]
