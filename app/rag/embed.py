"""Embeddings — local, keyless, reproducible.

Uses fastembed (ONNX, CPU, no torch, no API key) so retrieval costs nothing and
anyone can run it. Model: BAAI/bge-small-en-v1.5 (384-dim). Swap the model name
here and the schema dimension in store.py together if you change it.
"""

from __future__ import annotations

from functools import lru_cache

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    return [[float(x) for x in v] for v in _model().embed(list(texts))]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
