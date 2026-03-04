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
    logo = models.ImageField(upload_to='recruiter_logos/', null=True, blank=True)

    def __str__(self):
        label = self.company_name or 'Recruiter'
        return f"{self.user.username} ({label})"


class SavedSearch(models.Model):
    recruiter = models.ForeignKey(
        Recruiter,
        on_delete=models.CASCADE,
        related_name='saved_searches',
    )
    name = models.CharField(max_length=200)
    skills = models.CharField(max_length=600, blank=True)
    location = models.CharField(max_length=120, blank=True)
    company = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    last_checked_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.recruiter.user.username})"

    def get_query_params(self):
        params = {}
        if self.skills:
            params['skills'] = self.skills
        if self.location:
            params['location'] = self.location
        if self.company:
            params['company'] = self.company
        if self.job_title:
            params['job_title'] = self.job_title
        return params

    def get_search_url(self):
        from django.urls import reverse
        from django.utils.http import urlencode
        params = self.get_query_params()
        url = reverse('accounts.candidate_search')
        if params:
            url += '?' + urlencode(params)
        return url
