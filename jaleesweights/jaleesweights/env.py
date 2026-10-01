"""Key loading that asks only for what a step uses — the benchmark's own loader, narrowed.

One parser for the repo-root `.env` (an already-set environment variable wins; values are
taken literally, so write `KEY=value` without quotes): `jaleesbench.collect.load_env`, called
with the keys a step needs. A missing key is reported by name; no value is ever printed.
"""

from jaleesbench import collect


def load_keys(required: list[str], gemini: bool = False) -> None:
    """Fail fast naming exactly the keys in `required` that are unset after `.env` is read.
    With `gemini=True` also require a Gemini credential: the Vertex service-account file at
    the repo root or GEMINI_API_KEY."""
    collect.load_env(required=list(required), gemini=gemini)
