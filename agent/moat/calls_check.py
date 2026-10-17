import pandas as pd
d = pd.read_csv("tables/qa_turns.csv")
print(d.groupby("role").size())
a = d[d.role == "analyst"]
print("analyst firm blank", a.firm.isna().mean())
print(a[a.firm.isna()].groupby(["ticker", "quarter"]).size().sort_values(ascending=False).head(8))
print(d.text.str.len().describe())
print(d.sample(6, random_state=1)[["ticker", "quarter", "speaker", "role", "firm", "page"]])
