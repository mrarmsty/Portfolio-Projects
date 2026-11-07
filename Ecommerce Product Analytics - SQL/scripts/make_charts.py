"""Builds the portfolio charts from the SQL result files.

Every chart reads a CSV written by scripts/run_sql_project.py (outputs/results/ or data/processed/); no figure is
computed in Python beyond sorting and formatting. Run from the repository root after the SQL project has run:
    python scripts/make_charts.py
"""
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "outputs" / "results"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#b9b8b3"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
LBL = dict(facecolor=SURFACE, edgecolor="none", pad=0.6)
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"], "font.size": 10, "text.color": INK,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlesize": 12.5, "axes.titleweight": "semibold",
    "axes.titlelocation": "left", "axes.titlepad": 12, "axes.spines.top": False, "axes.spines.right": False,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "axes.grid": False, "grid.color": GRID, "grid.linewidth": 0.6,
    "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.25,
})


def note(fig, text):
    fig.text(0.01, -0.02, text, ha="left", va="top", fontsize=8.2, color=MUTED, wrap=True)


def save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)
    print("wrote", name)


def funnel():
    d = pd.read_csv(RES / "Q07_user_funnel.csv")
    d = d[d.stage_no >= 2].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    y = range(len(d))[::-1]
    shades = [SEQ[5], SEQ[4], SEQ[3], SEQ[2]]
    ax.barh(list(y), d.users, color=shades, height=0.62)
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.text(r.users + 300, yi, f"{r.users:,.0f} users  ({r.pct_of_product_viewers:.1f}% of viewers)",
                va="center", fontsize=9.5, color=INK)
    for i in range(1, len(d)):
        r = d.iloc[i]
        ax.text(-400, list(y)[i] + 0.5, f"−{r.step_dropoff_pct:.1f}%", ha="right", va="center",
                fontsize=9, color=ORANGE if r.dropoff_rank == 1 else INK2,
                fontweight="semibold" if r.dropoff_rank == 1 else "normal")
    ax.set_yticks(list(y), d.stage)
    ax.tick_params(axis="y", length=0, pad=56)
    ax.set_xlim(0, d.users.max() * 1.55)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
    ax.set_xlabel("Users (closed funnel: each stage also reached the earlier ones)")
    ax.spines["left"].set_visible(False)
    ax.set_title("The largest drop-off is between viewing a product and adding it to cart")
    note(fig, "Source: Q07_user_funnel (SQL). 26 weeks, 30,000 users. Orders table is the system of record for purchases. "
              "Orange = largest step drop-off.")
    save(fig, "01_user_funnel.png")


def weekly():
    d = pd.read_csv(RES / "Q28_weekly_kpis.csv")
    d["label"] = pd.to_datetime(d.week_start).dt.strftime("%d %b")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.6, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.6, 1], "hspace": 0.32})
    x = range(len(d))
    a1.bar(x, d.returning_users, color=BLUE, width=0.72, label="Returning users")
    a1.bar(x, d.new_users, bottom=d.returning_users, color=ORANGE, width=0.72, label="New users (first observed week)",
           edgecolor=SURFACE, linewidth=1)
    a1.set_ylabel("Weekly active users")
    a1.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    a1.yaxis.grid(True); a1.set_axisbelow(True)
    a1.legend(frameon=False, loc="upper left", fontsize=9, ncol=2)
    a1.set_title("Weekly active users were flat until Black Friday, then fell back")
    pk = d.active_users.idxmax()
    a1.annotate(f"Black Friday week\n{d.active_users[pk]:,} users", (pk, d.active_users[pk]), xytext=(pk + 0.9, d.active_users[pk] - 420),
                fontsize=9, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    a2.plot(list(x), d.session_conversion_pct, color=BLUE, lw=2, marker="o", ms=3.5)
    a2.set_ylabel("Sessions with an order (%)")
    a2.yaxis.grid(True); a2.set_axisbelow(True)
    a2.set_ylim(5, 10.5)
    a2.set_title("Session conversion by week", fontsize=11)
    a2.set_xticks(list(x)[::2], d.label[::2], rotation=0, fontsize=8.5)
    note(fig, "Source: Q28_weekly_kpis (vw_weekly_kpis). Weeks start on Monday; week 1 counts every user as new because the data starts on 7 Jul 2025.")
    save(fig, "02_weekly_active_users.png")


def cohort_heatmap():
    d = pd.read_csv(PROC / "cohort_retention.csv")
    d = d[(d.week_offset >= 1) & (d.week_offset <= 12)]
    m = d.pivot(index="cohort_start", columns="week_offset", values="retention_pct")
    fig, ax = plt.subplots(figsize=(9.4, 8.2))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", SEQ)
    cmap.set_bad(SURFACE)
    im = ax.imshow(m.values, cmap=cmap, vmin=0, vmax=40, aspect="auto")
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.6, color="white" if v >= 20 else INK)
    ax.set_xticks(range(m.shape[1]), [f"W{c}" for c in m.columns])
    labels = pd.to_datetime(m.index).strftime("%d %b")
    sizes = d.groupby("cohort_start").cohort_users.first().reindex(m.index)
    ax.set_yticks(range(m.shape[0]), [f"{l}  ({n:,})" for l, n in zip(labels, sizes)], fontsize=8.3)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("Weeks after the cohort's first observed week")
    ax.set_ylabel("Cohort (first week, users)")
    ax.set_title("Weekly cohort retention (% of cohort active in week N)")
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.outline.set_visible(False); cb.set_label("% active", color=INK2)
    note(fig, "Source: cohort_retention / vw_cohort_retention (recursive CTE). Blank cells are weeks not yet observed. "
              "The first two cohorts include customers who existed before the window, which inflates their retention.")
    save(fig, "03_cohort_retention_heatmap.png")


def product_scatter():
    d = pd.read_csv(PROC / "product_scorecard.csv")
    opp = set(pd.read_csv(RES / "Q15_high_interest_low_conversion.csv").product_id)
    d["vtp"] = 100 * d.view_to_purchase_rate
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    o = d[~d.product_id.isin(opp)]
    h = d[d.product_id.isin(opp)]
    ax.scatter(o.views, o.vtp, s=22, color=GREY, edgecolor=SURFACE, linewidth=0.8, label="Other products", zorder=2)
    ax.scatter(h.views, h.vtp, s=34, color=ORANGE, edgecolor=SURFACE, linewidth=0.8,
               label="Top view quartile, bottom conversion quartile (19)", zorder=3)
    ax.set_xscale("log")
    ax.axvline(d.median_views.iloc[0], color=AXIS, lw=0.9, ls="--", zorder=1)
    ax.axhline(100 * d.median_conversion.iloc[0], color=AXIS, lw=0.9, ls="--", zorder=1)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlabel("Product views (log scale)")
    ax.set_ylabel("Viewers who bought the product (%)")
    ax.yaxis.grid(True); ax.set_axisbelow(True)
    for pid, dx, dy in [("P0022", -10, -14), ("P0127", 8, 0), ("P0108", 8, -4), ("P0174", 8, 0), ("P0151", 8, -6)]:
        r = d[d.product_id == pid].iloc[0]
        ax.annotate(r.product_name, (r.views, r.vtp), xytext=(dx, dy), textcoords="offset points",
                    fontsize=8.3, color=INK2, ha="left" if dx > 0 else "right")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.set_title("Popular products do not convert better (Spearman ρ = −0.18)")
    note(fig, "Source: vw_product_scorecard and Q15 (SQL). 250 products; dashed lines are catalogue medians. "
              "Conversion = viewers of the product who later bought it.")
    save(fig, "04_product_views_vs_conversion.png")


def categories():
    d = pd.read_csv(RES / "Q16_category_performance.csv").sort_values("orders")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 4.6), sharey=True, gridspec_kw={"wspace": 0.08})
    a1.barh(d.category_name, d.orders, color=BLUE, height=0.62)
    a2.barh(d.category_name, d.view_to_purchase_pct, color=BLUE, height=0.62)
    for a, col, fmt in [(a1, "orders", "{:,.0f}"), (a2, "view_to_purchase_pct", "{:.1f}%")]:
        for yi, v in enumerate(d[col]):
            a.text(v, yi, "  " + fmt.format(v), va="center", fontsize=8.6, color=INK)
        a.set_xlim(0, d[col].max() * 1.25)
        a.xaxis.set_visible(False)
        a.spines["bottom"].set_visible(False)
        a.tick_params(axis="y", length=0)
    a1.set_title("Orders", fontsize=11)
    a2.set_title("Viewers who bought in the category", fontsize=11)
    fig.suptitle("Health & Beauty and Groceries lead purchase activity and conversion", x=0.01, ha="left",
                 fontsize=12.5, fontweight="semibold", y=1.03)
    note(fig, "Source: Q16_category_performance (SQL). Revenue is not shown: Computing and Phones & Tablets revenue is inflated "
              "by implausible list prices (DQ18).")
    save(fig, "05_category_performance.png")


def checkout_abandonment():
    d = pd.read_csv(RES / "Q12_checkout_abandonment.csv")
    allrow = d[d.platform == "ALL"].iloc[0]
    overall = 100 * allrow.abandoned_checkouts / allrow.checkout_sessions
    d = d[d.platform != "ALL"].copy()
    d["seg"] = d.platform.str.replace("_app", " app").str.replace("android", "Android").str.replace("ios", "iOS") \
                .str.replace("web", "Web") + " · " + d.device_type
    d = d.sort_values("checkout_abandonment_pct")
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    colors = [ORANGE if s == "Web · mobile" else BLUE for s in d.seg]
    ax.barh(d.seg, d.checkout_abandonment_pct, color=colors, height=0.62)
    for yi, (_, r) in enumerate(d.iterrows()):
        ax.annotate(f"{r.checkout_abandonment_pct:.1f}%  ({r.abandoned_checkouts:,} of {r.checkout_sessions:,})",
                va="center", fontsize=8.8, color=INK, bbox=LBL, zorder=4,
                    xy=(r.checkout_abandonment_pct, yi), xytext=(5, 0), textcoords="offset points")
    ax.axvline(overall, color=INK2, lw=0.9, ls="--", zorder=1)
    ax.text(overall, len(d) - 0.35, f" all sessions {overall:.1f}%", fontsize=8.5, color=INK2, va="bottom")
    ax.set_xlim(0, 52)
    ax.xaxis.set_visible(False); ax.spines["bottom"].set_visible(False); ax.tick_params(axis="y", length=0)
    ax.set_title("Checkout sessions that end without an order")
    note(fig, "Source: Q12_checkout_abandonment (SQL). A checkout session contains begin_checkout; abandoned = no order in that session.")
    save(fig, "06_checkout_abandonment_by_device.png")


def channel_retention():
    d = pd.read_csv(RES / "Q23_segment_repeat_engagement.csv")
    d = d[d.dimension == "acquisition channel"].sort_values("return_28d_pct")
    overall = pd.read_csv(RES / "Q19_returning_users.csv").pct_returned_within_28d.iloc[0]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    colors = [ORANGE if s == "paid_social" else BLUE for s in d.segment]
    ax.barh(d.segment.str.replace("_", " "), d.return_28d_pct, color=colors, height=0.62)
    for yi, (_, r) in enumerate(d.iterrows()):
        ax.annotate(f"{r.return_28d_pct:.1f}%   ({r.eligible_28d:,} users)", va="center", fontsize=8.8, color=INK, bbox=LBL, zorder=4,
                    xy=(r.return_28d_pct, yi), xytext=(5, 0), textcoords="offset points")
    ax.axvline(overall, color=INK2, lw=0.9, ls="--", zorder=1)
    ax.text(overall, len(d) - 0.35, f" all users {overall:.1f}%", fontsize=8.5, color=INK2, va="bottom")
    ax.set_xlim(0, 92)
    ax.xaxis.set_visible(False); ax.spines["bottom"].set_visible(False); ax.tick_params(axis="y", length=0)
    ax.set_title("Users returning within 28 days, by acquisition channel")
    note(fig, "Source: Q23_segment_repeat_engagement (SQL). Only users with at least 28 days of follow-up are counted. "
              "Association, not cause: channel mix also differs by registration and loyalty status.")
    save(fig, "07_retention_by_acquisition_channel.png")


def cart_abandonment():
    d = pd.read_csv(RES / "Q17b_abandonment_by_category_and_price.csv")
    d = d[d.dimension == "category"].sort_values("abandonment_pct")
    overall = pd.read_csv(RES / "Q12b_cart_abandonment_overall.csv").cart_abandonment_pct.iloc[0]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.barh(d.segment, d.abandonment_pct, color=BLUE, height=0.62)
    for yi, (_, r) in enumerate(d.iterrows()):
        ax.annotate(f"{r.abandonment_pct:.1f}%   ({r.cart_additions:,} additions)", va="center", fontsize=8.8, color=INK, bbox=LBL, zorder=4,
                    xy=(r.abandonment_pct, yi), xytext=(5, 0), textcoords="offset points")
    ax.axvline(overall, color=INK2, lw=0.9, ls="--", zorder=1)
    ax.text(overall, len(d) - 0.35, f" all {overall:.1f}%", fontsize=8.5, color=INK2, va="bottom")
    ax.set_xlim(0, 100)
    ax.xaxis.set_visible(False); ax.spines["bottom"].set_visible(False); ax.tick_params(axis="y", length=0)
    ax.set_title("Cart additions not bought within 7 days, by category")
    note(fig, "Source: Q17b (SQL) on cart_add_outcomes. Additions in the last 7 days of the window are excluded (outcome not yet observable).")
    save(fig, "08_cart_abandonment_by_category.png")


def sql_output_image():
    """Renders genuine sqlite3 shell output (box mode) of two queries as a PNG."""
    db = ROOT / "data" / "processed" / "ecommerce_analytics.db"
    q1 = ("WITH s AS (SELECT stage_no, stage, users, LAG(users) OVER (ORDER BY stage_no) AS prev FROM vw_user_funnel) "
          "SELECT stage_no, stage, users, ROUND(100.0 * users / prev, 1) AS step_conv_pct, prev - users AS users_lost "
          "FROM s ORDER BY stage_no;")
    q2 = "SELECT category, COUNT(*) AS checks, SUM(status='PASS') AS passed, SUM(status='FAIL') AS failed FROM validation_results GROUP BY category ORDER BY MIN(check_id);"
    out = []
    for title, q in [("sqlite> SELECT ... FROM vw_user_funnel;   -- closed user funnel", q1),
                     ("sqlite> SELECT ... FROM validation_results GROUP BY category;", q2)]:
        r = subprocess.run(["sqlite3", "-box", str(db), q], capture_output=True, text=True, check=True)
        out.append(title + "\n" + r.stdout)
    text = "\n".join(out)
    fig = plt.figure(figsize=(9.6, 0.19 * text.count("\n") + 0.6))
    fig.patch.set_facecolor("#0d1117")
    fig.text(0.02, 0.98, text, family="DejaVu Sans Mono", fontsize=9.2, color="#e6edf3", va="top", ha="left")
    fig.savefig(FIG / "09_sql_shell_output.png", facecolor="#0d1117")
    plt.close(fig)
    print("wrote 09_sql_shell_output.png")


if __name__ == "__main__":
    funnel(); weekly(); cohort_heatmap(); product_scatter(); categories()
    checkout_abandonment(); channel_retention(); cart_abandonment(); sql_output_image()
