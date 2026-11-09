"""
02_readmission_model.py
---------------------------------------------------------------------------
Supporting analysis for Objectives 2, 4 and 5.

Power BI is the reporting tool for this project, but it is not a sound place
to train and validate classification models. Python (scikit-learn,
statsmodels, SciPy) is therefore used for:
  * statistical association tests (chi-square, Cramer's V, Mann-Whitney U)
  * logistic regression (interpretable odds ratios + classifier)
  * random forest classifier
  * patient-grouped train/test split, cross-validation, threshold analysis
The outputs are written as CSV files that Power BI imports, so every model
number shown in the report comes from this script.

Population : encounters where the patient could be readmitted
             (excludes discharge to hospice or death, n = 2,423)
Target     : readmitted within 30 days (readmitted == "<30")
Leakage    : the split is grouped by patient_nbr so the same patient never
             appears in both train and test.
Run        : python scripts/02_readmission_model.py  (after script 01)
---------------------------------------------------------------------------
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_score
from sklearn.metrics import (roc_auc_score, average_precision_score, roc_curve,
                             brier_score_loss, confusion_matrix)
from sklearn.inspection import permutation_importance
import statsmodels.api as sm

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "model_outputs"
df = pd.read_pickle(OUT / "_analysis_frame.pkl")
age_sort = {a: i for i, a in enumerate(["0-10", "10-20", "20-30", "30-40", "40-50",
                                        "50-60", "60-70", "70-80", "80-90", "90-100"], 1)}
df["age_ordinal"] = df["age_band"].map(age_sort)
pop = df[df["eligible_for_readmission"] == 1].copy()
y = pop["readmit_30"].values
groups = pop["patient_nbr"].values
print("modelling population", len(pop), "positive rate", round(y.mean(), 4))

# ======================================================== 1. association tests
cat_vars = {"age_band": "Age band", "gender": "Gender", "race": "Race",
            "admission_type_group": "Admission type", "discharge_group": "Discharge disposition",
            "admission_source_group": "Admission source", "diag_1_group": "Primary diagnosis group",
            "specialty_group": "Admitting specialty", "A1Cresult": "HbA1c result",
            "max_glu_serum": "Max glucose serum", "insulin": "Insulin status",
            "change": "Diabetes medication changed", "diabetesMed": "On diabetes medication",
            "prior_inpatient_band": "Prior inpatient visits (band)",
            "prior_emergency_band": "Prior emergency visits (band)",
            "prior_outpatient_band": "Prior outpatient visits (band)",
            "los_band": "Length of stay (band)", "medications_band": "Medications (band)"}
num_vars = {"number_inpatient": "Prior inpatient visits", "number_emergency": "Prior emergency visits",
            "number_outpatient": "Prior outpatient visits", "time_in_hospital": "Length of stay (days)",
            "num_medications": "Number of medications", "num_lab_procedures": "Number of lab procedures",
            "num_procedures": "Number of procedures", "number_diagnoses": "Number of diagnoses",
            "diabetes_meds_count": "Diabetes medications count"}
rows = []
for v, label in cat_vars.items():
    ct = pd.crosstab(pop[v], pop["readmit_30"])
    chi2, p, dof, exp = stats.chi2_contingency(ct)
    n = ct.values.sum()
    cv = np.sqrt(chi2 / (n * (min(ct.shape) - 1)))
    rates = ct[1] / ct.sum(axis=1)
    rows.append({"variable": label, "variable_type": "Categorical", "test": "Chi-square",
                 "statistic": round(chi2, 2), "df": dof, "p_value": p,
                 "effect_size": round(cv, 4), "effect_measure": "Cramer's V",
                 "min_expected_count": round(exp.min(), 1),
                 "highest_rate_group": rates.idxmax(), "highest_rate_pct": round(rates.max() * 100, 2),
                 "lowest_rate_group": rates.idxmin(), "lowest_rate_pct": round(rates.min() * 100, 2)})
for v, label in num_vars.items():
    a, b = pop.loc[pop.readmit_30 == 1, v], pop.loc[pop.readmit_30 == 0, v]
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    rbc = 1 - 2 * u / (len(a) * len(b))          # rank-biserial correlation
    rows.append({"variable": label, "variable_type": "Numeric", "test": "Mann-Whitney U",
                 "statistic": round(u, 0), "df": None, "p_value": p,
                 "effect_size": round(-rbc, 4), "effect_measure": "Rank-biserial r",
                 "min_expected_count": None,
                 "highest_rate_group": f"Mean readmitted = {a.mean():.2f}",
                 "highest_rate_pct": round(a.mean(), 3),
                 "lowest_rate_group": f"Mean not readmitted = {b.mean():.2f}",
                 "lowest_rate_pct": round(b.mean(), 3)})
assoc = pd.DataFrame(rows).sort_values("effect_size", ascending=False)
assoc["significant_at_0_05"] = np.where(assoc["p_value"] < 0.05, "Yes", "No")
assoc["p_value_display"] = assoc["p_value"].apply(lambda p: "<0.001" if p < 0.001 else f"{p:.3f}")
assoc.to_csv(OUT / "association_tests.csv", index=False)
print(assoc[["variable", "effect_size", "p_value_display"]].to_string())

# ======================================================== 2. features + split
cat_features = ["gender", "race", "admission_type_group", "discharge_group",
                "admission_source_group", "specialty_group", "diag_1_group",
                "diag_2_group", "diag_3_group", "A1Cresult", "max_glu_serum",
                "insulin", "change", "diabetesMed"]
num_features = ["age_ordinal", "time_in_hospital", "num_lab_procedures", "num_procedures",
                "num_medications", "number_outpatient", "number_emergency",
                "number_inpatient", "number_diagnoses", "diabetes_meds_count",
                "med_dose_changes", "on_metformin"]
X = pop[cat_features + num_features]

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
tr_idx, te_idx = next(gss.split(X, y, groups))
X_tr, X_te, y_tr, y_te = X.iloc[tr_idx], X.iloc[te_idx], y[tr_idx], y[te_idx]
assert not set(groups[tr_idx]) & set(groups[te_idx]), "patient leakage"
print("train", len(tr_idx), "test", len(te_idx), "test pos rate", round(y_te.mean(), 4))

pre_lr = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), cat_features),
    ("num", StandardScaler(), num_features)])
pre_rf = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
    ("num", "passthrough", num_features)])
models = {
    "Logistic Regression": Pipeline([("pre", pre_lr),
                                     ("clf", LogisticRegression(max_iter=2000, C=1.0))]),
    "Random Forest": Pipeline([("pre", pre_rf),
                               ("clf", RandomForestClassifier(n_estimators=400, min_samples_leaf=25,
                                                              max_features="sqrt", n_jobs=-1,
                                                              random_state=SEED))]),
}

# ======================================================== 3. CV + fit
cv = GroupKFold(n_splits=5)
results, preds = {}, {}
for name, m in models.items():
    cv_auc = cross_val_score(m, X_tr, y_tr, groups=groups[tr_idx], cv=cv,
                             scoring="roc_auc", n_jobs=1)
    m.fit(X_tr, y_tr)
    p = m.predict_proba(X_te)[:, 1]
    preds[name] = p
    results[name] = {"cv_auc_mean": cv_auc.mean(), "cv_auc_sd": cv_auc.std(),
                     "test_auc": roc_auc_score(y_te, p),
                     "test_pr_auc": average_precision_score(y_te, p),
                     "brier": brier_score_loss(y_te, p)}
    print(name, {k: round(v, 4) for k, v in results[name].items()})

# Baseline: a simple clinical rule (any prior inpatient visit)
rule = (X_te["number_inpatient"] >= 1).astype(int).values
results["Baseline rule (prior inpatient >= 1)"] = {
    "cv_auc_mean": np.nan, "cv_auc_sd": np.nan,
    "test_auc": roc_auc_score(y_te, X_te["number_inpatient"].values),
    "test_pr_auc": average_precision_score(y_te, X_te["number_inpatient"].values),
    "brier": np.nan}


def cm_metrics(y_true, flag):
    tn, fp, fn, tp = confusion_matrix(y_true, flag, labels=[0, 1]).ravel()
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    spec = tn / (tn + fp) if tn + fp else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=prec, recall=rec,
                specificity=spec, f1=f1, alert_rate=(tp + fp) / len(y_true),
                accuracy=(tp + tn) / len(y_true))


# Operating point: flag the top 20% highest-risk encounters (capacity-based)
OP_SHARE = 0.20
metric_rows = []
for name in models:
    thr = float(np.quantile(preds[name], 1 - OP_SHARE))
    m = cm_metrics(y_te, (preds[name] >= thr).astype(int))
    m05 = cm_metrics(y_te, (preds[name] >= 0.5).astype(int))
    results[name].update({"op_threshold": thr, **{f"op_{k}": v for k, v in m.items()},
                          "recall_at_0_5": m05["recall"], "alerts_at_0_5": m05["tp"] + m05["fp"]})
m_rule = cm_metrics(y_te, rule)
results["Baseline rule (prior inpatient >= 1)"].update(
    {"op_threshold": 1, **{f"op_{k}": v for k, v in m_rule.items()},
     "recall_at_0_5": np.nan, "alerts_at_0_5": np.nan})

for name, r in results.items():
    for k, v in r.items():
        metric_rows.append({"model": name, "metric": k, "value": None if pd.isna(v) else float(v)})
pd.DataFrame(metric_rows).to_csv(OUT / "model_metrics_long.csv", index=False)
wide = pd.DataFrame(results).T.reset_index().rename(columns={"index": "model"})
wide["model_order"] = range(1, len(wide) + 1)
wide.to_csv(OUT / "model_metrics.csv", index=False)

# ======================================================== 4. threshold curve + ROC
thr_rows = []
for name in models:
    for t in np.round(np.arange(0.02, 0.61, 0.01), 2):
        m = cm_metrics(y_te, (preds[name] >= t).astype(int))
        thr_rows.append({"model": name, "threshold": t, **m})
pd.DataFrame(thr_rows).to_csv(OUT / "model_threshold_curve.csv", index=False)

roc_rows = []
for name in models:
    fpr, tpr, _ = roc_curve(y_te, preds[name])
    grid = np.linspace(0, 1, 101)
    roc_rows += [{"model": name, "fpr": g, "tpr": float(np.interp(g, fpr, tpr))} for g in grid]
roc_rows += [{"model": "Random guess", "fpr": g, "tpr": g} for g in np.linspace(0, 1, 101)]
pd.DataFrame(roc_rows).to_csv(OUT / "model_roc_curve.csv", index=False)

# ======================================================== 5. feature importance
label_map = {**{v: l for v, l in cat_vars.items()},
             "admission_type_group": "Admission type", "discharge_group": "Discharge disposition",
             "admission_source_group": "Admission source", "specialty_group": "Admitting specialty",
             "diag_1_group": "Primary diagnosis group", "diag_2_group": "Secondary diagnosis group",
             "diag_3_group": "Additional diagnosis group", "age_ordinal": "Age band",
             "time_in_hospital": "Length of stay", "num_lab_procedures": "Number of lab procedures",
             "num_procedures": "Number of procedures", "num_medications": "Number of medications",
             "number_outpatient": "Prior outpatient visits", "number_emergency": "Prior emergency visits",
             "number_inpatient": "Prior inpatient visits", "number_diagnoses": "Number of diagnoses",
             "diabetes_meds_count": "Diabetes medications count",
             "med_dose_changes": "Diabetes medication dose changes", "on_metformin": "On metformin",
             "change": "Diabetes medication changed", "diabetesMed": "On diabetes medication",
             "insulin": "Insulin status", "A1Cresult": "HbA1c result", "max_glu_serum": "Max glucose serum",
             "gender": "Gender", "race": "Race"}
imp_rows = []
for name, m in models.items():
    pi = permutation_importance(m, X_te, y_te, scoring="roc_auc", n_repeats=5,
                                random_state=SEED, n_jobs=-1)
    for f, mean, sd in zip(X_te.columns, pi.importances_mean, pi.importances_std):
        imp_rows.append({"model": name, "feature": label_map.get(f, f), "feature_code": f,
                         "auc_drop_mean": mean, "auc_drop_sd": sd})
imp = pd.DataFrame(imp_rows)
imp["rank"] = imp.groupby("model")["auc_drop_mean"].rank(ascending=False, method="first").astype(int)
imp.to_csv(OUT / "feature_importance.csv", index=False)
print(imp[imp["rank"] <= 8].sort_values(["model", "rank"]).to_string())

# ======================================================== 6. logistic odds ratios (statsmodels)
Xs = pd.get_dummies(X_tr, columns=cat_features, drop_first=False, dtype=float)
ref = {"gender": "Female", "race": "Caucasian", "admission_type_group": "Emergency",
       "discharge_group": "Home", "admission_source_group": "Emergency room",
       "specialty_group": "Internal Medicine", "diag_1_group": "Circulatory",
       "diag_2_group": "Circulatory", "diag_3_group": "Circulatory",
       "A1Cresult": "Not measured", "max_glu_serum": "Not measured",
       "insulin": "No", "change": "No", "diabetesMed": "No"}
Xs = Xs.drop(columns=[f"{c}_{v}" for c, v in ref.items()])
# drop very sparse dummies (< 30 cases) to keep estimates stable
sparse = [c for c in Xs.columns if Xs[c].nunique() == 2 and Xs[c].sum() < 30]
Xs = Xs.drop(columns=sparse)
logit = sm.Logit(y_tr, sm.add_constant(Xs)).fit(disp=0, maxiter=200)
ci = logit.conf_int()
orr = pd.DataFrame({"term": logit.params.index, "coef": logit.params.values,
                    "odds_ratio": np.exp(logit.params.values),
                    "or_ci_low": np.exp(ci[0].values), "or_ci_high": np.exp(ci[1].values),
                    "p_value": logit.pvalues.values})
orr = orr[orr.term != "const"]
def nice(t):
    for c in cat_features:
        if t.startswith(c + "_"):
            return f"{label_map.get(c, c)}: {t[len(c) + 1:]} (vs {ref[c]})"
    unit = {"age_ordinal": "per 10-year band"}.get(t, "per unit")
    return f"{label_map.get(t, t)} ({unit})"
orr["term_label"] = orr["term"].apply(nice)
orr["significant_at_0_05"] = np.where(orr["p_value"] < 0.05, "Yes", "No")
orr["direction"] = np.where(orr["odds_ratio"] >= 1, "Higher risk", "Lower risk")
orr.sort_values("odds_ratio", ascending=False).to_csv(OUT / "lr_odds_ratios.csv", index=False)
print("pseudo R2", round(logit.prsquared, 4), "dropped sparse", sparse)

# ======================================================== 7. encounter predictions
pred = pd.DataFrame({"encounter_id": pop["encounter_id"].values,
                     "data_split": "Train"})
pred.loc[te_idx, "data_split"] = "Test"
best = "Random Forest" if results["Random Forest"]["test_auc"] >= results["Logistic Regression"]["test_auc"] \
    else "Logistic Regression"
for name, m in models.items():
    col = "p_lr" if name.startswith("Logistic") else "p_rf"
    pred[col] = m.predict_proba(X)[:, 1]
# Risk deciles defined on the test set distribution of the selected model
best_col = "p_rf" if best == "Random Forest" else "p_lr"
edges = np.quantile(pred.loc[te_idx, best_col], np.linspace(0, 1, 11))
edges[0], edges[-1] = -np.inf, np.inf
pred["risk_decile"] = pd.cut(pred[best_col], edges, labels=range(1, 11)).astype(int)
pred["risk_tier"] = pd.cut(pred["risk_decile"], [0, 5, 8, 10],
                           labels=["Low (deciles 1-5)", "Medium (deciles 6-8)", "High (deciles 9-10)"]).astype(str)
pred["predicted_risk_best"] = pred[best_col]
pred.round(6).to_csv(OUT / "encounter_predictions.csv", index=False)

summary = {"population": int(len(pop)), "positives": int(y.sum()), "train": int(len(tr_idx)),
           "test": int(len(te_idx)), "selected_model": best, "operating_share": OP_SHARE,
           "results": {k: {kk: (None if pd.isna(vv) else float(vv)) for kk, vv in v.items()}
                       for k, v in results.items()},
           "logit_pseudo_r2": float(logit.prsquared)}
(OUT / "model_summary.json").write_text(json.dumps(summary, indent=2))
te = pred[pred.data_split == "Test"].merge(pop[["encounter_id", "readmit_30"]], on="encounter_id")
print(te.groupby("risk_decile")["readmit_30"].agg(["size", "mean"]))
print("selected", best)
