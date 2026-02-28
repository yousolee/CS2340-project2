import csv
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render

from applications.models import Application, Notification
from jobs.models import Job
from jobs.recommendations.service import recommend_jobs_for_profile
from profiles.models import Profile

from .models import Recruiter
from .forms import CandidateSearchForm, CustomErrorList, CustomUserCreationForm
from .utils import (
    get_user_role,
    is_administrator,
    is_recruiter as is_recruiter_user,
)

logger = logging.getLogger(__name__)


def _role_display_label(user):
    role = get_user_role(user)
    if role == 'administrator':
        return 'Administrator'
    if role == 'recruiter':
        return 'Recruiter'
    if role == 'job_seeker':
        return 'Job Seeker'
    return 'No Role'


def _notification_text(notification):
    if notification.verb == "application_received":
        applicant = (notification.data or {}).get("applicant", "A candidate")
        job_title = (notification.data or {}).get("job_title", "your job")
        return f"{applicant} applied to {job_title}."
    if notification.verb == "application_status_changed":
        new_status = (notification.data or {}).get("new_status", "")
        status_label = dict(Application.Status.choices).get(new_status, "Updated")
        return f"Application status changed to {status_label}."
    return notification.verb.replace("_", " ").capitalize()


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
    role = get_user_role(request.user)

    if role == 'recruiter':
        recruiter = request.user.recruiter_profile
        posted_jobs = Job.objects.filter(posted_by=recruiter)
        recent_applications = Application.objects.filter(
            job__posted_by=recruiter
        ).select_related("job", "applicant")[:8]
        unread_notifications_qs = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).select_related("application", "actor")[:8]
        unread_notifications = list(unread_notifications_qs)
        if unread_notifications:
            Notification.objects.filter(
                id__in=[notification.id for notification in unread_notifications]
            ).update(is_read=True)

        template_data = {
            'title': 'Recruiter Dashboard',
            'posted_jobs_count': posted_jobs.count(),
            'recent_jobs': posted_jobs[:5],
            'recent_applications': recent_applications,
            'notifications': [
                {
                    'id': notification.id,
                    'text': _notification_text(notification),
                    'created_at': notification.created_at,
                    'application_id': notification.application_id,
                }
                for notification in unread_notifications
            ],
        }
        return render(request, 'accounts/recruiter_dashboard.html', {'template_data': template_data})

    if role == 'job_seeker':
        profile, _ = Profile.objects.get_or_create(user=request.user)
        recommended_jobs = []
        profile_is_sparse = False
        try:
            recommended_jobs = recommend_jobs_for_profile(
                profile.id,
                k=int(getattr(settings, "RECOMMENDER_TOP_K", 8)),
            )
            if recommended_jobs:
                profile_is_sparse = recommended_jobs[0].profile_is_sparse
        except Exception:  # pragma: no cover - dashboard should not fail on recommendation errors
            logger.exception("Failed to load recommendations for profile %s", profile.id)

        recent_applications = Application.objects.filter(applicant=request.user).select_related(
            "job"
        )[:8]
        unread_notifications_qs = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).select_related("application", "actor")[:8]
        unread_notifications = list(unread_notifications_qs)

        template_data = {
            'title': 'Job Seeker Dashboard',
            'profile': profile,
            'recent_applications': recent_applications,
            'notification_count': len(unread_notifications),
            'recommended_jobs': recommended_jobs,
            'profile_is_sparse': profile_is_sparse,
            'notifications': [
                {
                    'id': notification.id,
                    'text': _notification_text(notification),
                    'created_at': notification.created_at,
                    'application_id': notification.application_id,
                }
                for notification in unread_notifications
            ],
        }
        return render(request, 'accounts/job_seeker_dashboard.html', {'template_data': template_data})

    if role == 'administrator':
        return redirect('accounts.admin_dashboard')

    return HttpResponseForbidden('No valid account role is assigned to this user.')


@login_required
def logout(request):
    auth_logout(request)
    return redirect('home.index')


@login_required
@user_passes_test(is_recruiter_user)
def candidate_search(request):
    template_data = {
        'title': 'Candidate Search',
    }

    if request.method == 'GET':
        form = CandidateSearchForm(request.GET)
        profiles = Profile.objects.filter(role=Profile.Role.JOB_SEEKER, visibility=Profile.Visibility.OPEN).select_related('user')

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
                profiles = profiles.filter(experiences__title__icontains=form.cleaned_data['job_title']).distinct()
            
            template_data['form'] = form
            template_data['profiles'] = profiles
            template_data['profile_count'] = profiles.count()
            return render(request, 'accounts/candidate_search.html', {'template_data': template_data})

    template_data['form'] = CandidateSearchForm()
    template_data['profiles'] = Profile.objects.none()
    template_data['profile_count'] = 0
    return render(request, 'accounts/candidate_search.html', {'template_data': template_data})


# ============= ADMIN DASHBOARD VIEWS =============

@login_required
@user_passes_test(is_administrator)
def admin_dashboard(request):
    """Main admin dashboard with statistics"""
    total_users = User.objects.count()
    total_recruiters = Recruiter.objects.count()
    total_job_seekers = Profile.objects.filter(role=Profile.Role.JOB_SEEKER).count()
    total_jobs = Job.objects.count()
    total_applications = Application.objects.count()
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
@user_passes_test(is_administrator)
def admin_users(request):
    """User management page"""
    users = User.objects.all().select_related('recruiter_profile', 'profile').order_by('-date_joined')

    users_with_roles = []
    for user in users:
        users_with_roles.append({
            'user': user,
            'role': _role_display_label(user),
        })

    template_data = {
        'title': 'User Management',
        'users_with_roles': users_with_roles,
    }
    return render(request, 'accounts/admin_users.html', {'template_data': template_data})


@login_required
@user_passes_test(is_administrator)
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
@user_passes_test(is_administrator)
def admin_jobs(request):
    """Job moderation page"""
    jobs = Job.objects.all().select_related('posted_by__user').order_by('-posted_date')

    template_data = {
        'title': 'Job Moderation',
        'jobs': jobs,
    }
    return render(request, 'accounts/admin_jobs.html', {'template_data': template_data})


@login_required
@user_passes_test(is_administrator)
def admin_delete_job(request, job_id):
    """Delete a job post"""
    if request.method == 'POST':
        job = Job.objects.get(id=job_id)
        job_title = job.title
        job.delete()
        messages.success(request, f'Job posting "{job_title}" has been removed.')

    return redirect('accounts.admin_jobs')


@login_required
@user_passes_test(is_administrator)
def admin_export_users(request):
    """Export users to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Role', 'Active', 'Date Joined'])

    users = User.objects.all().select_related('recruiter_profile', 'profile')
    for user in users:
        writer.writerow([
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            _role_display_label(user),
            user.is_active,
            user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


@login_required
@user_passes_test(is_administrator)
def admin_export_jobs(request):
    """Export jobs to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="jobs_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Job Title', 'Company', 'Location', 'Work Mode', 'Min Salary', 'Max Salary',
        'Visa Sponsorship', 'Skills', 'Posted By', 'Posted Date', 'Applications Count',
    ])

    jobs = Job.objects.all().select_related('posted_by__user')
    for job in jobs:
        app_count = Application.objects.filter(job=job).count()
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
@user_passes_test(is_administrator)
def admin_export_applications(request):
    """Export job applications to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="applications_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Applicant Username', 'Applicant Email', 'Applicant Name',
        'Job Title', 'Company', 'Personalized Note', 'Applied Date',
    ])

    applications = Application.objects.all().select_related('applicant', 'job')
    for app in applications:
        writer.writerow([
            app.applicant.username,
            app.applicant.email,
            app.applicant.get_full_name() or app.applicant.username,
            app.job.title,
            app.job.company,
            app.note,
            app.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response
