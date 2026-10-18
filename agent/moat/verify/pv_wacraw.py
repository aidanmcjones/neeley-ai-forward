import sys
import pandas as pd

f = sys.argv[1]
x = pd.read_excel(f, sheet_name=None, header=None)
for k, v in x.items():
    print(k, v.shape)
    hdr = v.index[v.astype(str).apply(lambda r: r.str.contains("NDC", case=False).any(), axis=1)][0]
    print(v.iloc[hdr].tolist())
    rows = v[v.astype(str).apply(lambda r: r.str.contains(sys.argv[2], case=False).any(), axis=1)]
    print(rows.head(6).to_string())
