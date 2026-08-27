"""Data structures for holding UKFP simulation outputs."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class SimulationResult:
    """The outcome of running a batch of UKFP allocation simulations.

    Attributes:
        raw: one row per simulated run, with columns:
            - user_rank: the random rank position drawn for "you" in that run
              (1 = best possible rank, `total_places` = worst).
            - choice_num: which of your ranked preferences you were allocated
              (1 = your 1st choice, 2 = your 2nd choice, ...).
            - rank_percentile: `user_rank` expressed as a percentile of
              `total_places` (0 = best, 100 = worst).
        n_runs: number of simulation runs that produced `raw`.
        total_places: total foundation-programme places across all schools.
        preferences: the ranked list of foundation schools used for this run,
            1st choice first.
    """

    raw: pd.DataFrame
    n_runs: int
    total_places: int
    preferences: list[str] = field(default_factory=list)

    def summary(self) -> pd.DataFrame:
        """Per-choice allocation probability, in preference order (1st..Nth).

        Columns: choice_num, foundation_school, count, probability_pct,
        cumulative_pct (probability of getting this choice *or better*).
        """
        counts = self.raw["choice_num"].value_counts()
        rows = []
        cumulative = 0.0
        for idx, school in enumerate(self.preferences, start=1):
            count = int(counts.get(idx, 0))
            pct = 100 * count / self.n_runs
            cumulative += pct
            rows.append(
                {
                    "choice_num": idx,
                    "foundation_school": school,
                    "count": count,
                    "probability_pct": pct,
                    "cumulative_pct": cumulative,
                }
            )
        return pd.DataFrame(rows)

    @property
    def mean_choice(self) -> float:
        """Average preference number obtained across all runs (lower = better)."""
        return float(self.raw["choice_num"].mean())

    @property
    def median_choice(self) -> float:
        """Median preference number obtained across all runs."""
        return float(self.raw["choice_num"].median())

    @property
    def mean_rank(self) -> float:
        """Average random rank position drawn across all runs."""
        return float(self.raw["user_rank"].mean())

    def choice_probability(self, choice_num: int) -> float:
        """Probability (%) of being allocated exactly this choice number."""
        return 100 * (self.raw["choice_num"] == choice_num).mean()

    def top_n_probability(self, n: int) -> float:
        """Probability (%) of being allocated one of your top `n` choices."""
        return 100 * (self.raw["choice_num"] <= n).mean()
