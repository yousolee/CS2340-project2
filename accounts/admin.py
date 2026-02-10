from django.contrib import admin
from .models import Recruiter


@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'created_at']
    search_fields = ['user__username', 'company_name']
