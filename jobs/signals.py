import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Job
from .recommendations.service import ensure_job_field_embeddings

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Job)
def refresh_job_embedding(sender, instance, **kwargs):
    try:
        fields = {"description", "title", "skills"}
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            fields = set()
            if {"description", "location", "mode"}.intersection(update_fields):
                fields.add("description")
            if {"title", "company"}.intersection(update_fields):
                fields.add("title")
            if "skills" in update_fields or "title" in update_fields:
                fields.add("skills")
            if not fields:
                fields = {"description", "title", "skills"}
        ensure_job_field_embeddings(instance, fields=fields)
    except Exception:  # pragma: no cover - scoring failures should not block writes
        logger.exception("Failed to refresh embedding for job %s", instance.pk)
