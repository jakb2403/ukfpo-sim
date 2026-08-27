"""Interactive UKFP allocation simulator - Streamlit app.

Run with:
    streamlit run app.py

Drag your foundation schools into your personal ranking, run the Monte
Carlo simulation, and explore the results with hoverable charts.
"""

import streamlit as st
from streamlit_sortables import sort_items

from ukfp_sim import UKFPSimulator, default_deanery_data, EXAMPLE_PREFERENCES_2026
from ukfp_sim.analysis import compare_results
from ukfp_sim.colors import competitiveness_labels
from ukfp_sim.plotting_plotly import (
    plot_choice_by_rank_bracket_plotly,
    plot_cumulative_comparison_plotly,
    plot_cumulative_probability_plotly,
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
if "scenario_a" not in st.session_state:
    st.session_state.scenario_a = None
if "scenario_b" not in st.session_state:
    st.session_state.scenario_b = None

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
    st.caption("🟥 most competitive → 🟧 → 🟨 → 🟩 least competitive (by places/demand ratio)")

    # Decorate each school with a colour-coded competitiveness emoji + its
    # numeric ratio for display, sort on those decorated labels, then map
    # back to plain school names - st.session_state.preferences must stay
    # plain names, since it's passed straight into UKFPSimulator below and
    # compared against foundation_school elsewhere.
    labels = competitiveness_labels(st.session_state.deanery_data)
    label_to_school = {v: k for k, v in labels.items()}
    decorated_items = [labels[school] for school in st.session_state.preferences]

    # sort_items only re-seeds its displayed items from `items` when its
    # widget (re)mounts under a given `key`. Editing a ratio changes this
    # label text without changing the *set* of school names, so a fixed key
    # would keep showing stale colours/numbers. Deriving the key from the
    # current ratios forces a clean remount whenever they change, without
    # losing the user's drag order (the items passed on remount are still
    # `st.session_state.preferences` in its current sequence, just re-decorated).
    ratio_signature = "_".join(f"{r:.4f}" for r in st.session_state.deanery_data["ratio"])
    sort_key = f"preference_sort_{ratio_signature}"

    sorted_decorated = sort_items(decorated_items, direction="vertical", key=sort_key)
    if all(item in label_to_school for item in sorted_decorated):
        st.session_state.preferences = [label_to_school[item] for item in sorted_decorated]
    # else: stale frontend state slipped through a remount - leave the
    # current order as-is this rerun rather than raising a KeyError.

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

    save_a_col, save_b_col = st.columns(2)
    save_a_clicked = save_a_col.button(
        "💾 Save as Scenario A", width='stretch', disabled=st.session_state.result is None
    )
    save_b_clicked = save_b_col.button(
        "💾 Save as Scenario B", width='stretch', disabled=st.session_state.result is None
    )
    if save_a_clicked:
        st.session_state.scenario_a = st.session_state.result
    if save_b_clicked:
        st.session_state.scenario_b = st.session_state.result
    if st.session_state.scenario_a is not None:
        st.caption(f"✅ Scenario A saved - mean choice {st.session_state.scenario_a.mean_choice:.2f}")
    if st.session_state.scenario_b is not None:
        st.caption(f"✅ Scenario B saved - mean choice {st.session_state.scenario_b.mean_choice:.2f}")

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
        tab_bar, tab_scatter, tab_cumulative, tab_compare, tab_table = st.tabs(
            ["📊 Bar chart", "🔵 Scatter plot", "📈 Cumulative chance", "🆚 A vs B", "📋 Summary table"]
        )
        with tab_bar:
            st.plotly_chart(
                plot_choice_by_rank_bracket_plotly(result), width='stretch'
            )
        with tab_scatter:
            st.plotly_chart(
                plot_rank_vs_choice_scatter_plotly(result), width='stretch'
            )
        with tab_cumulative:
            st.plotly_chart(
                plot_cumulative_probability_plotly(result), width='stretch'
            )
        with tab_compare:
            scenario_a, scenario_b = st.session_state.scenario_a, st.session_state.scenario_b
            if scenario_a is None or scenario_b is None:
                st.info(
                    "Save your current ranking as Scenario A, change your ranking, "
                    "run again, and save it as Scenario B to compare them here."
                )
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric(
                    "Mean choice received (B)",
                    f"{scenario_b.mean_choice:.2f}",
                    delta=f"{scenario_b.mean_choice - scenario_a.mean_choice:+.2f}",
                    delta_color="inverse",  # lower is better
                )
                m2.metric(
                    "Chance of 1st choice (B)",
                    f"{scenario_b.choice_probability(1):.1f}%",
                    delta=f"{scenario_b.choice_probability(1) - scenario_a.choice_probability(1):+.1f}pp",
                )
                m3.metric(
                    "Chance of a top-3 choice (B)",
                    f"{scenario_b.top_n_probability(3):.1f}%",
                    delta=f"{scenario_b.top_n_probability(3) - scenario_a.top_n_probability(3):+.1f}pp",
                )
                st.plotly_chart(
                    plot_cumulative_comparison_plotly(scenario_a, scenario_b), width='stretch'
                )
                st.caption("Sorted by biggest change in probability between scenario A and B.")
                st.dataframe(
                    compare_results(scenario_a, scenario_b), hide_index=True, width='stretch'
                )
        with tab_table:
            st.dataframe(result.summary(), hide_index=True, width='stretch')
