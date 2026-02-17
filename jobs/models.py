from django.conf import settings
from django.db import models

from accounts.models import Recruiter

# Create your models here.
class Job(models.Model):
    WORK_OPTIONS = [
        ('remote', 'Remote'),
        ('onsite', 'On-Site'),
        ('hybrid', 'Hybrid'),
    ]

    title = models.CharField(max_length = 200)
    company = models.CharField(max_length = 200)
    location = models.CharField(max_length = 200)
    description = models.TextField()
    skills = models.TextField(help_text = "Comma-separated skills (i.e. Python, Django, Java)")
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    visa_sponsorship = models.BooleanField(default=False)
    posted_date = models.DateTimeField(auto_now_add=True)
    mode = models.CharField(max_length=10, choices=WORK_OPTIONS, default='onsite')
    posted_by = models.ForeignKey(
        Recruiter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='jobs',
    )

    def __str__(self):
        return f"{self.title} at {self.company}"

    class Meta:
        ordering  = ['-posted_date']


class JobApplication(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications',
    )
    note = models.TextField(blank=True, help_text="Include a personalized note with your application")
    applied_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_date']
        unique_together = ['job', 'applicant']

    def __str__(self):
        return f"{self.applicant.username} -> {self.job.title}"
