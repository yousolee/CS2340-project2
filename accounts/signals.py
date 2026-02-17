from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from profiles.models import Profile

from .models import Recruiter


@receiver(post_save, sender=Recruiter)
def mark_profile_as_recruiter(sender, instance, **kwargs):
    Profile.objects.update_or_create(
        user=instance.user,
        defaults={"role": Profile.Role.RECRUITER},
    )


@receiver(post_delete, sender=Recruiter)
def mark_profile_as_job_seeker(sender, instance, **kwargs):
    Profile.objects.update_or_create(
        user=instance.user,
        defaults={"role": Profile.Role.JOB_SEEKER},
    )
