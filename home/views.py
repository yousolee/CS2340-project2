from django.shortcuts import render
from applications.models import Application
from accounts.utils import get_user_role
from jobs.models import Job
from profiles.models import Profile

# Create your views here.

def index(request):
    role = get_user_role(request.user)
    template_data = {
        'title': 'Home - Jobs Finder',
        'recent_jobs': Job.objects.order_by('-posted_date')[:5],
        'job_count': Job.objects.count(),
        'candidate_count': Profile.objects.filter(role=Profile.Role.JOB_SEEKER).count(),
        'company_count': Job.objects.values('company').distinct().count(),
    }

    if role == 'recruiter':
        recruiter = request.user.recruiter_profile
        recruiter_jobs = Job.objects.filter(posted_by=recruiter).order_by('-posted_date')
        template_data.update({
            'title': 'Recruiter Home - Jobs Finder',
            'my_jobs_count': recruiter_jobs.count(),
            'my_application_count': Application.objects.filter(job__posted_by=recruiter).count(),
            'recent_my_jobs': recruiter_jobs[:5],
        })
        return render(request, 'home/recruiter_index.html', {'template_data': template_data})

    return render(request, 'home/index.html', {'template_data': template_data})
    
def about(request):
    template_data = {}
    template_data['title'] = 'About'
    return render(request,
                  'home/about.html',
                  {'template_data': template_data})
