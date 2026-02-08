from django.shortcuts import render
from django.db.models import Q
from .models import Job
from .forms import JobSearchForm


# Create your views here.

def job_search(request):
    template_data = {}
    template_data['title'] = 'Search Jobs - JobsFinder'
    
    if request.method == 'GET':
        form = JobSearchForm(request.GET)
        jobs = Job.objects.all()
        
        if form.is_valid():

            if form.cleaned_data.get('title'):
                jobs = jobs.filter(title__icontains=form.cleaned_data['title'])
            
            if form.cleaned_data.get('skills'):
                skills_list = [skill.strip() for skill in form.cleaned_data['skills'].split(',')]
                skill_query = Q()
                for skill in skills_list:
                    skill_query |= Q(skills__icontains=skill)
                jobs = jobs.filter(skill_query)
            
            if form.cleaned_data.get('location'):
                jobs = jobs.filter(location__icontains=form.cleaned_data['location'])
            
            if form.cleaned_data.get('min_salary'):
                jobs = jobs.filter(max_salary__gte=form.cleaned_data['min_salary'])
            
            if form.cleaned_data.get('max_salary'):
                jobs = jobs.filter(min_salary__lte=form.cleaned_data['max_salary'])
            
            if form.cleaned_data.get('mode'):
                jobs = jobs.filter(mode=form.cleaned_data['mode'])
            
            if form.cleaned_data.get('visa_sponsorship'):
                jobs = jobs.filter(visa_sponsorship=True)
        
        template_data['form'] = form
        template_data['jobs'] = jobs
        template_data['job_count'] = jobs.count()
        return render(request, 'jobs/job_search.html', {'template_data': template_data})