"""Plotting helpers for `SimulationResult` objects.

Both chart functions:
  - take a `SimulationResult` (from `UKFPSimulator.run()` / `.result`),
  - return the `matplotlib.figure.Figure` they drew (so callers can
    `fig.savefig(...)`, embed it in a GUI canvas, or just let `show=True`
    pop it up as before),
  - accept an optional `ax` to draw into an existing axes (e.g. for laying
    multiple charts out in one figure, or for a future dashboard/UI), and
  - use the same choice-number -> colour mapping, so a given choice (e.g.
    "Choice 3: KSS") is always drawn in the same colour in both the bar
    chart and the scatter plot.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from .analysis import legend_label, rank_bracket_pivot
from .colors import DEFAULT_CMAP, choice_color_map
from .results import SimulationResult


def plot_rank_vs_choice_scatter(
    result: SimulationResult,
    alpha: float = 0.5,
    jitter: float = 0.15,
    cmap: str = DEFAULT_CMAP,
    ax=None,
    show: bool = True,
):
    """Scatter plot of random rank position vs. choice received.

    Each point is one simulated run. Points are grouped into horizontal
    bands by which choice number was allocated (vertical jitter within a
    band just separates overlapping points - it carries no meaning).

    Args:
        result: a `SimulationResult` from `UKFPSimulator.run()`.
        alpha: point transparency (lower = better for dense overlapping runs).
        jitter: vertical jitter magnitude, in choice-number units.
        cmap: matplotlib colormap name used for the choice-number colour scale.
        ax: existing axes to draw into. A new figure is created if omitted.
        show: call `plt.show()` before returning (set False when embedding,
            e.g. in a GUI, or when saving to file without a display).

    Returns:
        The `matplotlib.figure.Figure` containing the chart.
    """
    df = result.raw
    counts = df["choice_num"].value_counts()
    unique_choices = sorted(df["choice_num"].unique())
    colors = choice_color_map(result.preferences, cmap)

    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 8))
    else:
        fig = ax.figure

    rng = np.random.default_rng()  # display-only jitter; doesn't affect results
    for choice_num in unique_choices:
        df_sub = df[df["choice_num"] == choice_num]
        y_jittered = choice_num + rng.uniform(-jitter, jitter, size=len(df_sub))
        ax.scatter(
            df_sub["user_rank"],
            y_jittered,
            alpha=alpha,
            s=30,
            edgecolors="none",
            color=colors[choice_num],
            label=legend_label(result, choice_num, counts),
        )

    mean_rank = df["user_rank"].mean()
    ax.axvline(
        mean_rank,
        color="black",
        linestyle=":",
        linewidth=1.5,
        alpha=0.7,
        label=f"Mean rank: {mean_rank:,.0f} / {result.total_places:,}",
    )

    ax.get_yaxis().set_visible(False)
    ax.set_title(
        f"UKFP Simulation: Random Rank Position vs Choice Received ({result.n_runs:,} runs)",
        fontsize=14,
        pad=15,
    )
    ax.set_xlabel(
        f"Random Rank Position (1 = best rank, {result.total_places:,} = worst rank)",
        fontsize=11,
    )
    ax.set_xlim(0, result.total_places)
    ax.legend(
        title="Choice Allocated (Overall %)",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
    )
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()

    if show:
        plt.show()
    return fig


def plot_choice_by_rank_bracket(
    result: SimulationResult,
    n_bins: int = 10,
    cmap: str = DEFAULT_CMAP,
    ax=None,
    show: bool = True,
    annotate_counts: bool = True,
):
    """Stacked bar chart of choice allocated, grouped by random rank bracket.

    Rank positions are bucketed into `n_bins` equal-width percentile
    brackets (0-10%, 10-20%, ...) and each bar shows what share of runs in
    that bracket landed each choice number.

    Args:
        result: a `SimulationResult` from `UKFPSimulator.run()`.
        n_bins: number of equal-width rank-percentile brackets.
        cmap: matplotlib colormap name used for the choice-number colour scale.
        ax: existing axes to draw into. A new figure is created if omitted.
        show: call `plt.show()` before returning (set False when embedding
            or saving to file without a display).
        annotate_counts: print the number of simulated runs ("n=...") above
            each bar, so a thin bracket (e.g. very few runs landed in the
            0-10% band) doesn't get mistaken for a confident 100% result.

    Returns:
        The `matplotlib.figure.Figure` containing the chart.
    """
    pivot_pct = rank_bracket_pivot(result, n_bins=n_bins)
    bracket_totals = pivot_pct.attrs["bracket_totals"]
    df = result.raw

    colors = choice_color_map(result.preferences, cmap)
    bar_colors = [colors[c] for c in pivot_pct.columns]

    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 8))
    else:
        fig = ax.figure

    pivot_pct.plot(kind="bar", stacked=True, ax=ax, color=bar_colors, width=0.85)

    overall_counts = df["choice_num"].value_counts()
    legend_labels = [
        legend_label(result, choice_num, overall_counts) for choice_num in pivot_pct.columns
    ]
    ax.legend(
        legend_labels,
        title="Choice Allocated (Overall %)",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
    )

    if annotate_counts:
        for x, total in enumerate(bracket_totals):
            ax.text(
                x, 101, f"n={int(total)}", ha="center", va="bottom",
                fontsize=8, color="dimgray",
            )
        ax.set_ylim(0, 108)
    else:
        ax.set_ylim(0, 100)

    ax.set_title(
        f"UKFP Allocation Choice by Random Rank Position ({result.n_runs:,} runs)",
        fontsize=14,
        pad=15,
    )
    ax.set_xlabel(
        "Random Rank Percentile Bracket (0–10% = best ranks)", fontsize=11
    )
    ax.set_ylabel("Percentage of Runs (%)", fontsize=11)
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()

    if show:
        plt.show()
    return fig
