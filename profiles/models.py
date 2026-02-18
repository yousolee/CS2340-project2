from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Profile(models.Model):
    class Role(models.TextChoices):
        JOB_SEEKER = "job_seeker", "Job Seeker"
        RECRUITER = "recruiter", "Recruiter"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.JOB_SEEKER,
        db_index=True,
    )
    headline = models.CharField(max_length=160, blank=True)
    summary = models.TextField(max_length=1000, blank=True)
    location = models.CharField(max_length=120, blank=True)
    skills = models.TextField(
        max_length=600,
        blank=True,
        help_text="Comma-separated or bullet-style skills",
    )
    links = models.TextField(
        max_length=1000,
        blank=True,
        help_text="One link per line (LinkedIn, GitHub, portfolio, etc.)",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Experience(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full-time"
        PART_TIME = "PART_TIME", "Part-time"
        CONTRACT = "CONTRACT", "Contract"
        INTERNSHIP = "INTERNSHIP", "Internship"
        FREELANCE = "FREELANCE", "Freelance"
        OTHER = "OTHER", "Other"

    class WorkLocationType(models.TextChoices):
        ONSITE = "ONSITE", "On-site"
        HYBRID = "HYBRID", "Hybrid"
        REMOTE = "REMOTE", "Remote"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="experiences")
    company = models.CharField(max_length=120)
    title = models.CharField(max_length=120)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, blank=True
    )
    location = models.CharField(max_length=120, blank=True)
    location_type = models.CharField(
        max_length=10, choices=WorkLocationType.choices, blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(max_length=1000, blank=True)
    activities = models.TextField(max_length=600, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_current", "-end_date", "-start_date", "-id"]

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        if self.is_current and self.end_date:
            raise ValidationError({"end_date": "Current roles should not have an end date."})

    def __str__(self):
        return f"{self.title} at {self.company}"


class Education(models.Model):
    class EnrollmentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full-time"
        PART_TIME = "PART_TIME", "Part-time"
        ONLINE = "ONLINE", "Online"
        BOOTCAMP = "BOOTCAMP", "Bootcamp"
        OTHER = "OTHER", "Other"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="educations")
    school = models.CharField(max_length=120)
    degree = models.CharField(max_length=120, blank=True)
    field_of_study = models.CharField(max_length=120, blank=True)
    enrollment_type = models.CharField(
        max_length=20, choices=EnrollmentType.choices, blank=True
    )
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    grade = models.CharField(max_length=40, blank=True)
    activities = models.TextField(max_length=600, blank=True)
    description = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_current", "-end_date", "-start_date", "-id"]

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        if self.is_current and self.end_date:
            raise ValidationError({"end_date": "Current enrollment should not have an end date."})

    def __str__(self):
        return self.school


class ProfileEmbedding(models.Model):
    profile = models.OneToOneField(
        Profile, on_delete=models.CASCADE, related_name="embedding_record"
    )
    embedding = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Embedding for profile {self.profile_id}"


class ProfileExperienceEmbedding(models.Model):
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name="experience_embedding_record",
    )
    embedding = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ProfileExperienceEmbedding<{self.profile_id}>"


class ProfileSummarySkillsEmbedding(models.Model):
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name="summary_skills_embedding_record",
    )
    embedding = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ProfileSummarySkillsEmbedding<{self.profile_id}>"


class ProfileTitleEmbedding(models.Model):
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name="title_embedding_record",
    )
    embedding = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ProfileTitleEmbedding<{self.profile_id}>"
