"""Embeddings — local, keyless, reproducible.

Uses fastembed (ONNX, CPU, no torch, no API key) so retrieval costs nothing and
anyone can run it. Model: BAAI/bge-small-en-v1.5 (384-dim). Swap the model name
here and the schema dimension in store.py together if you change it.
"""

from __future__ import annotations

import os
import pathlib
import tempfile
from functools import lru_cache

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


def _cache_dir() -> str:
    """A writable dir for fastembed's model cache.

    On serverless (Vercel) the filesystem is read-only except the temp dir, so
    the default cache location fails with 'Read-only file system'. tempfile's
    temp dir is writable everywhere (/tmp on Linux, %TEMP% on Windows)."""
    override = os.environ.get("FASTEMBED_CACHE_DIR")
    return override or str(pathlib.Path(tempfile.gettempdir()) / "fastembed")


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=EMBED_MODEL, cache_dir=_cache_dir())


def embed(texts: list[str]) -> list[list[float]]:
    return [[float(x) for x in v] for v in _model().embed(list(texts))]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
