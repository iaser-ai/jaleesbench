"""Key loading that asks only for what a step uses.

Keys come from the environment, or from the clone's own `.env` at the
repository root (an already-set environment variable wins). A missing key is
reported by name; no value is ever printed.
"""

import os

from .paths import REPO_ROOT

ENV_PATH = REPO_ROOT / ".env"
VERTEX_SA = REPO_ROOT / ".vertex-sa.json"


def load_keys(required: list[str], gemini: bool = False) -> None:
    """Load `.env`, then fail fast naming exactly the keys in `required` that
    are still unset. With `gemini=True` also require a Gemini credential: the
    Vertex service-account file at the repo root or GEMINI_API_KEY."""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            f"missing keys (set them in the environment or in {ENV_PATH}): "
            + ", ".join(missing))
    if gemini and not VERTEX_SA.exists() and not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError(
            f"No Gemini credential: provide {VERTEX_SA} or set GEMINI_API_KEY.")
