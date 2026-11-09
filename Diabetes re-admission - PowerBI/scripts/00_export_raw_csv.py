"""
00_export_raw_csv.py
Exports the two sheets of the supplied workbook to CSV without changing any value
(all cells read as text, '?', 'None' and 'NULL' preserved). Power Query reads these
CSVs because parsing the 22 MB .xlsx repeatedly made a refresh take far too long.
The .xlsx remains in data/raw as the untouched original.
"""
from pathlib import Path
import pandas as pd
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
x = RAW / "diabetic_data.xlsx"
d = pd.read_excel(x, sheet_name="diabetic_data", dtype=str, keep_default_na=False, na_values=[])
d.to_csv(RAW / "diabetic_data.csv", index=False)
m = pd.read_excel(x, sheet_name="IDS_mapping", dtype=str, keep_default_na=False, na_values=[], header=None)
m.to_csv(RAW / "IDS_mapping.csv", index=False, header=False)
print(d.shape, m.shape)
