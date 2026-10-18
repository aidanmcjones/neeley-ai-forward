import sys

from agent.moat.epi_fetch import fetch

P = {
    "niddk_diabetes": "https://www.niddk.nih.gov/health-information/health-statistics/diabetes-statistics",
    "niddk_obesity": "https://www.niddk.nih.gov/health-information/health-statistics/overweight-obesity",
    "niams_ra": "https://www.niams.nih.gov/health-topics/rheumatoid-arthritis",
    "pmc_psoriasis_armstrong": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8254764/",
}
for k, u in P.items():
    print(k, fetch(k, u))
