"""
Credit Risk Portfolio Analysis - data preparation and model estimation
======================================================================

Supporting script for the Excel credit risk monitoring workbook.

Why this script exists
----------------------
Microsoft Excel is the primary analysis and delivery tool for this project. Every
KPI, statistical test, segment table, model score and evaluation metric in the
workbook is a live Excel formula. Two steps, however, cannot be done natively in
Excel without add-ins, so they are performed here and the results are written into
the workbook as clearly labelled, frozen model parameters:

1. Applying the documented cleaning rules reproducibly to 32,581 raw records
   (an equivalent Power Query M script is provided in documentation/).
2. Estimating model parameters:
   - logistic regression coefficients by maximum likelihood (statsmodels), and
   - a depth-limited CART decision tree (scikit-learn).

The workbook then *implements* both models with formulas (coefficient lookups and
a nested IF decision tree), scores every loan, and evaluates both models on the
held-out test set. The logistic coefficients can be re-verified inside Excel with
Solver (instructions on the Model_LR sheet).

Usage (from the repository root):
    python scripts/prepare_data_and_fit_models.py

Outputs:
    data/processed/credit_risk_clean.csv        analysis-ready dataset
    data/processed/excluded_records.csv         records removed, with reasons
    outputs/model/model_parameters.json         coefficients, tree, reference metrics
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "credit_risk_dataset.csv"
OUT_DATA = ROOT / "data" / "processed"
OUT_MODEL = ROOT / "outputs" / "model"
SEED = 42

RAW_COLS = [
    "person_age", "person_income", "person_home_ownership", "person_emp_length",
    "loan_intent", "loan_grade", "loan_amnt", "loan_int_rate", "loan_status",
    "loan_percent_income", "cb_person_default_on_file", "cb_person_cred_hist_length",
]

# ---------------------------------------------------------------------------
# Band definitions (lower bound inclusive). These are identical to the band
# tables on the workbook's Lists sheet.
# ---------------------------------------------------------------------------
BANDS = {
    "age_band": ("person_age", [0, 25, 30, 35, 45],
                 ["20–24", "25–29", "30–34", "35–44", "45+"]),
    "income_band": ("person_income", [0, 25000, 40000, 60000, 80000, 120000],
                    ["Under 25k", "25k–40k", "40k–60k", "60k–80k", "80k–120k", "120k+"]),
    "lti_band": ("lti", [0, 0.10, 0.20, 0.30, 0.40],
                 ["0–10%", "10–20%", "20–30%", "30–40%", "40%+"]),
    "emp_band": ("person_emp_length", [0, 1, 3, 6, 11],
                 ["Under 1 yr", "1–2 yrs", "3–5 yrs", "6–10 yrs", "Over 10 yrs"]),
    "rate_band": ("loan_int_rate", [0, 8, 10, 12, 14, 16, 18],
                  ["Under 8%", "8–10%", "10–12%", "12–14%", "14–16%", "16–18%", "18%+"]),
    "amount_band": ("loan_amnt", [0, 5000, 10000, 15000, 20000],
                    ["Under 5k", "5k–10k", "10k–15k", "15k–20k", "20k+"]),
    "hist_band": ("cb_person_cred_hist_length", [0, 5, 8, 11, 18],
                  ["2–4 yrs", "5–7 yrs", "8–10 yrs", "11–17 yrs", "18+ yrs"]),
}
MISSING_LABEL = {"emp_band": "Unknown", "rate_band": "Not recorded"}


def band(series: pd.Series, lowers: list, labels: list, missing: str | None) -> pd.Series:
    """Lower-bound-inclusive banding, same logic as Excel INDEX/MATCH(...,1)."""
    idx = np.searchsorted(np.array(lowers, dtype=float), series.to_numpy(dtype=float), side="right") - 1
    out = pd.Series(np.array(labels, dtype=object)[np.clip(idx, 0, len(labels) - 1)], index=series.index)
    if missing is not None:
        out[series.isna()] = missing
    return out


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df = raw.copy()
    df.insert(0, "loan_id", [f"LN{i:05d}" for i in range(1, len(df) + 1)])  # raw file order
    log = {"raw_records": len(df)}

    # 1. Exact duplicates across all 12 source fields: keep first occurrence.
    dup = df.duplicated(RAW_COLS, keep="first")
    # 2. Impossible ages (> 100). These records also carry other implausible values.
    bad_age = (df["person_age"] > 100) & ~dup
    excluded = pd.concat([
        df[dup].assign(exclusion_reason="Exact duplicate of an earlier record (all 12 fields identical)"),
        df[bad_age].assign(exclusion_reason="Invalid age (> 100 years)"),
    ]).sort_values("loan_id")
    log["duplicates_removed"] = int(dup.sum())
    log["invalid_age_removed"] = int(bad_age.sum())
    df = df[~dup & ~bad_age].copy()

    flags = pd.Series([[] for _ in range(len(df))], index=df.index)

    # 3. Employment length longer than possible working life -> treat as unknown.
    bad_emp = df["person_emp_length"] > (df["person_age"] - 14)
    log["emp_length_invalid_set_missing"] = int(bad_emp.sum())
    for i in df.index[bad_emp]:
        flags[i].append("EMP_INVALID")
    df.loc[bad_emp, "person_emp_length"] = np.nan

    # 4. Placeholder interest rate of exactly 6.00% in grades B-E (below grade pricing floor).
    bad_rate = (df["loan_int_rate"] == 6.0) & df["loan_grade"].isin(list("BCDE"))
    log["rate_placeholder_set_missing"] = int(bad_rate.sum())
    for i in df.index[bad_rate]:
        flags[i].append("RATE_PLACEHOLDER")
    df.loc[bad_rate, "loan_int_rate"] = np.nan

    # 5. Missing value flags (retained, not imputed in the analysis dataset).
    for i in df.index[df["person_emp_length"].isna() & ~bad_emp]:
        flags[i].append("EMP_MISSING")
    for i in df.index[df["loan_int_rate"].isna() & ~bad_rate]:
        flags[i].append("RATE_MISSING")
    log["emp_length_missing_after_cleaning"] = int(df["person_emp_length"].isna().sum())
    log["int_rate_missing_after_cleaning"] = int(df["loan_int_rate"].isna().sum())

    # 6. Loan-to-income recomputed from its components; supplied field kept for audit.
    df["lti"] = df["loan_amnt"] / df["person_income"]
    mismatch = (df["lti"] - df["loan_percent_income"]).abs() > 0.0051  # beyond 2-dp rounding
    log["lti_mismatch_flagged"] = int(mismatch.sum())
    log["lti_mismatch_default_share"] = float(df.loc[mismatch, "loan_status"].mean())
    for i in df.index[mismatch]:
        flags[i].append("LTI_MISMATCH")

    df["dq_flags"] = flags.apply(lambda f: "; ".join(f))

    # 7. Stratified 70/30 train/test split for model development.
    train_idx, _ = train_test_split(df.index, test_size=0.30, stratify=df["loan_status"], random_state=SEED)
    df["data_split"] = np.where(df.index.isin(train_idx), "Train", "Test")

    # 8. Analysis bands (also computed by formula in the workbook).
    for name, (col, lowers, labels) in BANDS.items():
        df[name] = band(df[col], lowers, labels, MISSING_LABEL.get(name))

    log["clean_records"] = len(df)
    return df, excluded, log


# ---------------------------------------------------------------------------
# Modelling
# ---------------------------------------------------------------------------
GRADES = list("ABCDEFG")
HOME_LEVELS = ["MORTGAGE", "OTHER", "OWN", "RENT"]           # MORTGAGE = reference
INTENT_LEVELS = ["EDUCATION", "DEBTCONSOLIDATION", "HOMEIMPROVEMENT", "MEDICAL", "PERSONAL", "VENTURE"]  # EDUCATION = reference


def lr_design(d: pd.DataFrame, extra: bool = False) -> pd.DataFrame:
    X = pd.DataFrame(index=d.index)
    for g in GRADES[1:]:
        X[f"loan_grade={g}"] = (d["loan_grade"] == g).astype(float)
    for h in HOME_LEVELS[1:]:
        X[f"person_home_ownership={h}"] = (d["person_home_ownership"] == h).astype(float)
    for i in INTENT_LEVELS[1:]:
        X[f"loan_intent={i}"] = (d["loan_intent"] == i).astype(float)
    X["lti"] = d["lti"]
    X["lti_squared"] = d["lti"] ** 2
    X["ln_income"] = np.log(d["person_income"])
    X["emp_unknown"] = d["person_emp_length"].isna().astype(float)
    if extra:  # candidate variables tested and dropped (likelihood-ratio test)
        X["emp_length_imputed"] = d["person_emp_length"].fillna(d["_emp_median"])
        X["prior_default"] = (d["cb_person_default_on_file"] == "Y").astype(float)
        X["person_age"] = d["person_age"]
        X["cred_hist_length"] = d["cb_person_cred_hist_length"]
        X["int_rate_imputed"] = d["_rate_model"]
    return sm.add_constant(X, has_constant="add")


TREE_FEATURES = ["lti", "grade_num", "person_income", "emp_length_model", "int_rate_model",
                 "person_age", "cb_person_cred_hist_length", "loan_amnt", "prior_default", "emp_unknown"] + \
                [f"home_{h}" for h in HOME_LEVELS] + [f"intent_{i}" for i in INTENT_LEVELS]


def tree_design(d: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame(index=d.index)
    X["lti"] = d["lti"]
    X["grade_num"] = d["loan_grade"].map({g: i + 1 for i, g in enumerate(GRADES)})
    X["person_income"] = d["person_income"]
    X["emp_length_model"] = d["_emp_model"]
    X["int_rate_model"] = d["_rate_model"]
    X["person_age"] = d["person_age"]
    X["cb_person_cred_hist_length"] = d["cb_person_cred_hist_length"]
    X["loan_amnt"] = d["loan_amnt"]
    X["prior_default"] = (d["cb_person_default_on_file"] == "Y").astype(int)
    X["emp_unknown"] = d["person_emp_length"].isna().astype(int)
    for h in HOME_LEVELS:
        X[f"home_{h}"] = (d["person_home_ownership"] == h).astype(int)
    for i in INTENT_LEVELS:
        X[f"intent_{i}"] = (d["loan_intent"] == i).astype(int)
    return X[TREE_FEATURES]


def export_tree(model: DecisionTreeClassifier, feature_names: list[str]) -> list[dict]:
    t = model.tree_
    nodes = []
    for n in range(t.node_count):
        is_leaf = t.children_left[n] == -1
        counts = t.value[n][0] * t.weighted_n_node_samples[n] if t.value[n][0].sum() <= 1.0001 else t.value[n][0]
        nodes.append({
            "node": n,
            "leaf": bool(is_leaf),
            "feature": None if is_leaf else feature_names[t.feature[n]],
            "threshold": None if is_leaf else float(t.threshold[n]),
            "left": None if is_leaf else int(t.children_left[n]),
            "right": None if is_leaf else int(t.children_right[n]),
            "n": int(t.n_node_samples[n]),
            "defaults": int(round(float(counts[1]))),
        })
    return nodes


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_MODEL.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(RAW)
    assert list(raw.columns) == RAW_COLS, "Unexpected raw schema"
    df, excluded, log = clean(raw)

    # ---- frozen imputation parameters (training data only) ----
    tr_mask = df["data_split"] == "Train"
    emp_median = float(df.loc[tr_mask, "person_emp_length"].median())
    rate_median = df[tr_mask].groupby("loan_grade")["loan_int_rate"].median().reindex(GRADES)
    df["_emp_median"] = emp_median
    df["_emp_model"] = df["person_emp_length"].fillna(emp_median)
    df["_rate_model"] = df["loan_int_rate"].fillna(df["loan_grade"].map(rate_median))
    tr, te = df[tr_mask], df[~tr_mask]

    # ---- logistic regression ----
    full = sm.Logit(tr["loan_status"], lr_design(tr, extra=True)).fit(disp=0)
    final = sm.Logit(tr["loan_status"], lr_design(tr)).fit(disp=0)
    lr_stat = 2 * (full.llf - final.llf)
    from scipy import stats
    lr_drop_p = float(stats.chi2.sf(lr_stat, full.df_model - final.df_model))
    lr_test_pd = final.predict(lr_design(te))
    lr_train_pd = final.predict(lr_design(tr))

    # linear-LTI alternative (to document the value of the squared term)
    lin = sm.Logit(tr["loan_status"], lr_design(tr).drop(columns="lti_squared")).fit(disp=0)
    lin_auc = roc_auc_score(te["loan_status"], lin.predict(lr_design(te).drop(columns="lti_squared")))

    # ---- decision tree (depth capped at 6 for transparency / Excel implementation) ----
    Xtr, Xte = tree_design(tr), tree_design(te)
    grid = GridSearchCV(
        DecisionTreeClassifier(random_state=SEED),
        {"max_depth": [3, 4, 5, 6], "min_samples_leaf": [50, 100, 200, 400]},
        cv=StratifiedKFold(5, shuffle=True, random_state=SEED), scoring="roc_auc",
    ).fit(Xtr, tr["loan_status"])
    tree = grid.best_estimator_
    leaf_tr = tree.apply(Xtr)
    leaf_te = tree.apply(Xte)
    nodes = export_tree(tree, TREE_FEATURES)
    leaf_stats = pd.DataFrame({"leaf": leaf_tr, "y": tr["loan_status"].to_numpy()}).groupby("leaf")["y"].agg(["size", "sum"])
    smoothed = (leaf_stats["sum"] + 1) / (leaf_stats["size"] + 2)  # Laplace-corrected leaf PD
    tree_test_pd = pd.Series(leaf_te).map(smoothed).to_numpy()
    tree_train_pd = pd.Series(leaf_tr).map(smoothed).to_numpy()

    # ---- benchmark only (not implementable natively in Excel) ----
    hgb = HistGradientBoostingClassifier(random_state=SEED).fit(Xtr, tr["loan_status"])
    hgb_auc = roc_auc_score(te["loan_status"], hgb.predict_proba(Xte)[:, 1])

    params = {
        "seed": SEED,
        "cleaning_log": log,
        "split": {"train_n": int(tr_mask.sum()), "test_n": int((~tr_mask).sum()),
                  "train_default_rate": float(tr["loan_status"].mean()),
                  "test_default_rate": float(te["loan_status"].mean())},
        "imputation": {"emp_length_train_median": emp_median,
                       "int_rate_train_median_by_grade": {g: float(v) for g, v in rate_median.items()}},
        "logistic_regression": {
            "reference_levels": {"loan_grade": "A", "person_home_ownership": "MORTGAGE", "loan_intent": "EDUCATION"},
            "terms": [
                {"term": k, "coef": float(final.params[k]), "se": float(final.bse[k]),
                 "z": float(final.tvalues[k]), "p": float(final.pvalues[k])}
                for k in final.params.index
            ],
            "llf": float(final.llf), "llnull": float(final.llnull), "aic": float(final.aic),
            "mcfadden_r2": float(final.prsquared), "n_train": int(final.nobs),
            "dropped_candidates": ["emp_length_imputed", "prior_default", "person_age",
                                   "cred_hist_length", "int_rate_imputed"],
            "dropped_lr_test": {"chi2": float(lr_stat), "df": int(full.df_model - final.df_model), "p": lr_drop_p},
            "full_model_terms": {k: {"coef": float(full.params[k]), "p": float(full.pvalues[k])} for k in full.params.index},
            "test_auc": float(roc_auc_score(te["loan_status"], lr_test_pd)),
            "train_auc": float(roc_auc_score(tr["loan_status"], lr_train_pd)),
            "test_auc_linear_lti_only": float(lin_auc),
        },
        "decision_tree": {
            "features": TREE_FEATURES,
            "best_params": grid.best_params_,
            "cv_auc": float(grid.best_score_),
            "cv_results": [
                {"max_depth": int(p["max_depth"]), "min_samples_leaf": int(p["min_samples_leaf"]), "cv_auc": float(s)}
                for p, s in zip(grid.cv_results_["params"], grid.cv_results_["mean_test_score"])
            ],
            "nodes": nodes,
            "n_leaves": int(tree.get_n_leaves()),
            "feature_importance": {f: float(v) for f, v in zip(TREE_FEATURES, tree.feature_importances_)},
            "test_auc": float(roc_auc_score(te["loan_status"], tree_test_pd)),
            "train_auc": float(roc_auc_score(tr["loan_status"], tree_train_pd)),
        },
        "benchmark_gradient_boosting_test_auc": float(hgb_auc),
    }
    (OUT_MODEL / "model_parameters.json").write_text(json.dumps(params, indent=2))

    # ---- analysis-ready dataset ----
    out_cols = ["loan_id"] + RAW_COLS + ["data_split", "dq_flags", "lti"] + list(BANDS)
    df[out_cols].to_csv(OUT_DATA / "credit_risk_clean.csv", index=False)
    excluded[["loan_id"] + RAW_COLS + ["exclusion_reason"]].to_csv(OUT_DATA / "excluded_records.csv", index=False)

    # reference scores for workbook QA (not a deliverable)
    ref = pd.DataFrame({"loan_id": df["loan_id"]})
    ref["lr_pd"] = final.predict(lr_design(df))
    Xall = tree_design(df)
    ref["tree_node"] = tree.apply(Xall)
    ref["tree_pd"] = pd.Series(ref["tree_node"].to_numpy()).map(smoothed).to_numpy()
    ref.to_csv(OUT_MODEL / "_reference_scores.csv", index=False)

    print(json.dumps(log, indent=2))
    print("LR test AUC", params["logistic_regression"]["test_auc"],
          "| Tree test AUC", params["decision_tree"]["test_auc"],
          "| HGB benchmark", hgb_auc)


if __name__ == "__main__":
    main()
