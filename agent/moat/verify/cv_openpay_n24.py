"""Run the PY2024 nature-of-payment queries for the 6 drugs in parallel with the main cv_openpay run."""
from concurrent.futures import ThreadPoolExecutor

from agent.moat.verify.cv_openpay import NAT, NATURE6, q

with ThreadPoolExecutor(3) as ex:
    list(ex.map(lambda dn: q(2024, [dn.upper()], NAT), NATURE6))
