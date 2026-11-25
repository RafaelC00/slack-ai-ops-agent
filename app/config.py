"""Tiny .env loader for local dev and scripts.

In production (Vercel) env vars come from the platform; locally we read .env.
Never overrides an already-set variable.
"""

from __future__ import annotations

import os
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_env() -> None:
    p = _ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
