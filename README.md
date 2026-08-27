# ukfpo-sim

Monte Carlo simulator for UK Foundation Programme (UKFP) allocation: given
each foundation school's places/competitiveness and your ranked preference
list, estimates the probability of landing each choice.

## Interactive app (recommended)

[app.py](app.py) is a [Streamlit](https://streamlit.io) web app: drag your
foundation schools into your ranking, click **Run simulation**, and explore
the results with hoverable/zoomable charts. It runs entirely on your own
machine - Streamlit just opens a local page in your normal browser, nothing
is uploaded anywhere.

Decision-support features, beyond the original bar/scatter charts:
- **Competitiveness colour-coding** on the draggable list itself - each
  school shows its demand/places ratio and a 🟥🟧🟨🟩 colour (red = most
  competitive, green = least), so you can see the landscape before you even
  start ranking.
- **Cumulative "chance of top-N" chart** - a quick read on "how safe is my
  list overall?" (e.g. what's my chance of landing one of my top 3?).
- **Scenario A vs B comparison** - save your current ranking as "Scenario
  A", tweak it (e.g. swap two schools), run again, save as "Scenario B",
  and see exactly what changed: headline metric deltas, an overlaid
  cumulative-chance chart, and a per-school probability table sorted by
  biggest change - directly answers "should I swap these two?".

### Setup (once), on macOS

Open Terminal, `cd` into this folder, then:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running it

Every time you want to use it:

```bash
cd path/to/ukfpo-amy
source .venv/bin/activate
streamlit run app.py
```

This opens the app in your browser automatically (`Ctrl+C` in the terminal
to stop it). Send your friend the same three setup commands once, then just
the three "running it" commands whenever they want to use it.

## Module: `ukfp_sim`

The simulation logic (originally prototyped in [ukfp_sim.ipynb](ukfp_sim.ipynb))
lives in the [ukfp_sim/](ukfp_sim/) package, so it's shared by the notebook,
`app.py`, and any script - no copy-pasted logic to keep in sync:

```python
from ukfp_sim import UKFPSimulator, default_deanery_data, EXAMPLE_PREFERENCES_2026

sim = UKFPSimulator(
    deanery_data=default_deanery_data(),   # swap in your own school data
    user_preferences=EXAMPLE_PREFERENCES_2026,  # swap in your own ranking
    n_runs=1000,
    seed=42,  # optional, for reproducible results
)

result = sim.run()          # -> SimulationResult
sim.summary()                # per-choice probability table
sim.plot_bar()                # stacked bar chart: choice vs. rank bracket (matplotlib)
sim.plot_scatter()            # scatter: rank position vs. choice received (matplotlib)
sim.plot_bar_plotly()         # same charts, interactive/hoverable (used by app.py)
sim.plot_scatter_plotly()
sim.plot_cumulative()         # cumulative "chance of top-N" chart (matplotlib)
sim.plot_cumulative_plotly()  # ...and its interactive version
sim.rerun()                   # re-run with fresh randomness, same setup
```

See [example_usage.py](example_usage.py) for a runnable script, or
`ukfp_sim.ipynb` for the interactive notebook version.

- `ukfp_sim/simulator.py` - the `UKFPSimulator` class (setup + Monte Carlo core).
- `ukfp_sim/results.py` - `SimulationResult`: the output of a run, plus summary stats.
- `ukfp_sim/plotting.py` / `plotting_plotly.py` - bar/scatter charts, matplotlib and Plotly versions.
- `ukfp_sim/analysis.py`, `colors.py` - shared logic (rank-bracket binning, choice colour mapping) used by both chart backends.
- `ukfp_sim/data.py` - example/reference deanery data.

### Performance note

Each simulated run allocates ~10,000+ synthetic applicants across all
schools, so it's not free - expect roughly 15-20ms per run (~500 runs in a
few seconds, ~3,000 in well under a minute). The allocation logic is an
inherently sequential process (each applicant's outcome depends on every
higher-priority applicant's outcome already having been decided), so it
can't be vectorised away entirely; if it ever needs to be faster (e.g. much
larger run counts), the next lever would be running batches of simulations
across multiple CPU cores in parallel.

### Setup (plain pip, any OS)

```
pip install -r requirements.txt
```

### Roadmap

Done: a Streamlit-based interactive UI (`app.py`) with drag-and-drop
preference ranking and hoverable charts, in place of the originally
planned Tkinter version.
