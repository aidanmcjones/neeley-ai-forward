import re
import sys

from agent.moat.epi_fetch import fetch

P = {
    "pmc_af_prevalence_2019_2023": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11686049/",
    "pmc_ibd_medicare_mmwr": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8118152/",
}
for k, u in P.items():
    print(k, fetch(k, u))
