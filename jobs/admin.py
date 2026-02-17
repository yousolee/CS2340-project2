from django.contrib import admin
from .models import Job

# Register your models here.
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'mode', 'visa_sponsorship', 'posted_date']
    list_filter = ['mode', 'visa_sponsorship']
    search_fields = ['title', 'company', 'location', 'skills']
admin.site.register(Job, JobAdmin)
