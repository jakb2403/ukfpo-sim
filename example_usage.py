"""Example: using the ukfp_sim module the same way the notebook did.

Run with: python example_usage.py
"""

from ukfp_sim import EXAMPLE_PREFERENCES_2026, UKFPSimulator, default_deanery_data

sim = UKFPSimulator(
    deanery_data=default_deanery_data(),
    user_preferences=EXAMPLE_PREFERENCES_2026,
    n_runs=1000,
    seed=42,  # omit for fresh randomness each run
)

result = sim.run()
print(result.summary().to_string(index=False))
print(f"\nMean choice received: {result.mean_choice:.2f}")
print(f"P(top 3 choice): {result.top_n_probability(3):.1f}%")

# Re-run the same simulator with fresh randomness and compare:
result2 = sim.rerun()
print(f"\nAfter rerun - mean choice received: {result2.mean_choice:.2f}")

# Charts (close the window, or set show=False and use fig.savefig(...) instead)
sim.plot_bar()
sim.plot_scatter()
