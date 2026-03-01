from django.shortcuts import render
from jobs.models import Job
from profiles.models import Profile
from django.db.models import Count

# Create your views here.

def index(request):
    template_data = {
        'title': 'Home - Jobs Finder',
        'recent_jobs': Job.objects.order_by('-posted_date')[:5],
        'job_count': Job.objects.count(),
        'candidate_count': Profile.objects.filter(role=Profile.Role.JOB_SEEKER).count(),
        'company_count': Job.objects.values('company').distinct().count(),
    }
    return render(request, 'home/index.html', {'template_data': template_data})
    
def about(request):
    template_data = {}
    template_data['title'] = 'About'
    return render(request,
                  'home/about.html',
                  {'template_data': template_data})