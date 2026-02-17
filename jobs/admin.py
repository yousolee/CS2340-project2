from django.contrib import admin
from .models import Job, JobApplication

# Register your models here.
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'mode', 'visa_sponsorship', 'posted_date']
    list_filter = ['mode', 'visa_sponsorship']
    search_fields = ['title', 'company', 'location', 'skills']
admin.site.register(Job, JobAdmin)


class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'job', 'applied_date']
    list_filter = ['applied_date']
    search_fields = ['applicant__username', 'job__title']
admin.site.register(JobApplication, JobApplicationAdmin)