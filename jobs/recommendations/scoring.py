import math
import re
from dataclasses import dataclass
from datetime import datetime

_TOKEN_RE = re.compile(r"[a-z0-9+#.-]+")


@dataclass(frozen=True)
class PairFeatures:
    exp_desc_embedding: float
    title_embedding: float
    skills_embedding: float
    summary_desc_embedding: float
    mode_location_structured: float
    visa_structured: float
    recency_boost: float


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(value, max_value))


def normalize_tokens(value: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall((value or "").lower()) if token}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    if length == 0:
        return 0.0

    dot = sum(a[i] * b[i] for i in range(length))
    norm_a = math.sqrt(sum(a[i] * a[i] for i in range(length)))
    norm_b = math.sqrt(sum(b[i] * b[i] for i in range(length)))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embedding_similarity_score(profile_vector: list[float], job_vector: list[float]) -> float:
    cosine = cosine_similarity(profile_vector, job_vector)
    return clamp((cosine + 1.0) / 2.0)


def mode_location_structured_score(profile_location: str, job_location: str, job_mode: str) -> float:
    mode = (job_mode or "").lower()
    if mode == "remote":
        return 0.75

    profile_tokens = normalize_tokens(profile_location)
    job_tokens = normalize_tokens(job_location)

    if not job_tokens:
        return 0.3
    if not profile_tokens:
        return 0.5

    overlap = len(profile_tokens.intersection(job_tokens)) / len(job_tokens)
    if overlap <= 0:
        return 0.25
    return clamp(0.6 + 0.4 * overlap)


def visa_structured_score() -> float:
    # Neutral value until candidate visa preference exists in the schema.
    return 0.5


def recency_boost(posted_date: datetime | None, now: datetime) -> float:
    if posted_date is None:
        return 0.0
    age_days = max(0.0, (now - posted_date).total_seconds() / 86400.0)
    return clamp(math.exp(-age_days / 30.0))


def compute_fit_score(features: PairFeatures) -> float:
    raw = (
        0.60 * features.exp_desc_embedding
        + 0.20 * features.title_embedding
        + 0.20 * features.skills_embedding
        #+ 0.15 * features.summary_desc_embedding
        #+ 0.10 * features.mode_location_structured
        #+ 0.05 * features.visa_structured
    )
    return clamp(raw)


def compute_ranking_score(fit_score_raw: float, recency_value: float) -> float:
    return clamp(0.85 * fit_score_raw + 0.15 * clamp(recency_value))


def fit_score_to_100(fit_score_raw: float) -> int:
    return round(clamp(fit_score_raw) * 100)


def fit_band(score_100: int) -> str:
    if score_100 <= 39:
        return "low"
    if score_100 <= 69:
        return "medium"
    return "high"


def is_sparse_document(document_text: str, min_tokens: int = 8) -> bool:
    return len(normalize_tokens(document_text)) < min_tokens
