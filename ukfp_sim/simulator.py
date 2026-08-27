"""Monte Carlo simulator for UK Foundation Programme (UKFP) allocation.

This models a single applicant's chances of landing each of their ranked
foundation-school preferences, given:

  - how many places each foundation school has, and
  - a competition `ratio` per school (used to infer how popular it is as a
    first choice, relative to its size).

For each simulated run we:

  1. Synthesise a cohort of "everyone else" applying, sized to exactly fill
     every place, whose first choices are drawn to match each school's
     implied demand, and whose remaining preferences are randomised (Gumbel
     noise on top of school popularity, i.e. a Plackett-Luce style ranking).
  2. Give "you" a uniformly random rank position amongst the whole cohort
     (this stands in for the many real factors - academic score, SJT score,
     etc. - that determine allocation order, without needing to model them
     individually).
  3. Run a standard two-pass serial allocation: everyone tries their 1st
     choice in rank order, then remaining students try their next available
     choice, etc.
  4. Record the random rank you were given and which of your ranked
     preferences you ended up with.

Running many such simulations builds up a distribution of "if you end up
with rank X, what's the chance you get your Nth choice?".
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .results import SimulationResult

_REQUIRED_COLUMNS = {"foundation_school", "places", "ratio"}


class UKFPSimulator:
    """Simulates the UKFP allocation lottery for one applicant's preference list.

    Example:
        >>> from ukfp_sim import UKFPSimulator, default_deanery_data, EXAMPLE_PREFERENCES_2026
        >>> sim = UKFPSimulator(default_deanery_data(), EXAMPLE_PREFERENCES_2026, n_runs=2000, seed=42)
        >>> result = sim.run()
        >>> result.summary().head()
        >>> sim.plot_bar()
        >>> sim.plot_scatter()
        >>> sim.rerun()  # fresh random draw, same parameters
    """

    def __init__(
        self,
        deanery_data: pd.DataFrame,
        user_preferences: Sequence[str],
        n_runs: int = 1000,
        seed: int | None = None,
    ) -> None:
        """Create a simulator instance.

        Args:
            deanery_data: DataFrame with columns `foundation_school`, `places`
                (int, places available) and `ratio` (float, competition/demand
                weighting). One row per foundation school.
            user_preferences: your ranked list of foundation school names,
                1st choice first. Must contain every school in `deanery_data`
                exactly once.
            n_runs: default number of Monte Carlo runs used by `.run()`.
            seed: optional seed for reproducible results. Leave as None to
                get fresh randomness on every `.run()`/`.rerun()` call.
        """
        missing = _REQUIRED_COLUMNS - set(deanery_data.columns)
        if missing:
            raise ValueError(
                f"deanery_data is missing required column(s): {sorted(missing)}"
            )

        self.n_runs = n_runs
        self.deanery_data = deanery_data.reset_index(drop=True).copy()
        self.user_preferences = list(user_preferences)
        self.seed = seed

        n_schools = len(self.deanery_data)
        if len(self.user_preferences) != n_schools:
            raise ValueError(
                "user_preferences must rank every foundation school exactly "
                f"once ({n_schools} schools, got {len(self.user_preferences)} "
                "preferences)."
            )
        if set(self.user_preferences) != set(self.deanery_data["foundation_school"]):
            raise ValueError(
                "user_preferences must exactly match the foundation_school "
                "names in deanery_data (check spelling/casing)."
            )

        self.deanery_data["id"] = np.arange(n_schools)
        self.name_to_id = dict(
            zip(self.deanery_data["foundation_school"], self.deanery_data["id"])
        )

        self.places = self.deanery_data["places"].to_numpy()
        self.weights = self.deanery_data["ratio"].to_numpy()
        self.total_places = int(self.places.sum())

        # Scale raw demand so it matches total available places 1:1.
        raw_demand = self.places * self.weights
        scaling_factor = self.total_places / raw_demand.sum()
        self.first_choice_counts = np.round(raw_demand * scaling_factor).astype(int)
        remainder = self.total_places - self.first_choice_counts.sum()
        self.first_choice_counts[np.argmax(self.places)] += remainder

        self.user_prefs_ids = np.array(
            [self.name_to_id[name] for name in self.user_preferences]
        )

        self._result: SimulationResult | None = None
        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def has_run(self) -> bool:
        """Whether `.run()` has produced a cached result yet."""
        return self._result is not None

    @property
    def result(self) -> SimulationResult:
        """The most recent `SimulationResult`. Raises if `.run()` hasn't been called."""
        if self._result is None:
            raise RuntimeError(
                "No simulation results yet - call `.run()` (or `.rerun()`) first."
            )
        return self._result

    def run(
        self,
        n_runs: int | None = None,
        force: bool = False,
        seed: int | None = None,
    ) -> SimulationResult:
        """Run the Monte Carlo simulation, caching the result.

        Calling `.run()` again with the same `n_runs` is a cheap no-op unless
        `force=True` - use `.rerun()` as a shorthand for "run again with
        fresh randomness".

        Args:
            n_runs: override the number of runs for this call. Does not
                permanently change `self.n_runs`.
            force: re-simulate even if a cached result already matches
                `n_runs`.
            seed: reseed the RNG before this run, for a reproducible result.
                If omitted, randomness continues from wherever the
                simulator's RNG stream currently is.

        Returns:
            The `SimulationResult` (also available afterwards as `.result`).
        """
        runs = n_runs if n_runs is not None else self.n_runs
        if self.has_run and not force and runs == self._result.n_runs:
            return self._result

        if seed is not None:
            self._rng = np.random.default_rng(seed)

        records = np.empty((runs, 2), dtype=np.int64)
        for i in range(runs):
            rank, choice_num = self._run_single_simulation()
            records[i, 0] = rank
            records[i, 1] = choice_num

        raw = pd.DataFrame(records, columns=["user_rank", "choice_num"])
        raw["rank_percentile"] = raw["user_rank"] / self.total_places * 100

        self._result = SimulationResult(
            raw=raw,
            n_runs=runs,
            total_places=self.total_places,
            preferences=list(self.user_preferences),
        )
        return self._result

    def rerun(
        self, n_runs: int | None = None, seed: int | None = None
    ) -> SimulationResult:
        """Re-run the simulation from scratch (discarding any cached result).

        Shorthand for `run(force=True)`. Same parameters (deanery data,
        preferences, n_runs) as before unless overridden here - useful for
        "run it again and see if the picture looks the same" without having
        to rebuild the simulator.
        """
        return self.run(n_runs=n_runs, force=True, seed=seed)

    def summary(self) -> pd.DataFrame:
        """Per-choice allocation probability table. See `SimulationResult.summary`."""
        return self.result.summary()

    def plot_bar(self, **kwargs):
        """Stacked bar chart of choice allocated vs. random rank bracket.

        Runs the simulation first if it hasn't been already. See
        `ukfp_sim.plotting.plot_choice_by_rank_bracket` for options.
        """
        from .plotting import plot_choice_by_rank_bracket

        if not self.has_run:
            self.run()
        return plot_choice_by_rank_bracket(self.result, **kwargs)

    def plot_scatter(self, **kwargs):
        """Scatter plot of random rank position vs. choice received.

        Runs the simulation first if it hasn't been already. See
        `ukfp_sim.plotting.plot_rank_vs_choice_scatter` for options.
        """
        from .plotting import plot_rank_vs_choice_scatter

        if not self.has_run:
            self.run()
        return plot_rank_vs_choice_scatter(self.result, **kwargs)

    def plot_bar_plotly(self, **kwargs):
        """Interactive (Plotly) version of `plot_bar`, with hover tooltips.

        Runs the simulation first if it hasn't been already. See
        `ukfp_sim.plotting_plotly.plot_choice_by_rank_bracket_plotly` for options.
        """
        from .plotting_plotly import plot_choice_by_rank_bracket_plotly

        if not self.has_run:
            self.run()
        return plot_choice_by_rank_bracket_plotly(self.result, **kwargs)

    def plot_scatter_plotly(self, **kwargs):
        """Interactive (Plotly) version of `plot_scatter`, with hover tooltips.

        Runs the simulation first if it hasn't been already. See
        `ukfp_sim.plotting_plotly.plot_rank_vs_choice_scatter_plotly` for options.
        """
        from .plotting_plotly import plot_rank_vs_choice_scatter_plotly

        if not self.has_run:
            self.run()
        return plot_rank_vs_choice_scatter_plotly(self.result, **kwargs)

    def plot_cumulative(self, **kwargs):
        """Line chart of cumulative "chance of a top-N choice".

        Runs the simulation first if it hasn't been already. See
        `ukfp_sim.plotting.plot_cumulative_probability` for options.
        """
        from .plotting import plot_cumulative_probability

        if not self.has_run:
            self.run()
        return plot_cumulative_probability(self.result, **kwargs)

    def plot_cumulative_plotly(self, **kwargs):
        """Interactive (Plotly) version of `plot_cumulative`, with hover tooltips.

        Runs the simulation first if it hasn't been already. See
        `ukfp_sim.plotting_plotly.plot_cumulative_probability_plotly` for options.
        """
        from .plotting_plotly import plot_cumulative_probability_plotly

        if not self.has_run:
            self.run()
        return plot_cumulative_probability_plotly(self.result, **kwargs)

    # ------------------------------------------------------------------
    # Simulation mechanics
    # ------------------------------------------------------------------

    def _generate_synthetic_cohort(self) -> np.ndarray:
        """Build the "everyone else" applicant pool for one simulation run.

        Returns an (n_synthetic, n_schools) array where row i is applicant
        i's full ranked preference list (school ids), first choice first.
        First choices are drawn to match each school's implied demand;
        the rest of each ranking is a Plackett-Luce draw (school popularity
        plus Gumbel noise) over the remaining schools.
        """
        user_first_choice = self.user_prefs_ids[0]
        adjusted_counts = self.first_choice_counts.copy()
        if adjusted_counts[user_first_choice] > 0:
            adjusted_counts[user_first_choice] -= 1

        first_choices = np.repeat(np.arange(len(self.places)), adjusted_counts)
        n_synthetic = len(first_choices)

        log_weights = np.log(self.weights + 1e-9)
        gumbel_noise = self._rng.gumbel(size=(n_synthetic, len(self.places)))
        scores = log_weights + gumbel_noise

        row_indices = np.arange(n_synthetic)
        scores[row_indices, first_choices] = -np.inf

        remaining_choices = np.argsort(-scores, axis=1)[:, :-1]
        return np.column_stack((first_choices, remaining_choices))

    def _run_single_simulation(self) -> tuple[int, int]:
        """Run one full allocation round and return (user_rank, choice_num)."""
        synthetic_prefs = self._generate_synthetic_cohort()
        all_prefs = np.vstack([synthetic_prefs, self.user_prefs_ids])
        n_total_students = len(all_prefs)
        user_index = n_total_students - 1

        random_ranks = self._rng.random(n_total_students)
        process_order = np.argsort(random_ranks)

        user_random_rank = np.where(process_order == user_index)[0][0] + 1

        # The allocation passes below are an inherently sequential
        # serial-dictatorship process (each student's outcome depends on
        # every higher-priority student's outcome), so it can't be
        # vectorised away with numpy. What *can* be avoided is numpy's
        # per-element scalar-indexing overhead in a tight Python loop -
        # working with plain Python ints/lists here instead of numpy
        # scalars is ~10-20x faster for this access pattern and produces
        # bit-identical results (same random draws, same logic).
        n_schools = len(self.places)
        places_left = self.places.tolist()
        allocated = [-1] * n_total_students
        prefs_list = all_prefs.tolist()
        order_list = process_order.tolist()

        # Pass 1: everyone tries their 1st choice, in rank order.
        for i in order_list:
            pref_1 = prefs_list[i][0]
            if places_left[pref_1] > 0:
                allocated[i] = pref_1
                places_left[pref_1] -= 1

        # Pass 2: anyone still unplaced tries their remaining choices in order.
        for i in order_list:
            if allocated[i] == -1:
                row = prefs_list[i]
                for j in range(1, n_schools):
                    pref_j = row[j]
                    if places_left[pref_j] > 0:
                        allocated[i] = pref_j
                        places_left[pref_j] -= 1
                        break

        user_final_allocation_id = allocated[user_index]
        if user_final_allocation_id == -1:
            # Shouldn't happen: every applicant ranks all schools and total
            # demand == total supply, but guard against it rather than
            # silently mis-recording a result.
            raise RuntimeError(
                "Simulation produced an unallocated applicant - check that "
                "deanery_data places/ratio values are sane."
            )
        choice_idx = (
            np.where(self.user_prefs_ids == user_final_allocation_id)[0][0] + 1
        )

        return int(user_random_rank), int(choice_idx)
