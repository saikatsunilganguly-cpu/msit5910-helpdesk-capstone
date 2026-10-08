"""
Redraws the two-panel chart used in the Unit 6 reports (accuracy by category on the
left, latency distribution on the right) from the saved results files.

    python evaluation/make_chart.py              uses evaluation/results/        (your own run)
    python evaluation/make_chart.py --original   uses results_unit6_original_run (the reports' data)
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--original", action="store_true", help="use the results the Unit 6 reports were built from")
args = ap.parse_args()

src = HERE / ("results_unit6_original_run" if args.original else "results")
acc_file, lat_file = src / "accuracy_results.json", src / "latency_results.json"
if not (acc_file.exists() and lat_file.exists()):
    sys.exit(f"Missing results in {src}. Run measure_accuracy.py and measure_latency.py first.")
acc = json.load(open(acc_file, encoding="utf-8"))
lat = json.load(open(lat_file, encoding="utf-8"))

keys = ["Password / Account Access", "Hardware Issue", "Software / Application Error",
        "Network Connectivity", "Access Request / Permissions"]
labels = ["Password /\nAccount Access", "Hardware\nIssue", "Software /\nApplication Error",
          "Network\nConnectivity", "Access Request /\nPermissions"]
accs = [acc["per_category"][k]["correct"] / acc["per_category"][k]["total"] * 100 for k in keys]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
bars = axes[0].bar(labels, accs, color=["#4a7fb5" if a == 100 else "#c9922f" for a in accs],
                   edgecolor="#2c5f8a", linewidth=0.8)
axes[0].set_ylim(0, 110)
axes[0].set_ylabel("Accuracy (%)")
axes[0].set_title(f"Categorisation accuracy by category\n(overall: {acc['accuracy_pct']:.1f}%, n={acc['total']})", fontsize=10)
axes[0].axhline(100, color="#ccc", linewidth=0.5, linestyle="--")
for b, a in zip(bars, accs):
    axes[0].text(b.get_x() + b.get_width() / 2, a + 2, f"{a:.0f}%", ha="center", fontsize=9)
axes[0].tick_params(axis="x", labelsize=8)

axes[1].hist(lat, bins=15, color="#4a7fb5", edgecolor="#2c5f8a", linewidth=0.8)
mean = sum(lat) / len(lat)
axes[1].axvline(mean, color="#c9922f", linestyle="--", linewidth=1.5, label=f"Mean = {mean:.2f} ms")
axes[1].set_xlabel("Latency (ms)")
axes[1].set_ylabel("Number of requests")
axes[1].set_title(f"POST /submit latency distribution\n(n={len(lat)} real HTTP requests)", fontsize=10)
axes[1].legend(fontsize=8)

plt.tight_layout()
out = src / "chart_metrics.png" if not args.original else HERE / "results" / "chart_from_original_data.png"
out.parent.mkdir(exist_ok=True)
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {out}")
