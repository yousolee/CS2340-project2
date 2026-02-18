import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from jobs.recommendations.service import ensure_profile_field_embeddings

from .models import Education, Experience, Profile

User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, role=Profile.Role.JOB_SEEKER)


def _refresh_profile_embedding_fields(profile: Profile, fields: set[str]):
    try:
        print(f"Refreshing embedding for profile {profile.pk}")
        ensure_profile_field_embeddings(profile, fields=fields)
    except Exception:  # pragma: no cover - embedding failures should not block writes
        logger.exception(
            "Failed to refresh embedding fields %s for profile %s",
            sorted(fields),
            profile.pk,
        )


@receiver(post_save, sender=Profile)
def refresh_profile_embedding_after_profile_save(sender, instance, **kwargs):
    _refresh_profile_embedding_fields(instance, {"experience", "summary_skills", "title"})


@receiver(post_save, sender=Experience)
def refresh_profile_embedding_after_experience_save(sender, instance, **kwargs):
    _refresh_profile_embedding_fields(instance.profile, {"experience", "summary_skills", "title"})


@receiver(post_delete, sender=Experience)
def refresh_profile_embedding_after_experience_delete(sender, instance, **kwargs):
    _refresh_profile_embedding_fields(instance.profile, {"experience", "summary_skills", "title"})


@receiver(post_save, sender=Education)
def refresh_profile_embedding_after_education_save(sender, instance, **kwargs):
    _refresh_profile_embedding_fields(instance.profile, {"experience", "summary_skills", "title"})


@receiver(post_delete, sender=Education)
def refresh_profile_embedding_after_education_delete(sender, instance, **kwargs):
    _refresh_profile_embedding_fields(instance.profile, {"experience", "summary_skills", "title"})
