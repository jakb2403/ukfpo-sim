"""Shared choice-number -> colour mapping.

Both the matplotlib charts (`plotting.py`) and the Plotly charts
(`plotting_plotly.py`) use this so that, for example, "Choice 3: KSS" is
drawn in the same colour everywhere - in the bar chart, the scatter plot,
and (via the web app) whichever of the two you're looking at.
"""

from __future__ import annotations

import matplotlib.colors
import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_CMAP = "tab20"

#: Ascending competitiveness: green (least competitive) -> red (most).
_COMPETITIVENESS_PALETTE = ["🟩", "🟨", "🟧", "🟥"]


def choice_color_map(preferences: list[str], cmap_name: str = DEFAULT_CMAP) -> dict:
    """Map each 1-indexed choice number to a stable RGBA colour (0-1 floats)."""
    n = len(preferences)
    cmap = plt.get_cmap(cmap_name, max(n, 1))
    return {i + 1: cmap(i) for i in range(n)}


def choice_color_map_hex(preferences: list[str], cmap_name: str = DEFAULT_CMAP) -> dict:
    """Map each 1-indexed choice number to a stable hex colour string, e.g. for Plotly."""
    return {
        choice_num: matplotlib.colors.to_hex(rgba)
        for choice_num, rgba in choice_color_map(preferences, cmap_name).items()
    }


def competitiveness_emoji_map(deanery_data: pd.DataFrame, n_buckets: int = 4) -> dict:
    """Map each `foundation_school` to a colour-square emoji, by `ratio` quartile.

    Red = most competitive (highest `ratio`), green = least. Buckets are
    computed fresh from the *current* spread of `ratio` values (quantiles,
    not fixed thresholds), so the colouring stays meaningful if a caller
    edits ratios - don't cache the result across a data change.
    """
    ratios = deanery_data["ratio"]
    palette = _COMPETITIVENESS_PALETTE[:n_buckets]
    mid_bucket = len(palette) // 2

    if ratios.nunique() < 2:
        # All ratios identical - "all equal" isn't meaningfully "least
        # competitive", so fall back to the middle of the palette for
        # everyone rather than asking qcut to split a constant series
        # (which produces NaN for every row, not a raised error).
        return dict.fromkeys(deanery_data["foundation_school"], palette[mid_bucket])

    buckets = pd.qcut(ratios, q=n_buckets, labels=False, duplicates="drop")
    # A handful of tied ratios can still leave stray NaNs even when there's
    # more than one distinct value overall - treat those as "middle".
    buckets = buckets.fillna(mid_bucket).astype(int)

    n_actual_buckets = int(buckets.max()) + 1
    if n_actual_buckets < n_buckets:
        # Tied ratios collapsed some quantile bins - rescale so the two
        # extremes of the palette (greenest/reddest) are still used, rather
        # than bunching every school into one end of it.
        scale = (len(palette) - 1) / max(n_actual_buckets - 1, 1)
        buckets = (buckets * scale).round().astype(int)

    return {
        school: palette[bucket]
        for school, bucket in zip(deanery_data["foundation_school"], buckets)
    }


def competitiveness_labels(deanery_data: pd.DataFrame, n_buckets: int = 4) -> dict:
    """Map each `foundation_school` to a decorated label, e.g. "🟥 London (2.31)".

    Combines `competitiveness_emoji_map` with the school's numeric `ratio`.
    Must be rebuilt fresh every call from the current `deanery_data` -
    callers should not cache this across a data edit.
    """
    emoji = competitiveness_emoji_map(deanery_data, n_buckets)
    return {
        school: f"{emoji[school]} {school} ({ratio:.2f})"
        for school, ratio in zip(
            deanery_data["foundation_school"], deanery_data["ratio"]
        )
    }
