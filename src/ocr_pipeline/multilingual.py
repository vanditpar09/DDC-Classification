"""Offline text features for the multilingual DDC experiments.

The encoder is downloaded explicitly, never by an inference request. Only text
is accepted here; labels, identifiers and catalog decisions are not features.
"""
from __future__ import annotations

from functools import lru_cache
from collections import OrderedDict
import os
from pathlib import Path

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

ROOT = Path(__file__).resolve().parents[2]
ENCODER_PATH = "models/encoders/multilingual-e5-small"
ENCODER_ID = "intfloat/multilingual-e5-small"
ENCODER_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"


@lru_cache(maxsize=2)
def get_encoder(path: str):
    from sentence_transformers import SentenceTransformer
    import torch

    threads = int(os.environ.get("FIELDNOTE_CPU_THREADS", "4"))
    if not 1 <= threads <= 32:
        raise ValueError("FIELDNOTE_CPU_THREADS must be between 1 and 32")
    torch.set_num_threads(threads)
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = ROOT / resolved
    if not (resolved / "config.json").exists():
        raise FileNotFoundError(
            f"Local encoder missing: {resolved}. See docs/MODEL_IMPROVEMENT.md."
        )
    return SentenceTransformer(str(resolved), device="cpu", local_files_only=True, trust_remote_code=False)


class MultilingualEmbeddings(TransformerMixin, BaseEstimator):
    """Frozen E5 embeddings; the query prefix is also used for classification.

    The small in-memory cache avoids re-encoding identical strings during CV.
    Neither this cache nor the large encoder weights are copied into joblib.
    """

    def __init__(self, encoder_path=ENCODER_PATH, batch_size=32, cache_size=2048):
        self.encoder_path = encoder_path
        self.batch_size = batch_size
        self.cache_size = cache_size

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if not hasattr(self, "_cache"):
            self._cache = OrderedDict()
        elif not isinstance(self._cache, OrderedDict):
            self._cache = OrderedDict(self._cache)
        limit = getattr(self, "cache_size", 2048)  # Compatibility with existing joblib artifacts.
        if limit < 0:
            raise ValueError("cache_size cannot be negative")
        texts = [str(x) for x in X]
        missing = list(dict.fromkeys(x for x in texts if x not in self._cache))
        fresh = {}
        if missing:
            vectors = get_encoder(self.encoder_path).encode(
                ["query: " + x for x in missing],
                batch_size=self.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            if not np.isfinite(vectors).all():
                raise ValueError("Encoder returned non-finite embeddings")
            fresh = dict(zip(missing, vectors))
        # Materialize before eviction: a training batch may exceed the cache size.
        result = np.asarray([self._cache[x] if x in self._cache else fresh[x] for x in texts], dtype=np.float32)
        for text in texts:
            if text in self._cache:
                self._cache.move_to_end(text)
            else:
                self._cache[text] = fresh[text]
        while len(self._cache) > limit:
            self._cache.popitem(last=False)
        return result

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k != "_cache"}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.cache_size = state.get("cache_size", 2048)
