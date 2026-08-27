"""Interactive UKFP allocation simulator - Streamlit app.

Run with:
    streamlit run app.py

Drag your foundation schools into your personal ranking, run the Monte
Carlo simulation, and explore the results with hoverable charts.
"""

import streamlit as st
from streamlit_sortables import sort_items

from ukfp_sim import UKFPSimulator, default_deanery_data, EXAMPLE_PREFERENCES_2026
from ukfp_sim.plotting_plotly import (
    plot_choice_by_rank_bracket_plotly,
    plot_rank_vs_choice_scatter_plotly,
)

st.set_page_config(page_title="UKFP Allocation Simulator", layout="wide")

st.title("UKFP Allocation Simulator")
st.caption(
    "Monte Carlo simulation of the UK Foundation Programme allocation lottery. "
    "Drag your foundation schools into your personal ranking, run the "
    "simulation, and see how likely each outcome is."
)

# ---------------------------------------------------------------------------
# Session state (persists across reruns of this script, per browser session)
# ---------------------------------------------------------------------------
if "deanery_data" not in st.session_state:
    st.session_state.deanery_data = default_deanery_data()
if "preferences" not in st.session_state:
    st.session_state.preferences = list(EXAMPLE_PREFERENCES_2026)
if "simulator" not in st.session_state:
    st.session_state.simulator = None
if "result" not in st.session_state:
    st.session_state.result = None

# ---------------------------------------------------------------------------
# Sidebar: run settings + (optional) editable school data
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Simulation settings")
    n_runs = st.slider(
        "Number of simulated runs",
        min_value=100,
        max_value=3000,
        value=500,
        step=100,
        help="More runs = smoother/more reliable percentages, but slower. "
        "~500 runs takes a few seconds; 3,000 can take half a minute or so.",
    )
    seed_enabled = st.checkbox(
        "Use a fixed random seed",
        value=False,
        help="On: Run/Rerun always give the exact same result (reproducible). "
        "Off (default): Rerun draws fresh randomness each time.",
    )
    seed = None
    if seed_enabled:
        seed = int(st.number_input("Seed", value=42, step=1))

    st.divider()
    with st.expander("Foundation school data (advanced)"):
        st.caption("Edit places / competition ratio per school if you want to try different assumptions.")
        st.session_state.deanery_data = st.data_editor(
            st.session_state.deanery_data,
            hide_index=True,
            num_rows="fixed",
            width='stretch',
            key="deanery_editor",
        )

# Keep the ranking in sync if the school data was edited (e.g. a name changed)
current_schools = list(st.session_state.deanery_data["foundation_school"])
if set(st.session_state.preferences) != set(current_schools):
    st.session_state.preferences = current_schools

# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------
left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("Your ranking")
    st.caption("Drag to reorder - 1st choice at the top.")
    st.session_state.preferences = sort_items(
        st.session_state.preferences,
        direction="vertical",
        key="preference_sort",
    )

    run_col, rerun_col = st.columns(2)
    run_clicked = run_col.button(
        "▶️ Run simulation", width='stretch', type="primary"
    )
    rerun_clicked = rerun_col.button(
        "🔁 Rerun (new draw)",
        width='stretch',
        disabled=st.session_state.simulator is None,
        help="Re-run the same setup with fresh randomness, without rebuilding it.",
    )

    if run_clicked:
        with st.spinner(f"Running {n_runs:,} simulations..."):
            sim = UKFPSimulator(
                deanery_data=st.session_state.deanery_data,
                user_preferences=st.session_state.preferences,
                n_runs=n_runs,
                seed=seed,
            )
            st.session_state.simulator = sim
            st.session_state.result = sim.run()

    elif rerun_clicked and st.session_state.simulator is not None:
        with st.spinner(f"Re-running {n_runs:,} simulations..."):
            st.session_state.result = st.session_state.simulator.rerun(
                n_runs=n_runs, seed=seed
            )

    result = st.session_state.result
    if result is not None:
        st.divider()
        st.metric("Chance of 1st choice", f"{result.choice_probability(1):.1f}%")
        st.metric("Chance of a top-3 choice", f"{result.top_n_probability(3):.1f}%")
        st.metric("Mean choice received", f"{result.mean_choice:.2f}")

with right:
    result = st.session_state.result
    if result is None:
        st.info("Set your ranking on the left and click **Run simulation** to see results.")
    else:
        tab_bar, tab_scatter, tab_table = st.tabs(
            ["📊 Bar chart", "🔵 Scatter plot", "📋 Summary table"]
        )
        with tab_bar:
            st.plotly_chart(
                plot_choice_by_rank_bracket_plotly(result), width='stretch'
            )
        with tab_scatter:
            st.plotly_chart(
                plot_rank_vs_choice_scatter_plotly(result), width='stretch'
            )
        with tab_table:
            st.dataframe(result.summary(), hide_index=True, width='stretch')
