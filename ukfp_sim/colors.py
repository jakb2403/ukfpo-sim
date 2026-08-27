"""Shared choice-number -> colour mapping.

Both the matplotlib charts (`plotting.py`) and the Plotly charts
(`plotting_plotly.py`) use this so that, for example, "Choice 3: KSS" is
drawn in the same colour everywhere - in the bar chart, the scatter plot,
and (via the web app) whichever of the two you're looking at.
"""

from __future__ import annotations

import matplotlib.colors
import matplotlib.pyplot as plt

DEFAULT_CMAP = "tab20"


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
