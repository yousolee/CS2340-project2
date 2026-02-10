from django.conf import settings
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    headline = models.CharField(max_length=120, blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated or bullet-style skills")
    education = models.TextField(blank=True)
    work_experience = models.TextField(blank=True)
    links = models.TextField(blank=True, help_text="One link per line (LinkedIn, GitHub, portfolio, etc.)")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"
