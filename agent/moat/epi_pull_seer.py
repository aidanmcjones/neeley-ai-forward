from agent.moat.epi_fetch import fetch
for s in "lungb breast mulmy colorect melan urinb kidrp livibd stomach esoph cervix corp ovary hodg dlbcl oralcav thyro pancreas".split():
    print(s, fetch(f"seer_{s}", f"https://seer.cancer.gov/statfacts/html/{s}.html"))
