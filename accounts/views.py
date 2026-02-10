from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required

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
