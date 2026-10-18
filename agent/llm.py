"""One wrapper for every Claude call in the project.

call(prompt, context) -> {"text": str, "model": str, "cached": bool}

- Claude Opus 5.5 with server-side refusal fallback (pharma questions can trip
  the bio safety classifier; "default" fallback reroutes instead of failing).
- File cache keyed on (prompt, context, system) so demo inputs never wait on the API.
"""

import hashlib
import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-opus-5-5"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

DEFAULT_SYSTEM = (
    "You are an analyst helping a pharmaceutical business team make a decision. "
    "Use only the provided context documents. Cite every factual claim with the "
    "source name in square brackets, like [source: trial_data.csv row 12]. "
    "If the context does not support an answer, say so plainly."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            try:
                import streamlit as st

                os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
            except Exception:
                pass
        _client = anthropic.Anthropic(max_retries=3)
    return _client


def _cache_key(prompt, context, system, effort):
    raw = json.dumps([MODEL, prompt, context, system, effort], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _format_context(context):
    """context: dict of {source_name: text}, a plain string, or None."""
    if not context:
        return ""
    if isinstance(context, str):
        return f"<document source=\"context\">\n{context}\n</document>\n\n"
    return "".join(
        f"<document source=\"{name}\">\n{text}\n</document>\n\n"
        for name, text in context.items()
    )


def call(prompt, context=None, system=DEFAULT_SYSTEM, effort="medium", use_cache=True):
    key = _cache_key(prompt, context, system, effort)
    path = CACHE_DIR / f"{key}.json"
    if use_cache and path.exists():
        out = json.loads(path.read_text())
        out["cached"] = True
        return out

    response = _get_client().beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": _format_context(context) + prompt}],
    )

    if response.stop_reason == "refusal":
        text = "The model declined this request. Rephrase it around the business decision."
    else:
        text = "".join(b.text for b in response.content if b.type == "text")
        if response.stop_reason == "max_tokens":
            text += "\n\n[truncated: hit max_tokens]"

    out = {"text": text, "model": response.model, "cached": False}
    if response.stop_reason != "refusal":
        path.write_text(json.dumps(out))
    return out


if __name__ == "__main__":
    print(call("Reply with exactly: scaffold OK", use_cache=False)["text"])
