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


class JobEmbedding(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="embedding_record")
    embedding = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Embedding for job {self.job_id}"


class JobDescriptionEmbedding(models.Model):
    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name="description_embedding_record",
    )
    embedding = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"JobDescriptionEmbedding<{self.job_id}>"


class JobTitleEmbedding(models.Model):
    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name="title_embedding_record",
    )
    embedding = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"JobTitleEmbedding<{self.job_id}>"


class JobSkillsEmbedding(models.Model):
    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name="skills_embedding_record",
    )
    embedding = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"JobSkillsEmbedding<{self.job_id}>"
