"""Streamlit front end. Hello-world golden path: load case docs, ask, show a cited answer.

Run locally:  streamlit run app/main.py
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.llm import call  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

st.set_page_config(page_title="Neeley AI Forward", layout="wide")
st.title("Pharma decision copilot")
st.caption("Placeholder title. Replace with the one-liner from PLAN.md once the case is chosen.")

# Context: every text-like file in data/ plus anything uploaded.
context = {}
for f in sorted(DATA_DIR.glob("*")):
    if f.suffix.lower() in {".txt", ".md", ".csv", ".json"}:
        context[f.name] = f.read_text(errors="ignore")[:200_000]

uploads = st.file_uploader(
    "Add case files", type=["txt", "md", "csv", "json"], accept_multiple_files=True
)
for u in uploads or []:
    context[u.name] = u.read().decode(errors="ignore")[:200_000]

with st.sidebar:
    st.subheader("Loaded sources")
    for name in context:
        st.write(f"- {name}")
    if not context:
        st.write("None yet. Put case files in data/ or upload above.")

question = st.text_area(
    "Question", "Summarize the decision this case asks for and the three numbers that matter most."
)

if st.button("Run", type="primary"):
    with st.spinner("Thinking..."):
        result = call(question, context=context or None)
    st.markdown(result["text"])
    st.caption(f"model: {result['model']} | cached: {result['cached']}")
