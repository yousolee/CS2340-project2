from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Max
from django.utils import timezone

from applications.models import Application
from jobs.models import (
    Job,
    JobDescriptionEmbedding,
    JobSkillsEmbedding,
    JobTitleEmbedding,
)
from profiles.models import (
    Profile,
    ProfileExperienceEmbedding,
    ProfileSummarySkillsEmbedding,
    ProfileTitleEmbedding,
)

from .documents import (
    build_job_description_document,
    build_job_skills_document,
    build_job_title_document,
    build_profile_experience_document,
    build_profile_summary_skills_document,
    build_profile_title_document,
    compute_document_hash,
)
from .embeddings import EmbeddingProvider, get_embedding_provider
from .scoring import (
    PairFeatures,
    compute_fit_score,
    compute_ranking_score,
    embedding_similarity_score,
    fit_band,
    fit_score_to_100,
    is_sparse_document,
    mode_location_structured_score,
    recency_boost,
    visa_structured_score,
)


@dataclass(frozen=True)
class ProfileFieldEmbeddings:
    experience_vector: list[float]
    summary_skills_vector: list[float]
    title_vector: list[float]
    experience_hash: str
    summary_skills_hash: str
    title_hash: str
    retrieval_vector: list[float]
    retrieval_hash: str
    retrieval_source: str
    profile_is_sparse: bool


@dataclass(frozen=True)
class JobFieldEmbeddings:
    description_vector: list[float]
    title_vector: list[float]
    skills_vector: list[float]
    description_hash: str
    title_hash: str
    skills_hash: str


@dataclass(frozen=True)
class RetrievedCandidate:
    job: Job
    retrieval_score: float


@dataclass(frozen=True)
class JobFitScore:
    fit_score_raw: float
    fit_score_100: int
    band: str
    components: dict[str, float]
    profile_is_sparse: bool


@dataclass(frozen=True)
class JobRecommendation:
    job: Job
    fit_score_raw: float
    fit_score_100: int
    ranking_score: float
    band: str
    components: dict[str, float]
    profile_is_sparse: bool


def _cache_timeout() -> int:
    return int(getattr(settings, "RECOMMENDER_CACHE_TTL", 30 * 60))


def _top_n() -> int:
    return int(getattr(settings, "RECOMMENDER_TOP_N", 200))


def _coerce_vector(values: list[Any]) -> list[float]:
    return [float(value) for value in (values or [])]


def _expected_embedding_dim() -> int:
    return int(getattr(settings, "RECOMMENDER_EMBEDDING_DIM", 1024))


def _has_expected_embedding_dim(values: list[Any]) -> bool:
    return isinstance(values, list) and len(values) == _expected_embedding_dim()


def _ensure_embedding_record(
    model_cls,
    lookup: dict[str, Any],
    document: str,
    provider: EmbeddingProvider,
    force: bool = False,
) -> tuple[list[float], str]:
    source_hash = compute_document_hash(document)
    record = model_cls.objects.filter(**lookup).first()
    should_refresh = (
        force
        or record is None
        or record.source_hash != source_hash
        or not record.embedding
        or not _has_expected_embedding_dim(record.embedding)
    )

    if should_refresh:
        vector = provider.embed(document)
        model_cls.objects.update_or_create(
            **lookup,
            defaults={"embedding": vector, "source_hash": source_hash},
        )
        return vector, source_hash

    return _coerce_vector(record.embedding), source_hash


def _selective_embedding_record(
    model_cls,
    lookup: dict[str, Any],
    document: str,
    provider: EmbeddingProvider,
    should_refresh: bool,
) -> tuple[list[float], str]:
    if should_refresh:
        return _ensure_embedding_record(model_cls, lookup, document, provider, force=False)

    source_hash = compute_document_hash(document)
    record = model_cls.objects.filter(**lookup).first()
    if (
        record is not None
        and record.embedding
        and str(record.source_hash or "") == source_hash
    ):
        return _coerce_vector(record.embedding), str(record.source_hash or source_hash)

    return _ensure_embedding_record(model_cls, lookup, document, provider, force=False)


def ensure_profile_field_embeddings(
    profile: Profile,
    force: bool = False,
    fields: set[str] | None = None,
) -> ProfileFieldEmbeddings:
    provider = get_embedding_provider()
    selected = set(fields or set())

    experience_doc = build_profile_experience_document(profile)
    print(f"Experience for profile {profile.pk}: {experience_doc}")
    summary_skills_doc = build_profile_summary_skills_document(profile)
    print(f"Summary for profile {profile.pk}: {summary_skills_doc}")
    title_doc = build_profile_title_document(profile)
    print(f"Title for profile {profile.pk}: {title_doc}")

    experience_vector, experience_hash = _selective_embedding_record(
        ProfileExperienceEmbedding,
        {"profile": profile},
        experience_doc,
        provider,
        should_refresh=force or ("experience" in selected),
    )
    summary_skills_vector, summary_skills_hash = _selective_embedding_record(
        ProfileSummarySkillsEmbedding,
        {"profile": profile},
        summary_skills_doc,
        provider,
        should_refresh=force or ("summary_skills" in selected),
    )
    title_vector, title_hash = _selective_embedding_record(
        ProfileTitleEmbedding,
        {"profile": profile},
        title_doc,
        provider,
        should_refresh=force or ("title" in selected),
    )

    profile_is_sparse = is_sparse_document(experience_doc)
    if profile_is_sparse:
        retrieval_vector = summary_skills_vector
        retrieval_hash = summary_skills_hash
        retrieval_source = "summary_skills"
    else:
        retrieval_vector = experience_vector
        retrieval_hash = experience_hash
        retrieval_source = "experience"

    print(f"Profile {profile.pk} embedding: experience_hash={experience_hash[:8]}, summary_skills_hash={summary_skills_hash[:8]}, title_hash={title_hash[:8]}, retrieval_source={retrieval_source}")
    return ProfileFieldEmbeddings(
        experience_vector=experience_vector,
        summary_skills_vector=summary_skills_vector,
        title_vector=title_vector,
        experience_hash=experience_hash,
        summary_skills_hash=summary_skills_hash,
        title_hash=title_hash,
        retrieval_vector=retrieval_vector,
        retrieval_hash=retrieval_hash,
        retrieval_source=retrieval_source,
        profile_is_sparse=profile_is_sparse,
    )


def ensure_job_field_embeddings(
    job: Job,
    force: bool = False,
    fields: set[str] | None = None,
) -> JobFieldEmbeddings:
    provider = get_embedding_provider()
    selected = set(fields or set())

    description_doc = build_job_description_document(job)
    title_doc = build_job_title_document(job)
    skills_doc = build_job_skills_document(job)

    description_vector, description_hash = _selective_embedding_record(
        JobDescriptionEmbedding,
        {"job": job},
        description_doc,
        provider,
        should_refresh=force or ("description" in selected),
    )
    title_vector, title_hash = _selective_embedding_record(
        JobTitleEmbedding,
        {"job": job},
        title_doc,
        provider,
        should_refresh=force or ("title" in selected),
    )
    skills_vector, skills_hash = _selective_embedding_record(
        JobSkillsEmbedding,
        {"job": job},
        skills_doc,
        provider,
        should_refresh=force or ("skills" in selected),
    )

    return JobFieldEmbeddings(
        description_vector=description_vector,
        title_vector=title_vector,
        skills_vector=skills_vector,
        description_hash=description_hash,
        title_hash=title_hash,
        skills_hash=skills_hash,
    )


def _job_description_version() -> str:
    latest = JobDescriptionEmbedding.objects.aggregate(max_updated=Max("updated_at"))["max_updated"]
    return str(int(latest.timestamp())) if latest else "none"


def _retrieval_cache_key(profile_id: int, profile_retrieval_hash: str) -> str:
    return (
        f"retrieval:{profile_id}:v2:"
        f"{(profile_retrieval_hash or '')[:12]}:{_job_description_version()}"
    )


def _fit_cache_key(
    profile_id: int,
    job_id: int,
    profile_fields: ProfileFieldEmbeddings,
    job_fields: JobFieldEmbeddings,
) -> str:
    profile_hash_tuple = (
        f"{profile_fields.experience_hash[:8]}-"
        f"{profile_fields.summary_skills_hash[:8]}-"
        f"{profile_fields.title_hash[:8]}"
    )
    job_hash_tuple = (
        f"{job_fields.description_hash[:8]}-"
        f"{job_fields.title_hash[:8]}-"
        f"{job_fields.skills_hash[:8]}"
    )
    return (
        f"fit:{profile_id}:{job_id}:v3:"
        f"d{_expected_embedding_dim()}:{profile_hash_tuple}:{job_hash_tuple}"
    )


def _profile_fields_from_models(profile: Profile) -> ProfileFieldEmbeddings | None:
    experience_record = ProfileExperienceEmbedding.objects.filter(profile=profile).first()
    summary_record = ProfileSummarySkillsEmbedding.objects.filter(profile=profile).first()
    title_record = ProfileTitleEmbedding.objects.filter(profile=profile).first()
    if not (experience_record and summary_record and title_record):
        return None
    if not (
        experience_record.embedding
        and summary_record.embedding
        and title_record.embedding
    ):
        return None
    if not (
        _has_expected_embedding_dim(experience_record.embedding)
        and _has_expected_embedding_dim(summary_record.embedding)
        and _has_expected_embedding_dim(title_record.embedding)
    ):
        return None

    profile_is_sparse = is_sparse_document(build_profile_experience_document(profile))
    if profile_is_sparse:
        retrieval_vector = _coerce_vector(summary_record.embedding)
        retrieval_hash = str(summary_record.source_hash or "")
        retrieval_source = "summary_skills"
    else:
        retrieval_vector = _coerce_vector(experience_record.embedding)
        retrieval_hash = str(experience_record.source_hash or "")
        retrieval_source = "experience"

    return ProfileFieldEmbeddings(
        experience_vector=_coerce_vector(experience_record.embedding),
        summary_skills_vector=_coerce_vector(summary_record.embedding),
        title_vector=_coerce_vector(title_record.embedding),
        experience_hash=str(experience_record.source_hash or ""),
        summary_skills_hash=str(summary_record.source_hash or ""),
        title_hash=str(title_record.source_hash or ""),
        retrieval_vector=retrieval_vector,
        retrieval_hash=retrieval_hash,
        retrieval_source=retrieval_source,
        profile_is_sparse=profile_is_sparse,
    )


def _job_fields_from_job(job: Job) -> JobFieldEmbeddings | None:
    try:
        description_record = job.description_embedding_record
        title_record = job.title_embedding_record
        skills_record = job.skills_embedding_record
    except (JobDescriptionEmbedding.DoesNotExist, JobTitleEmbedding.DoesNotExist, JobSkillsEmbedding.DoesNotExist):
        return None

    if not (
        description_record.embedding
        and title_record.embedding
        and skills_record.embedding
    ):
        return None
    if not (
        _has_expected_embedding_dim(description_record.embedding)
        and _has_expected_embedding_dim(title_record.embedding)
        and _has_expected_embedding_dim(skills_record.embedding)
    ):
        return None

    return JobFieldEmbeddings(
        description_vector=_coerce_vector(description_record.embedding),
        title_vector=_coerce_vector(title_record.embedding),
        skills_vector=_coerce_vector(skills_record.embedding),
        description_hash=str(description_record.source_hash or ""),
        title_hash=str(title_record.source_hash or ""),
        skills_hash=str(skills_record.source_hash or ""),
    )


def _get_profile_fields(profile: Profile) -> ProfileFieldEmbeddings:
    profile_fields = _profile_fields_from_models(profile)
    if profile_fields is not None:
        return profile_fields
    # One-time fallback for existing rows that predate embedding signals.
    ensure_profile_field_embeddings(profile, force=True)
    profile_fields = _profile_fields_from_models(profile)
    if profile_fields is None:
        return ensure_profile_field_embeddings(profile, force=True)
    return profile_fields


def _get_job_fields(job: Job) -> JobFieldEmbeddings:
    job_fields = _job_fields_from_job(job)
    if job_fields is not None:
        return job_fields
    # One-time fallback for existing rows that predate embedding signals.
    ensure_job_field_embeddings(job, force=True)
    job_fields = _job_fields_from_job(job)
    if job_fields is None:
        return ensure_job_field_embeddings(job, force=True)
    return job_fields


def retrieve_candidate_jobs(
    profile: Profile,
    profile_fields: ProfileFieldEmbeddings,
    top_n: int | None = None,
) -> list[RetrievedCandidate]:
    limit = top_n or _top_n()
    cache_key = _retrieval_cache_key(profile.id, profile_fields.retrieval_hash)
    cached = cache.get(cache_key)

    if cached is None:
        retrieval_scores: list[tuple[int, float]] = []
        for job in Job.objects.select_related("description_embedding_record"):
            try:
                description_record = job.description_embedding_record
            except JobDescriptionEmbedding.DoesNotExist:
                continue
            if not description_record.embedding:
                continue
            score = embedding_similarity_score(
                profile_fields.retrieval_vector,
                _coerce_vector(description_record.embedding),
            )
            retrieval_scores.append((job.id, score))

        retrieval_scores.sort(key=lambda item: item[1], reverse=True)
        cached = retrieval_scores[: limit * 3]
        cache.set(cache_key, cached, timeout=_cache_timeout())

    applied_job_ids = set(
        Application.objects.filter(applicant=profile.user).values_list("job_id", flat=True)
    )
    filtered = [item for item in cached if item[0] not in applied_job_ids]
    filtered = filtered[:limit]

    job_map = {
        job.id: job
        for job in Job.objects.filter(id__in=[job_id for job_id, _ in filtered]).select_related(
            "description_embedding_record",
            "title_embedding_record",
            "skills_embedding_record",
        )
    }

    ordered_candidates: list[RetrievedCandidate] = []
    for job_id, retrieval_score in filtered:
        job = job_map.get(job_id)
        if job is not None:
            ordered_candidates.append(
                RetrievedCandidate(job=job, retrieval_score=float(retrieval_score))
            )
    return ordered_candidates


def build_pair_features(
    profile: Profile,
    job: Job,
    profile_fields: ProfileFieldEmbeddings,
    job_fields: JobFieldEmbeddings,
    now,
) -> PairFeatures:
    return PairFeatures(
        exp_desc_embedding=embedding_similarity_score(
            profile_fields.experience_vector,
            job_fields.description_vector,
        ),
        title_embedding=embedding_similarity_score(
            profile_fields.title_vector,
            job_fields.title_vector,
        ),
        skills_embedding=embedding_similarity_score(
            profile_fields.summary_skills_vector,
            job_fields.skills_vector,
        ),
        summary_desc_embedding=embedding_similarity_score(
            profile_fields.summary_skills_vector,
            job_fields.description_vector,
        ),
        mode_location_structured=mode_location_structured_score(
            profile.location,
            job.location,
            job.mode,
        ),
        visa_structured=visa_structured_score(),
        recency_boost=recency_boost(job.posted_date, now),
    )


def _fit_score_from_cache(payload: dict[str, Any]) -> JobFitScore:
    return JobFitScore(
        fit_score_raw=float(payload["fit_score_raw"]),
        fit_score_100=int(payload["fit_score_100"]),
        band=str(payload["band"]),
        components={
            "exp_desc_embedding": float(payload["components"]["exp_desc_embedding"]),
            "title_embedding": float(payload["components"]["title_embedding"]),
            "skills_embedding": float(payload["components"]["skills_embedding"]),
            "summary_desc_embedding": float(payload["components"]["summary_desc_embedding"]),
            "mode_location_structured": float(payload["components"]["mode_location_structured"]),
            "visa_structured": float(payload["components"]["visa_structured"]),
        },
        profile_is_sparse=bool(payload.get("profile_is_sparse", False)),
    )


def _payload_from_features(features: PairFeatures, profile_is_sparse: bool) -> dict[str, Any]:
    fit_score_raw = compute_fit_score(features)
    fit_score_100 = fit_score_to_100(fit_score_raw)
    band = fit_band(fit_score_100)
    return {
        "fit_score_raw": fit_score_raw,
        "fit_score_100": fit_score_100,
        "band": band,
        "components": {
            "exp_desc_embedding": features.exp_desc_embedding,
            "title_embedding": features.title_embedding,
            "skills_embedding": features.skills_embedding,
            "summary_desc_embedding": features.summary_desc_embedding,
            "mode_location_structured": features.mode_location_structured,
            "visa_structured": features.visa_structured,
        },
        "profile_is_sparse": profile_is_sparse,
    }


def score_job_fit_for_profile(profile_id: int, job_id: int) -> JobFitScore:
    profile = (
        Profile.objects.select_related("user")
        .prefetch_related("experiences", "educations")
        .get(pk=profile_id)
    )
    job = Job.objects.get(pk=job_id)

    profile_fields = _get_profile_fields(profile)
    job_fields = _get_job_fields(job)
    key = _fit_cache_key(profile.id, job.id, profile_fields, job_fields)

    cached = cache.get(key)
    if cached is not None:
        return _fit_score_from_cache(cached)

    now = timezone.now()
    features = build_pair_features(profile, job, profile_fields, job_fields, now)
    payload = _payload_from_features(features, profile_fields.profile_is_sparse)
    cache.set(key, payload, timeout=_cache_timeout())
    return _fit_score_from_cache(payload)


def recommend_jobs_for_profile(profile_id: int, k: int = 8) -> list[JobRecommendation]:
    if not getattr(settings, "RECOMMENDER_ENABLED", True):
        return []

    profile = (
        Profile.objects.select_related("user")
        .prefetch_related("experiences", "educations")
        .get(pk=profile_id)
    )
    if profile.role != Profile.Role.JOB_SEEKER:
        return []

    profile_fields = _get_profile_fields(profile)
    candidates = retrieve_candidate_jobs(profile, profile_fields, top_n=_top_n())

    now = timezone.now()
    recommendations: list[JobRecommendation] = []
    for candidate in candidates:
        job_fields = _get_job_fields(candidate.job)
        key = _fit_cache_key(profile.id, candidate.job.id, profile_fields, job_fields)

        fit_payload = cache.get(key)
        if fit_payload is None:
            features = build_pair_features(profile, candidate.job, profile_fields, job_fields, now)
            fit_payload = _payload_from_features(features, profile_fields.profile_is_sparse)
            cache.set(key, fit_payload, timeout=_cache_timeout())
            fit = _fit_score_from_cache(fit_payload)
            recency_value = features.recency_boost
        else:
            fit = _fit_score_from_cache(fit_payload)
            recency_value = recency_boost(candidate.job.posted_date, now)

        ranking_score = compute_ranking_score(fit.fit_score_raw, recency_value)
        recommendations.append(
            JobRecommendation(
                job=candidate.job,
                fit_score_raw=fit.fit_score_raw,
                fit_score_100=fit.fit_score_100,
                ranking_score=ranking_score,
                band=fit.band,
                components=fit.components,
                profile_is_sparse=fit.profile_is_sparse,
            )
        )

    recommendations.sort(key=lambda item: item.ranking_score, reverse=True)
    return recommendations[:k]
