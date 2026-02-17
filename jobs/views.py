from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Recruiter

from .forms import JobCreateForm, JobSearchForm
from .models import Job


def get_recruiter(user):
    if not user.is_authenticated:
        return None
    try:
        return user.recruiter_profile
    except Recruiter.DoesNotExist:
        return None


def job_list(request):
    template_data = {}
    template_data['title'] = 'Search Jobs - JobsFinder'
    template_data['can_post_jobs'] = get_recruiter(request.user) is not None

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
        return render(request, 'jobs/job_list.html', {'template_data': template_data})


def job_detail(request, job_id):
    recruiter = get_recruiter(request.user)
    job = get_object_or_404(Job, pk=job_id)
    can_edit_job = recruiter is not None and job.posted_by_id == recruiter.id
    template_data = {
        'title': f"{job.title} - JobsFinder",
        'job': job,
        'can_edit_job': can_edit_job,
        'can_view_applications': can_edit_job,
        'application_count': job.applications.count() if can_edit_job else 0,
    }
    return render(request, 'jobs/job_detail.html', {'template_data': template_data})


@login_required
def create_job(request):
    recruiter = get_recruiter(request.user)
    if recruiter is None:
        return HttpResponseForbidden('Only recruiter accounts can create job postings.')

    template_data = {
        'title': 'Create Job Posting - JobsFinder',
        'can_post_jobs': True,
    }

    if request.method == 'POST':
        form = JobCreateForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = recruiter
            job.save()
            return redirect('jobs.detail', job_id=job.id)
    else:
        form = JobCreateForm(initial={'company': recruiter.company_name})

    template_data['form'] = form
    return render(request, 'jobs/job_create.html', {'template_data': template_data})


@login_required
def edit_job(request, job_id):
    recruiter = get_recruiter(request.user)
    if recruiter is None:
        return HttpResponseForbidden('Only recruiter accounts can edit job postings.')

    job = get_object_or_404(Job, pk=job_id)
    if job.posted_by_id != recruiter.id:
        return HttpResponseForbidden('You can only edit your own job postings.')

    template_data = {
        'title': 'Edit Job Posting - JobsFinder',
        'can_post_jobs': True,
        'form_heading': 'Edit Job Posting',
        'submit_label': 'Save Changes',
        'cancel_to_job': True,
        'job_id': job.id,
    }

    if request.method == 'POST':
        form = JobCreateForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            return redirect('jobs.detail', job_id=job.id)
    else:
        form = JobCreateForm(instance=job)

    template_data['form'] = form
    return render(request, 'jobs/job_create.html', {'template_data': template_data})


@login_required
def my_postings(request):
    recruiter = get_recruiter(request.user)
    if recruiter is None:
        return HttpResponseForbidden('Only recruiter accounts can view recruiter postings.')

    jobs = Job.objects.filter(posted_by=recruiter).annotate(application_count=Count("applications"))
    template_data = {
        'title': 'My Job Postings - JobsFinder',
        'jobs': jobs,
        'job_count': jobs.count(),
        'can_post_jobs': True,
    }
    return render(request, 'jobs/my_postings.html', {'template_data': template_data})
