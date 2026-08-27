"""Plotly versions of the two charts, for the interactive (Streamlit) app.

These mirror `plotting.py` chart-for-chart (same data, same colour mapping,
same titles) but render as Plotly figures so hovering a point/bar shows a
tooltip, and the chart pans/zooms - which a static matplotlib PNG can't do.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from .analysis import legend_label, rank_bracket_pivot
from .colors import DEFAULT_CMAP, choice_color_map_hex
from .results import SimulationResult


def plot_rank_vs_choice_scatter_plotly(
    result: SimulationResult,
    jitter: float = 0.15,
    cmap: str = DEFAULT_CMAP,
) -> go.Figure:
    """Interactive scatter plot of random rank position vs. choice received.

    Hovering a point shows the exact rank and choice for that simulated run.
    """
    df = result.raw
    counts = df["choice_num"].value_counts()
    unique_choices = sorted(df["choice_num"].unique())
    colors = choice_color_map_hex(result.preferences, cmap)
    rng = np.random.default_rng()  # display-only jitter; doesn't affect results

    fig = go.Figure()
    for choice_num in unique_choices:
        df_sub = df[df["choice_num"] == choice_num]
        y_jittered = choice_num + rng.uniform(-jitter, jitter, size=len(df_sub))
        school_name = result.preferences[choice_num - 1]
        fig.add_trace(
            go.Scattergl(
                x=df_sub["user_rank"],
                y=y_jittered,
                mode="markers",
                marker=dict(color=colors[choice_num], size=7, opacity=0.55),
                name=legend_label(result, choice_num, counts),
                customdata=np.column_stack(
                    [
                        df_sub["user_rank"],
                        np.full(len(df_sub), choice_num),
                        np.full(len(df_sub), school_name),
                    ]
                ),
                hovertemplate=(
                    "Random rank: %{customdata[0]}<br>"
                    "Choice %{customdata[1]}: %{customdata[2]}<extra></extra>"
                ),
            )
        )

    mean_rank = df["user_rank"].mean()
    fig.add_vline(
        x=mean_rank,
        line=dict(color="gray", dash="dot", width=1.5),
        annotation_text=f"Mean rank: {mean_rank:,.0f} / {result.total_places:,}",
        annotation_position="top",
    )

    fig.update_layout(
        title=f"Random Rank Position vs Choice Received ({result.n_runs:,} runs)",
        xaxis_title=f"Random Rank Position (1 = best rank, {result.total_places:,} = worst rank)",
        yaxis=dict(visible=False),
        legend=dict(title="Choice Allocated (Overall %)"),
        hovermode="closest",
        margin=dict(t=60, r=20, b=50, l=20),
        template="plotly_white",
    )
    fig.update_xaxes(range=[0, result.total_places], showgrid=True)
    return fig


def plot_choice_by_rank_bracket_plotly(
    result: SimulationResult,
    n_bins: int = 10,
    cmap: str = DEFAULT_CMAP,
) -> go.Figure:
    """Interactive stacked bar chart of choice allocated, by random rank bracket.

    Hovering a bar segment shows the exact percentage and run count for that
    bracket/choice combination.
    """
    pivot_pct = rank_bracket_pivot(result, n_bins=n_bins)
    bracket_totals = pivot_pct.attrs["bracket_totals"]
    counts = result.raw["choice_num"].value_counts()
    colors = choice_color_map_hex(result.preferences, cmap)

    fig = go.Figure()
    for choice_num in pivot_pct.columns:
        school_name = result.preferences[choice_num - 1]
        pct_values = pivot_pct[choice_num]
        run_counts = (pct_values / 100 * bracket_totals).round().astype(int)
        fig.add_trace(
            go.Bar(
                x=pivot_pct.index.astype(str),
                y=pct_values,
                name=legend_label(result, choice_num, counts),
                marker_color=colors[choice_num],
                customdata=np.column_stack(
                    [np.full(len(pivot_pct), school_name), run_counts]
                ),
                hovertemplate=(
                    f"Choice {choice_num}: " + "%{customdata[0]}<br>"
                    "%{y:.1f}% of this bracket (n=%{customdata[1]})<extra></extra>"
                ),
            )
        )

    # Small "n=" annotation above each bar, so a thin bracket (few runs)
    # isn't mistaken for a confident 100% result.
    for x, total in enumerate(bracket_totals):
        fig.add_annotation(
            x=x, y=102, text=f"n={int(total)}", showarrow=False,
            font=dict(size=10, color="gray"),
        )

    fig.update_layout(
        title=f"Allocation Choice by Random Rank Position ({result.n_runs:,} runs)",
        xaxis_title="Random Rank Percentile Bracket (0-10% = best ranks)",
        yaxis_title="Percentage of Runs (%)",
        yaxis=dict(range=[0, 110]),
        barmode="stack",
        legend=dict(title="Choice Allocated (Overall %)"),
        margin=dict(t=60, r=20, b=50, l=20),
        template="plotly_white",
    )
    return fig
