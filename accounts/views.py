from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from profiles.models import Profile, Experience
from .forms import CandidateSearchForm

from jobs.models import Job
from .forms import CustomUserCreationForm, CustomErrorList


def is_recruiter(user):
    return user.is_authenticated and hasattr(user, 'recruiter_profile')


def signup(request):
    template_data = {}
    template_data['title'] = 'Sign Up'

    if request.method == 'GET':
        template_data['form'] = CustomUserCreationForm()
        return render(request, 'accounts/signup.html', {'template_data': template_data})

    elif request.method == 'POST':
        form = CustomUserCreationForm(request.POST, error_class=CustomErrorList)
        if form.is_valid():
            user = form.save()

            auth_login(request, user)
            return redirect('accounts.dashboard')
        else:
            template_data['form'] = form
            return render(request, 'accounts/signup.html', {'template_data': template_data})


def login(request):
    template_data = {}
    template_data['title'] = 'Login'

    if request.method == 'GET':
        return render(request, 'accounts/login.html', {'template_data': template_data})

    elif request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user is None:
            template_data['error'] = 'The username or password is incorrect.'
            return render(request, 'accounts/login.html', {'template_data': template_data})
        else:
            auth_login(request, user)
            return redirect('accounts.dashboard')


@login_required
def dashboard(request):
    if is_recruiter(request.user):
        recruiter = request.user.recruiter_profile
        posted_jobs = Job.objects.filter(posted_by=recruiter)
        template_data = {
            'title': 'Recruiter Dashboard',
            'posted_jobs_count': posted_jobs.count(),
            'recent_jobs': posted_jobs[:5],
        }
        return render(request, 'accounts/recruiter_dashboard.html', {'template_data': template_data})

    template_data = {
        'title': 'Job Seeker Dashboard',
    }
    return render(request, 'accounts/job_seeker_dashboard.html', {'template_data': template_data})


@login_required
def logout(request):
    auth_logout(request)
    return redirect('home.index')

@login_required
@user_passes_test(is_recruiter)
def candidate_search(request):
    template_data = {}
    template_data['title'] = 'Candidate Search'

    if request.method == 'GET':
        form = CandidateSearchForm(request.GET)
        profiles = Profile.objects.filter(user__recruiter_profile__isnull=True).select_related('user')

        if form.is_valid():
            if form.cleaned_data.get('skills'):
                skills_list = [skill.strip() for skill in form.cleaned_data['skills'].split(',')]
                skill_query = Q()
                for skill in skills_list:
                    skill_query |= Q(skills__icontains=skill)
                profiles = profiles.filter(skill_query)
            
            if form.cleaned_data.get('location'):
                profiles = profiles.filter(location__icontains=form.cleaned_data['location'])
            
            if form.cleaned_data.get('company'):
                profiles = profiles.filter(experiences__company__icontains=form.cleaned_data['company']).distinct()
            
            if form.cleaned_data.get('job_title'):
                profiles = profiles.filter(experiences__job_title__icontains=form.cleaned_data['job_title']).distinct()
            
            template_data['form'] = form
            template_data['profiles'] = profiles
            template_data['profile_count'] = profiles.count()
            return render(request, 'accounts/candidate_search.html', {'template_data': template_data})
    