from django.contrib import admin
from .models import Recruiter, SavedSearch


@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'created_at']
    search_fields = ['user__username', 'company_name']


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ['name', 'recruiter', 'skills', 'location', 'company', 'job_title', 'last_checked_at', 'created_at']
    search_fields = ['name', 'recruiter__user__username']
    list_filter = ['created_at']
