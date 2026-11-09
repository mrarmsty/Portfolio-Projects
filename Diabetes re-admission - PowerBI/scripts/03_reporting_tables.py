"""
03_reporting_tables.py
Rebuilds the threshold curve and operating-point metrics from the exported
(6-decimal) predictions in encounter_predictions.csv - the exact values Power BI
imports - so that the Python tables and the DAX confusion-matrix measures agree
to the encounter at every threshold.
"""
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "model_outputs"
pred = pd.read_csv(OUT / "encounter_predictions.csv")
y = pd.read_csv(ROOT / "data" / "processed" / "fact_encounter_clean.csv", usecols=["encounter_id", "readmit_30"])
t = pred[pred.data_split == "Test"].merge(y, on="encounter_id")

def cm(yv, flag):
    tp = int(((flag == 1) & (yv == 1)).sum()); fp = int(((flag == 1) & (yv == 0)).sum())
    fn = int(((flag == 0) & (yv == 1)).sum()); tn = int(((flag == 0) & (yv == 0)).sum())
    prec = tp / (tp + fp) if tp + fp else 0; rec = tp / (tp + fn) if tp + fn else 0
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=prec, recall=rec,
                specificity=tn / (tn + fp) if tn + fp else 0,
                f1=2 * prec * rec / (prec + rec) if prec + rec else 0,
                alert_rate=(tp + fp) / len(yv), accuracy=(tp + tn) / len(yv))

rows = []
for name, col in [("Logistic Regression", "p_lr"), ("Random Forest", "p_rf")]:
    for i in range(2, 61):
        thr = i / 100                       # identical double to DAX [Value] / 100
        rows.append({"model": name, "threshold": thr, **cm(t.readmit_30.values, (t[col].values >= thr).astype(int))})
pd.DataFrame(rows).to_csv(OUT / "model_threshold_curve.csv", index=False)

m = pd.read_csv(OUT / "model_metrics.csv")
for name, col in [("Logistic Regression", "p_lr"), ("Random Forest", "p_rf")]:
    thr = float(np.quantile(t[col], 0.80))
    r = cm(t.readmit_30.values, (t[col].values >= thr).astype(int))
    idx = m.model == name
    m.loc[idx, "op_threshold"] = thr
    for k, v in r.items():
        m.loc[idx, f"op_{k}"] = v
m.to_csv(OUT / "model_metrics.csv", index=False)
print(m[["model", "test_auc", "op_threshold", "op_tp", "op_fp", "op_precision", "op_recall"]].to_string())
