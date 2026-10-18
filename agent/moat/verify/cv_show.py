"""Scratch: print rows of a moat table. usage: cv_show TABLE [cols...]"""
import sys
import pandas as pd
d = pd.read_csv(f"data/moat/tables/{sys.argv[1]}.csv")
cols = sys.argv[2:] or list(d.columns)
for i, r in d.iterrows():
    print(i, " | ".join(f"{c}={str(r[c])[:700]}" for c in cols), "\n")
