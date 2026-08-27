"""UKFP allocation Monte Carlo simulator.

Typical usage:

    from ukfp_sim import UKFPSimulator, default_deanery_data, EXAMPLE_PREFERENCES_2026

    sim = UKFPSimulator(
        deanery_data=default_deanery_data(),
        user_preferences=EXAMPLE_PREFERENCES_2026,
        n_runs=1000,
    )
    result = sim.run()          # run the simulation
    sim.summary()               # per-choice probability table
    sim.plot_bar()              # stacked bar chart
    sim.plot_scatter()          # scatter plot
    sim.rerun()                 # run it again with fresh randomness

See `ukfp_sim.simulator.UKFPSimulator` for full documentation.
"""

from .data import DEANERY_DATA_2026, EXAMPLE_PREFERENCES_2026, default_deanery_data
from .plotting import (
    plot_choice_by_rank_bracket,
    plot_cumulative_probability,
    plot_rank_vs_choice_scatter,
)
from .plotting_plotly import (
    plot_choice_by_rank_bracket_plotly,
    plot_cumulative_probability_plotly,
    plot_rank_vs_choice_scatter_plotly,
)
from .results import SimulationResult
from .simulator import UKFPSimulator

__all__ = [
    "UKFPSimulator",
    "SimulationResult",
    "DEANERY_DATA_2026",
    "EXAMPLE_PREFERENCES_2026",
    "default_deanery_data",
    "plot_choice_by_rank_bracket",
    "plot_rank_vs_choice_scatter",
    "plot_cumulative_probability",
    "plot_choice_by_rank_bracket_plotly",
    "plot_rank_vs_choice_scatter_plotly",
    "plot_cumulative_probability_plotly",
]
