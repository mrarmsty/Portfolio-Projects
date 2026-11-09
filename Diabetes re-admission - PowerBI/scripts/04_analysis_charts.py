"""
04_analysis_charts.py
Static analysis charts for the README and analyst report, drawn directly from
data/processed and data/model_outputs (the same data the Power BI report uses).
"""
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "charts"; OUT.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, AQUA, GREY, INK, INK2, SURF = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29c", "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#d9d8d3",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF,
                     "axes.facecolor": SURF, "axes.grid": True, "grid.color": "#ecebe7", "grid.linewidth": 0.8, "axes.axisbelow": True})

f = pd.read_csv(ROOT / "data/processed/fact_encounter_clean.csv", low_memory=False)
dd = pd.read_csv(ROOT / "data/processed/dim_discharge_disposition.csv")
f = f.merge(dd[["discharge_disposition_id", "discharge_disposition_group"]], on="discharge_disposition_id")
e = f[f.eligible_for_readmission == 1]
overall = e.readmit_30.mean()

def finish(ax, title, subtitle, name, pct_axis="y"):
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold", pad=22)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=INK2)
    fmt = matplotlib.ticker.PercentFormatter(1.0, decimals=0)
    (ax.yaxis if pct_axis == "y" else ax.xaxis).set_major_formatter(fmt)
    ax.figure.text(0.01, 0.01, "Source: Diabetes 130-US Hospitals 1999-2008 (UCI). Eligible encounters exclude death/hospice discharges.",
                   fontsize=7.5, color=GREY)
    ax.figure.tight_layout(rect=(0, 0.03, 1, 1))
    ax.figure.savefig(OUT / name, dpi=200); plt.close(ax.figure)

def ref_line(ax, horizontal=True):
    if horizontal:
        ax.axhline(overall, color=INK2, lw=1, ls="--")
    else:
        ax.axvline(overall, color=INK2, lw=1, ls="--")

# 1 prior inpatient
order = ["0", "1", "2", "3-4", "5+"]
g = e.groupby("prior_inpatient_band").readmit_30.agg(["mean", "size"]).reindex(order)
fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(g.index, g["mean"], color=BLUE, width=0.6, edgecolor=SURF, linewidth=2)
for b_, (m, n) in zip(bars, g.values):
    ax.text(b_.get_x() + b_.get_width() / 2, m + 0.006, f"{m:.1%}", ha="center", fontsize=9, color=INK)
    ax.text(b_.get_x() + b_.get_width() / 2, 0.006, f"n={int(n):,}", ha="center", fontsize=7.5, color="white")
ax.set_xlabel("Inpatient visits in the year before the encounter"); ax.set_ylabel("30-day readmission rate"); ax.grid(axis="x", visible=False)
ref_line(ax)
finish(ax, "Readmission risk rises steadily with prior inpatient visits",
       "30-day readmission rate by prior-year inpatient visits; dashed line = overall rate 11.4%", "01_rate_by_prior_inpatient.png")

# 2 discharge group
g = e.groupby("discharge_disposition_group").readmit_30.agg(["mean", "size"])
g = g[g["size"] >= 500].sort_values("mean")
fig, ax = plt.subplots(figsize=(8, 4.5))
cols = [ORANGE if m >= overall * 1.2 else BLUE for m in g["mean"]]
ax.barh(g.index, g["mean"], color=cols, height=0.6, edgecolor=SURF, linewidth=2)
for i, (m, n) in enumerate(g.values):
    ax.text(m + 0.004, i, f"{m:.1%}  (n={int(n):,})", va="center", fontsize=8.5, color=INK)
ax.set_xlim(0, g["mean"].max() * 1.35); ax.grid(axis="y", visible=False); ax.set_xlabel("30-day readmission rate")
ref_line(ax, horizontal=False)
finish(ax, "Discharge destination separates risk the most",
       "500+ encounters per group; orange = 1.2x overall or more; dashed = 11.4% overall",
       "02_rate_by_discharge_group.png", pct_axis="x")

# 3 age
order = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-90", "90-100"]
g = e.groupby("age_band").readmit_30.agg(["mean", "size"]).reindex(order)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(g.index, g["mean"], color=BLUE, width=0.6, edgecolor=SURF, linewidth=2)
for i, (m, n) in enumerate(g.values):
    ax.text(i, m + 0.005, f"{m:.1%}", ha="center", fontsize=8.5, color=INK)
ax.set_xlabel("Age band (years)"); ax.grid(axis="x", visible=False); ref_line(ax)
finish(ax, "Among adults, age moves the rate only between about 10% and 13%",
       "30-day rate by age band; dashed = overall 11.4%; bands under 30 have fewer than 1,700 encounters each", "03_rate_by_age.png")

# 4 ROC
roc = pd.read_csv(ROOT / "data/model_outputs/model_roc_curve.csv")
mm = pd.read_csv(ROOT / "data/model_outputs/model_metrics.csv").set_index("model")
fig, ax = plt.subplots(figsize=(6.5, 5.5))
for name, c in [("Random Forest", BLUE), ("Logistic Regression", ORANGE)]:
    d = roc[roc.model == name]; ax.plot(d.fpr, d.tpr, color=c, lw=2, label=f"{name} (AUC {mm.loc[name, 'test_auc']:.3f})")
ax.plot([0, 1], [0, 1], color=GREY, lw=1.2, ls="--", label="Random guess (AUC 0.500)")
ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate (recall)")
ax.legend(frameon=False, loc="lower right", fontsize=9); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
finish(ax, "Both models rank risk moderately well", "ROC curves on 19,802 held-out test encounters (patient-grouped split)",
       "04_roc_curves.png")
for a in []: pass

# 5 deciles
p = pd.read_csv(ROOT / "data/model_outputs/encounter_predictions.csv")
t = p[p.data_split == "Test"].merge(f[["encounter_id", "readmit_30"]], on="encounter_id")
g = t.groupby("risk_decile").readmit_30.mean()
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(g.index.astype(int).astype(str), g.values, color=[ORANGE if i >= 9 else BLUE for i in g.index], width=0.6, edgecolor=SURF, linewidth=2)
for i, m in enumerate(g.values):
    ax.text(i, m + 0.005, f"{m:.1%}", ha="center", fontsize=8.5, color=INK)
ax.axhline(t.readmit_30.mean(), color=INK2, lw=1, ls="--")
ax.set_xlabel("Random Forest risk decile (1 = lowest predicted risk)"); ax.grid(axis="x", visible=False)
finish(ax, "The highest-risk decile readmits at 2.5x the average",
       "Observed 30-day rate by predicted-risk decile, test set; dashed = test average 11.2%; orange = deciles 9-10", "05_risk_deciles.png")

# 6 threshold trade-off
c = pd.read_csv(ROOT / "data/model_outputs/model_threshold_curve.csv")
c = c[(c.model == "Random Forest") & (c.threshold >= 0.05) & (c.threshold <= 0.30)]
fig, ax = plt.subplots(figsize=(8, 4.5))
for col, colr, lab in [("recall", BLUE, "Recall (readmissions caught)"), ("precision", ORANGE, "Precision (alerts that are right)"),
                       ("alert_rate", AQUA, "Alert rate (discharges flagged)")]:
    ax.plot(c.threshold, c[col], color=colr, lw=2, label=lab)
r = c[np.isclose(c.threshold, 0.15)].iloc[0]
ax.axvline(0.15, color=GREY, lw=1, ls=":")
ax.text(0.155, 0.62, f"15% threshold: recall {r.recall:.0%},\nprecision {r.precision:.0%}, alerts {r.alert_rate:.0%}", fontsize=8.5, color=INK2, va="top")
ax.set_xlabel("Risk threshold"); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
ax.legend(frameon=False, fontsize=9, loc="upper right"); ax.set_ylim(0, 1)
finish(ax, "Choosing the alert threshold is a capacity decision",
       "Random Forest, test set, thresholds 5%-30% (above 30% too few alerts for stable precision)", "06_threshold_tradeoff.png")
print(sorted(x.name for x in OUT.iterdir()))
