from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from profiles.models import Profile, Experience
from .forms import CandidateSearchForm
from .models import Recruiter
from jobs.models import Job
from .forms import CustomUserCreationForm, CustomErrorList
import csv
from django.http import HttpResponse


def is_recruiter(user):
    return user.is_authenticated and hasattr(user, 'recruiter_profile')


def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


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
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if user exists and is inactive
        try:
            existing_user = User.objects.get(username=username)
            if not existing_user.is_active:
                template_data['error'] = 'Your account has been deactivated. Please contact an administrator.'
                return render(request, 'accounts/login.html', {'template_data': template_data})
        except User.DoesNotExist:
            pass  # Will handle in authenticate below

        user = authenticate(
            request,
            username=username,
            password=password
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
        from jobs.models import JobApplication
        recruiter = request.user.recruiter_profile
        posted_jobs = Job.objects.filter(posted_by=recruiter)
        total_applications = JobApplication.objects.filter(job__posted_by=recruiter).count()
        template_data = {
            'title': 'Recruiter Dashboard',
            'posted_jobs_count': posted_jobs.count(),
            'total_applications': total_applications,
            'recent_jobs': posted_jobs[:5],
        }
        return render(request, 'accounts/recruiter_dashboard.html', {'template_data': template_data})

    if hasattr(request.user, 'profile'):
        from jobs.models import JobApplication
        application_count = JobApplication.objects.filter(applicant=request.user).count()
        template_data = {
            'title': 'Job Seeker Dashboard',
            'application_count': application_count,
        }
    else:
        template_data = {
            'title': 'Job Seeker Dashboard',
            'application_count': 0,
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


# ============= ADMIN DASHBOARD VIEWS =============

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard with statistics"""
    from jobs.models import JobApplication

    total_users = User.objects.count()
    total_recruiters = Recruiter.objects.count()
    total_job_seekers = Profile.objects.count()
    total_jobs = Job.objects.count()
    total_applications = JobApplication.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()

    template_data = {
        'title': 'Admin Dashboard',
        'total_users': total_users,
        'total_recruiters': total_recruiters,
        'total_job_seekers': total_job_seekers,
        'total_jobs': total_jobs,
        'total_applications': total_applications,
        'active_users': active_users,
        'inactive_users': inactive_users,
    }
    return render(request, 'accounts/admin_dashboard.html', {'template_data': template_data})


@login_required
@user_passes_test(is_admin)
def admin_users(request):
    """User management page"""
    users = User.objects.all().select_related('recruiter_profile', 'profile').order_by('-date_joined')

    # Add role to each user
    users_with_roles = []
    for user in users:
        if user.is_superuser:
            role = 'Administrator'
        elif hasattr(user, 'recruiter_profile'):
            role = 'Recruiter'
        elif hasattr(user, 'profile'):
            role = 'Job Seeker'
        else:
            role = 'No Role'

        users_with_roles.append({
            'user': user,
            'role': role,
        })

    template_data = {
        'title': 'User Management',
        'users_with_roles': users_with_roles,
    }
    return render(request, 'accounts/admin_users.html', {'template_data': template_data})


@login_required
@user_passes_test(is_admin)
def admin_toggle_user(request, user_id):
    """Toggle user active status"""
    if request.method == 'POST':
        user = User.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()

        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {user.username} has been {status}.')

    return redirect('accounts.admin_users')


@login_required
@user_passes_test(is_admin)
def admin_jobs(request):
    """Job moderation page"""
    jobs = Job.objects.all().select_related('posted_by__user').order_by('-posted_date')

    template_data = {
        'title': 'Job Moderation',
        'jobs': jobs,
    }
    return render(request, 'accounts/admin_jobs.html', {'template_data': template_data})


@login_required
@user_passes_test(is_admin)
def admin_delete_job(request, job_id):
    """Delete a job post"""
    if request.method == 'POST':
        job = Job.objects.get(id=job_id)
        job_title = job.title
        job.delete()
        messages.success(request, f'Job posting "{job_title}" has been removed.')

    return redirect('accounts.admin_jobs')


@login_required
@user_passes_test(is_admin)
def admin_export_users(request):
    """Export users to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Role', 'Active', 'Date Joined'])

    users = User.objects.all().select_related('recruiter_profile', 'profile')
    for user in users:
        if user.is_superuser:
            role = 'Administrator'
        elif hasattr(user, 'recruiter_profile'):
            role = 'Recruiter'
        elif hasattr(user, 'profile'):
            role = 'Job Seeker'
        else:
            role = 'No Role'

        writer.writerow([
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            role,
            user.is_active,
            user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


@login_required
@user_passes_test(is_admin)
def admin_export_jobs(request):
    """Export jobs to CSV"""
    from jobs.models import JobApplication

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="jobs_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Job Title', 'Company', 'Location', 'Work Mode', 'Min Salary', 'Max Salary',
        'Visa Sponsorship', 'Skills', 'Posted By', 'Posted Date', 'Applications Count',
    ])

    jobs = Job.objects.all().select_related('posted_by__user')
    for job in jobs:
        app_count = JobApplication.objects.filter(job=job).count()
        writer.writerow([
            job.title,
            job.company,
            job.location,
            job.get_mode_display(),
            job.min_salary or '',
            job.max_salary or '',
            'Yes' if job.visa_sponsorship else 'No',
            job.skills,
            job.posted_by.user.username if job.posted_by else '',
            job.posted_date.strftime('%Y-%m-%d %H:%M:%S'),
            app_count,
        ])

    return response


@login_required
@user_passes_test(is_admin)
def admin_export_applications(request):
    """Export job applications to CSV"""
    from jobs.models import JobApplication

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="applications_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Applicant Username', 'Applicant Email', 'Applicant Name',
        'Job Title', 'Company', 'Personalized Note', 'Applied Date',
    ])

    applications = JobApplication.objects.all().select_related('applicant', 'job')
    for app in applications:
        writer.writerow([
            app.applicant.username,
            app.applicant.email,
            app.applicant.get_full_name() or app.applicant.username,
            app.job.title,
            app.job.company,
            app.note,
            app.applied_date.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response
