import hashlib
import math
import re
from typing import Any, Protocol

try:
    import cohere
except ImportError:
    cohere = None

from django.conf import settings

_TOKEN_RE = re.compile(r"[a-z0-9+#.-]+")


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class LocalDeterministicEmbeddingProvider:
    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = _TOKEN_RE.findall((text or "").lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if (digest[4] % 2 == 0) else -1.0
            vector[index] += sign

        return _l2_normalize(vector)


class CohereEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        dim: int,
        input_type: str = "search_document",
    ):
        self.api_key = api_key
        self.model = model
        self.dim = dim
        self.input_type = input_type
        self._fallback = LocalDeterministicEmbeddingProvider(dim=dim)
        self._client = cohere.Client(api_key) if cohere is not None else None

    def embed(self, text: str) -> list[float]:
        if not (text or "").strip():
            return self._fallback.embed(text)

        if self._client is None:
            return self._fallback.embed(text)

        try:
            response = self._client.embed(
                texts=[text],
                model=self.model,
                input_type=self.input_type,
            )
            vector = _extract_float_embedding(response)
            parsed = [float(value) for value in vector]
            if len(parsed) != self.dim:
                return self._fallback.embed(text)
            return _l2_normalize(parsed)
        except Exception:
            return self._fallback.embed(text)


def get_embedding_provider() -> EmbeddingProvider:
    dim = int(getattr(settings, "RECOMMENDER_EMBEDDING_DIM", 1024))
    provider_name = getattr(settings, "RECOMMENDER_EMBEDDING_PROVIDER", "cohere")

    if provider_name == "cohere":
        api_key = getattr(settings, "RECOMMENDER_COHERE_API_KEY", "")
        model = getattr(settings, "RECOMMENDER_COHERE_MODEL", "embed-english-v3.0")
        input_type = getattr(settings, "RECOMMENDER_COHERE_INPUT_TYPE", "search_document")
        if api_key and model:
            return CohereEmbeddingProvider(
                api_key=api_key,
                model=model,
                dim=dim,
                input_type=input_type,
            )

    # Backward-compatible alias from prior implementation.
    if provider_name == "external":
        api_key = getattr(settings, "RECOMMENDER_COHERE_API_KEY", "")
        model = getattr(settings, "RECOMMENDER_COHERE_MODEL", "embed-english-v3.0")
        input_type = getattr(settings, "RECOMMENDER_COHERE_INPUT_TYPE", "search_document")
        if api_key and model:
            return CohereEmbeddingProvider(
                api_key=api_key,
                model=model,
                dim=dim,
                input_type=input_type,
            )

    return LocalDeterministicEmbeddingProvider(dim=dim)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0:
        return vector
    return [value / norm for value in vector]


def _extract_float_embedding(response: Any) -> list[float]:
    embeddings = getattr(response, "embeddings", None)
    if embeddings is None:
        raise KeyError("Cohere SDK response is missing embeddings.")

    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, list):
            return first
        if isinstance(first, dict) and "float" in first and isinstance(first["float"], list):
            return first["float"]

    # Some SDK/model combinations return embeddings by type.
    float_vectors = getattr(embeddings, "float", None)
    if float_vectors is None:
        float_vectors = getattr(embeddings, "float_", None)
    if float_vectors is not None:
        if (
            isinstance(float_vectors, list)
            and float_vectors
            and isinstance(float_vectors[0], list)
        ):
            return float_vectors[0]

    raise KeyError("Unsupported Cohere embeddings response shape.")
