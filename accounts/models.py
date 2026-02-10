from django.conf import settings
from django.db import models


class Recruiter(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recruiter_profile',
    )
    company_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        label = self.company_name or 'Recruiter'
        return f"{self.user.username} ({label})"
