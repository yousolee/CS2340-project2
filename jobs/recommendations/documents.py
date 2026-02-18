import hashlib
import re

from jobs.models import Job
from profiles.models import Profile


_SKILL_SPLIT_RE = re.compile(r"[,\n\r\t\u2022;|/]+")


def _clean(value: str) -> str:
    return " ".join((value or "").strip().split())


def _normalize_skills(skills_text: str) -> str:
    raw_tokens = [token.strip().lower() for token in _SKILL_SPLIT_RE.split(skills_text or "")]
    tokens = [token for token in raw_tokens if token]
    return ", ".join(tokens)


def build_profile_experience_document(profile: Profile) -> str:
    lines: list[str] = ["Experience:"]
    for experience in profile.experiences.all():
        lines.append(
            (
                f"- {_clean(experience.title)} @ {_clean(experience.company)} "
                f"({_clean(experience.location_type)}, {_clean(experience.location)}) "
                f"- {_clean(experience.description)} {_clean(experience.activities)}"
            ).strip()
        )
    return "\n".join(lines)


def build_profile_summary_skills_document(profile: Profile) -> str:
    lines: list[str] = [
        f"Skills: {_normalize_skills(profile.skills)}",
    ]
    return "\n".join(lines)


def build_profile_title_document(profile: Profile) -> str:
    lines: list[str] = ["Titles:"]
    for title, company in profile.experiences.values_list("title", "company")[:5]:
        lines.append(f"- {_clean(title)} @ {_clean(company)}")
    return "\n".join(lines)


def build_job_description_document(job: Job) -> str:
    lines = [
        f"Title: {_clean(job.title)} @ {_clean(job.company)}",
        f"Description: {_clean(job.description)}",
        f"Location: {_clean(job.location)}",
        f"Mode: {_clean(job.mode)}",
    ]
    return "\n".join(lines)


def build_job_title_document(job: Job) -> str:
    lines = [
        f"Title: {_clean(job.title)}",
        f"Company: {_clean(job.company)}",
    ]
    return "\n".join(lines)


def build_job_skills_document(job: Job) -> str:
    lines = [
        f"Skills: {_normalize_skills(job.skills)}",
    ]
    return "\n".join(lines)


# Legacy wrappers kept for compatibility.
def build_profile_document(profile: Profile) -> str:
    lines = [
        build_profile_summary_skills_document(profile),
        build_profile_experience_document(profile),
        "Education:",
    ]
    for experience in profile.experiences.all():
        lines.append(f"- {_clean(experience.title)}")
    for education in profile.educations.values_list("school", flat=True):
        lines.append(
            f"- {_clean(education)}"
        )
    return "\n".join(lines)


def build_job_document(job: Job) -> str:
    return "\n".join(
        [
            build_job_title_document(job),
            build_job_skills_document(job),
            build_job_description_document(job),
        ]
    )


def compute_document_hash(document_text: str) -> str:
    return hashlib.sha256((document_text or "").encode("utf-8")).hexdigest()
