"""Interactive UKFP allocation simulator - Streamlit app.

Run with:
    streamlit run app.py

Drag your foundation schools into your personal ranking, run the Monte
Carlo simulation, and explore the results with hoverable charts.
"""

import streamlit as st
from streamlit_sortables import sort_items

from ukfp_sim import (
    DATA_SOURCE_LABEL,
    DATA_SOURCE_URL,
    DEANERY_DATA_BY_YEAR,
    LATEST_YEAR,
    UKFPSimulator,
    default_deanery_data,
    deanery_data_for_year,
    EXAMPLE_PREFERENCES_2026,
)
from ukfp_sim.analysis import compare_results
from ukfp_sim.colors import competitiveness_labels
from ukfp_sim.plotting_plotly import (
    plot_choice_by_rank_bracket_plotly,
    plot_cumulative_comparison_plotly,
    plot_cumulative_probability_plotly,
    plot_rank_vs_choice_scatter_plotly,
)

st.set_page_config(page_title="UKFP Allocation Simulator", layout="wide")

# ---------------------------------------------------------------------------
# Session state (persists across reruns of this script, per browser session)
# ---------------------------------------------------------------------------
if "deanery_data" not in st.session_state:
    st.session_state.deanery_data = default_deanery_data()
if "data_year" not in st.session_state:
    st.session_state.data_year = LATEST_YEAR
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
if "show_intro" not in st.session_state:
    st.session_state.show_intro = True
if "show_methodology" not in st.session_state:
    st.session_state.show_methodology = False


# ---------------------------------------------------------------------------
# Popups: first-load instructions/disclaimer, and "how it works" methodology
# ---------------------------------------------------------------------------
@st.dialog("👋 Welcome to the UKFP Allocation Simulator", width="large")
def _intro_dialog():
    st.markdown(
        """
This tool runs a **Monte Carlo simulation** of the UK Foundation Programme
(UKFP) allocation lottery, to estimate your chance of landing each of your
ranked foundation-school preferences.

**How to use it:**
1. **Drag your foundation schools into your own ranking**
   (1st choice at the top). Each one is colour-coded by how competitive it
   is, so you can see the landscape before you start.
2. Pick how many simulated runs to use, then click **▶️ Run simulation**.
3. Explore the results in the tabs on the right - a bar chart, a scatter
   plot, a cumulative "chance of a top-N choice" chart, and a summary
   table.
4. Want to compare two rankings? Save one as **Scenario A**, change your
   ranking, run again, save it as **Scenario B**, and see exactly what
   changed in the **🆚 A vs B** tab.

You can revisit this message any time from the **ℹ️ How to use this app**
button, and see exactly how the numbers are calculated under
**📖 How the simulation works**.
        """
    )
    st.warning(
        "**Disclaimer:** this is a simplified statistical model, not a "
        "prediction. It does **not** reflect how real applicants actually "
        "rank foundation schools, or any real allocation data - it makes "
        "simplifying assumptions (see **How the simulation works**) to turn "
        "published places/competition-ratio figures into a plausible-looking "
        "population. Treat every percentage here as a rough, illustrative "
        "estimate - a pinch of salt, not a guarantee - and not a substitute "
        "for official UKFPO guidance.",
        icon="⚠️",
    )
    if st.button("Got it - let's go", type="primary", width="stretch"):
        st.session_state.show_intro = False
        st.rerun()


@st.dialog("📖 How the simulation works", width="large")
def _methodology_dialog():
    st.markdown(
        """
Each simulated run builds a synthetic "everyone else" applicant pool sized
to fill every place exactly, then allocates places by a random rank order -
repeating this many times builds up a distribution of "which choice did you
end up with?".

#### 1. How many synthetic applicants pick each school 1st

For each foundation school $s$, take its number of places $p_s$ and its
published first-choice competition ratio $r_s$ (applicants-per-place style
demand weighting). The implied 1st-choice demand is $p_s r_s$, which is then
rescaled so the total number of synthetic 1st choices exactly equals the
total number of places $P = \\sum_s p_s$:
        """
    )
    st.latex(
        r"n_s = \mathrm{round}\!\left(p_s\, r_s \cdot \frac{P}{\sum_{k} p_k\, r_k}\right)"
    )
    st.markdown(
        """
$n_s$ synthetic applicants are then given school $s$ as their 1st choice.

#### 2. How choices 2 through 18 are chosen

There's no published data on how people rank schools they *don't* put
first, so the simulator reuses the **same first-choice ratios $r_s$** to
drive every later choice too - i.e. it assumes "how popular a school is as
a 1st choice" is also a reasonable stand-in for "how popular it is as a
2nd, 3rd, ... 18th choice" among people who didn't rank it 1st. This is a
simplifying assumption, not something backed by real preference data.

Concretely, once an applicant's 1st choice is fixed, their ranking of the
remaining schools is drawn from a **Plackett-Luce model** using those same
ratios as weights: having already ranked some schools, the next one is
picked from the schools left, with probability proportional to its ratio:
        """
    )
    st.latex(
        r"P(\text{next choice} = j \mid \text{remaining schools } R) "
        r"= \frac{r_j}{\sum_{k \in R} r_k}"
    )
    st.markdown(
        """
Sampling a full ranking this way, one position at a time, is equivalent
(via the **Gumbel-max trick**) to a single vectorised step: draw one Gumbel
noise value per remaining school, add it to the log-ratio, and sort:
        """
    )
    st.latex(
        r"\mathrm{score}_j = \ln(r_j) + G_j, \qquad "
        r"G_j \overset{\text{iid}}{\sim} \mathrm{Gumbel}(0, 1)"
    )
    st.markdown(
        """
sorting the remaining schools by $\\mathrm{score}_j$ (descending) gives that
applicant's full order of choices 2 through 18. This is the trick the code
actually uses, since it's exact and much faster than sampling position by
position.

#### 3. Where "you" fit in

Every simulated run, you are given a uniformly random rank position among
the *entire* applicant pool (synthetic applicants + you):
        """
    )
    st.latex(r"U \sim \mathrm{Uniform}\{1, 2, \dots, P + 1\}")
    st.markdown(
        """
just as you would in the actual draw.

#### 4. Allocation

Places are then allocated in two passes, in rank
order - matching the real UKFP process: on the first pass, everyone tries their 1st choice
first (in rank order, best rank first); anyone who missed out is skipped on this pass.
On the second pass, all the remaining applicants are processed in rank order and 
allocated the next foundation school on their list which still has space. Your recorded outcome is whichever of
*your* ranked choices you ended up with.

Repeating steps 1-4 for many runs builds up the probability of ending up
with each of your choices - that's what the charts show.
        """
    )
    if st.button("Close", width="stretch"):
        st.session_state.show_methodology = False
        st.rerun()


if st.session_state.show_intro:
    _intro_dialog()
if st.session_state.show_methodology:
    _methodology_dialog()

# ---------------------------------------------------------------------------
# Title row
# ---------------------------------------------------------------------------
title_col, info_col, howitworks_col = st.columns([6, 1.4, 1.7])
with title_col:
    st.title("UKFP Allocation Simulator")
with info_col:
    st.write("")
    if st.button("ℹ️ How to use this app", width="stretch"):
        st.session_state.show_intro = True
        st.rerun()
with howitworks_col:
    st.write("")
    if st.button("📖 How the simulation works", width="stretch"):
        st.session_state.show_methodology = True
        st.rerun()

st.caption(
    "Monte Carlo simulation of the UK Foundation Programme allocation lottery. "
    "Drag your foundation schools into your personal ranking, run the "
    "simulation, and see how likely each outcome is."
)
st.caption(
    "This is a simplified statistical model, not a prediction of how "
    "people actually choose - see **How the simulation works** above, and "
    "take every percentage with a pinch of salt."
)

# A keyed widget's latest value is available in session_state as soon as a
# rerun starts (from the user's interaction), even before the widget itself
# is drawn later in the script by `st.selectbox(..., key="data_year_select")`
# down in the main panel. Apply a data-year change here, before the
# sidebar's data editor renders below, so it doesn't show a stale year for
# one extra rerun.
_pending_year = st.session_state.get("data_year_select", st.session_state.data_year)
if _pending_year != st.session_state.data_year:
    st.session_state.data_year = _pending_year
    st.session_state.deanery_data = deanery_data_for_year(_pending_year)

# ---------------------------------------------------------------------------
# Sidebar: optional manual editing of the foundation school data
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Foundation school data")
    with st.expander("Advanced: edit places / ratio"):
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
    st.subheader("Simulation settings")

    year_options = sorted(DEANERY_DATA_BY_YEAR, reverse=True)
    st.selectbox(
        "Data year",
        year_options,
        index=year_options.index(st.session_state.data_year),
        help="Which year's published places/competition-ratio figures to simulate with.",
        key="data_year_select",
    )
    st.caption(f"Source: [{DATA_SOURCE_LABEL}]({DATA_SOURCE_URL})")

    n_runs = st.slider(
        "Number of simulated runs",
        min_value=100,
        max_value=3000,
        value=500,
        step=100,
        help="More runs = smoother/more reliable percentages, but slower. "
        "~500 runs takes a few seconds; 3,000 can take half a minute or so.",
    )
    with st.expander("Advanced: fixed random seed"):
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
