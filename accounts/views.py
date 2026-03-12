import csv
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from applications.models import Application, Notification
from jobs.models import Job
from jobs.recommendations.service import recommend_jobs_for_profile, recommend_profiles_for_job
from profiles.models import Profile

from .models import Recruiter, SavedSearch
from .forms import (
    CandidateSearchForm,
    CustomErrorList,
    CustomUserCreationForm,
    RecruiterAccountForm,
    RecruiterProfileForm,
    SavedSearchForm,
)
from .utils import (
    filter_candidate_profiles,
    get_user_role,
    is_administrator,
    is_recruiter as is_recruiter_user,
)

logger = logging.getLogger(__name__)

RECRUITER_PROFILE_SECTION_LABELS = {
    'basic': 'Basic Info',
    'company': 'Company Profile',
}


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
    if notification.verb == "saved_search_new_matches":
        search_name = (notification.data or {}).get("search_name", "A saved search")
        match_count = (notification.data or {}).get("match_count", 0)
        return f'{match_count} new candidate(s) match your saved search "{search_name}".'
    return notification.verb.replace("_", " ").capitalize()


def _build_applicant_map_context(recruiter, selected_job_id=''):
    recruiter_jobs = Job.objects.filter(posted_by=recruiter).order_by('-posted_date')
    selected_job = None
    applications = Application.objects.filter(job__posted_by=recruiter)

    if selected_job_id:
        selected_job = recruiter_jobs.filter(pk=selected_job_id).first()
        if selected_job is not None:
            applications = applications.filter(job=selected_job)

    location_counts = (
        applications
        .exclude(applicant__profile__location__isnull=True)
        .exclude(applicant__profile__location='')
        .values('applicant__profile__location')
        .annotate(count=Count('applicant', distinct=True))
        .order_by('-count', 'applicant__profile__location')
    )

    location_data = []
    for entry in location_counts:
        location = entry['applicant__profile__location'].strip()
        if location.lower() == 'remote':
            continue
        location_data.append({
            'location': location,
            'count': entry['count'],
        })

    return {
        'location_data': location_data,
        'location_data_json': json.dumps(location_data),
        'total_applicants': sum(entry['count'] for entry in location_data),
        'recruiter_jobs': recruiter_jobs,
        'selected_job': selected_job,
        'selected_job_id': selected_job_id,
    }


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
        selected_job_id = (request.GET.get('job_id') or '').strip()
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

        status_breakdown = Application.objects.filter(job__posted_by=recruiter).values('status').annotate(count=Count('id'))
        status_map = {s['status']: s['count'] for s in status_breakdown}
        statuses = Application.Status.choices
        status_labels = [label for _, label in statuses]
        status_counts = [status_map.get(value, 0) for value, _ in statuses]
        saved_searches = SavedSearch.objects.filter(recruiter=recruiter)
        applicant_map_data = _build_applicant_map_context(recruiter, selected_job_id)

        template_data = {
            'title': 'Recruiter Dashboard',
            'posted_jobs_count': posted_jobs.count(),
            'recent_jobs': posted_jobs[:5],
            'recent_applications': recent_applications,
            'status_labels': status_labels,
            'status_counts': status_counts,
            'saved_searches': saved_searches,
            'notifications': [
                {
                    'id': notification.id,
                    'text': _notification_text(notification),
                    'created_at': notification.created_at,
                    'application_id': notification.application_id,
                    'search_url': (
                        (notification.data or {}).get('search_url', '')
                        if notification.verb == 'saved_search_new_matches'
                        else ''
                    ),
                }
                for notification in unread_notifications
            ],
            **applicant_map_data,
        }
        return render(request, 'accounts/recruiter_dashboard.html', {'template_data': template_data})

    if role == 'job_seeker':
        profile, _ = Profile.objects.get_or_create(user=request.user)

        applications = Application.objects.filter(applicant=request.user)
        total_applications = applications.count()
        pending_applications = applications.filter(status='UNDER_REVIEW').count()
        interview_applications = applications.filter(status='INTERVIEW').count()

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
            'total_applications': total_applications,
            'pending_applications': pending_applications,
            'interview_applications': interview_applications,
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
    recruiter = request.user.recruiter_profile
    recruiter_jobs = Job.objects.filter(posted_by=recruiter).order_by("-posted_date")
    form = CandidateSearchForm(request.GET or None)
    selected_recommended_job_id = (request.GET.get("recommended_job_id") or "").strip()

    profiles = Profile.objects.filter(visibility='open')
    candidate_recommendations = []
    selected_recommended_job = None
    profile_count = 0

    if selected_recommended_job_id:
        selected_recommended_job = recruiter_jobs.filter(pk=selected_recommended_job_id).first()
        if selected_recommended_job is None:
            messages.warning(request, "Please choose a valid job from your postings.")
        else:
            try:
                candidate_recommendations = recommend_profiles_for_job(
                    selected_recommended_job.id,
                    k=int(getattr(settings, "RECOMMENDER_TOP_K", 8)),
                )
                profile_count = len(candidate_recommendations)
            except Exception:  # pragma: no cover - search page should not fail on recommendation errors
                logger.exception(
                    "Failed to load candidate recommendations for job %s",
                    selected_recommended_job.id,
                )
                messages.error(
                    request,
                    "Could not generate candidate recommendations right now. Please try again.",
                )
    elif request.GET and form.is_valid():
        profiles = filter_candidate_profiles(
            skills=form.cleaned_data.get('skills', ''),
            location=form.cleaned_data.get('location', ''),
            company=form.cleaned_data.get('company', ''),
            job_title=form.cleaned_data.get('job_title', ''),
        )
        profile_count = profiles.count()

    has_filter_criteria = bool(
        request.GET.get('skills') or request.GET.get('location')
        or request.GET.get('company') or request.GET.get('job_title')
    )

    template_data = {
        'title': 'Candidate Search',
        'form': form,
        'profiles': profiles,
        'candidate_recommendations': candidate_recommendations,
        'profile_count': profile_count,
        'recruiter_jobs': recruiter_jobs,
        'selected_recommended_job': selected_recommended_job,
        'selected_recommended_job_id': selected_recommended_job_id,
        'has_filter_criteria': has_filter_criteria,
        'saved_search_form': SavedSearchForm(initial={
            'skills': request.GET.get('skills', ''),
            'location': request.GET.get('location', ''),
            'company': request.GET.get('company', ''),
            'job_title': request.GET.get('job_title', ''),
        }),
        'saved_search_count': SavedSearch.objects.filter(recruiter=recruiter).count(),
    }
    return render(request, 'accounts/candidate_search.html', {'template_data': template_data})


@login_required
@user_passes_test(is_recruiter_user)
def save_search(request):
    if request.method != 'POST':
        return redirect('accounts.candidate_search')

    form = SavedSearchForm(request.POST)
    if form.is_valid():
        recruiter = request.user.recruiter_profile
        SavedSearch.objects.create(
            recruiter=recruiter,
            name=form.cleaned_data['name'],
            skills=form.cleaned_data.get('skills', ''),
            location=form.cleaned_data.get('location', ''),
            company=form.cleaned_data.get('company', ''),
            job_title=form.cleaned_data.get('job_title', ''),
        )
        messages.success(request, f'Search "{form.cleaned_data["name"]}" saved successfully.')
    else:
        messages.error(request, 'Please provide a name for your saved search.')

    params = {}
    for key in ['skills', 'location', 'company', 'job_title']:
        val = request.POST.get(key, '').strip()
        if val:
            params[key] = val
    redirect_url = reverse('accounts.candidate_search')
    if params:
        redirect_url += '?' + urlencode(params)
    return redirect(redirect_url)


@login_required
@user_passes_test(is_recruiter_user)
def saved_searches(request):
    recruiter = request.user.recruiter_profile
    searches = SavedSearch.objects.filter(recruiter=recruiter)

    template_data = {
        'title': 'Saved Searches',
        'saved_searches': searches,
    }
    return render(request, 'accounts/saved_searches.html', {'template_data': template_data})


@login_required
@user_passes_test(is_recruiter_user)
def delete_saved_search(request, search_id):
    if request.method != 'POST':
        return redirect('accounts.saved_searches')

    recruiter = request.user.recruiter_profile
    search = SavedSearch.objects.filter(pk=search_id, recruiter=recruiter).first()
    if search:
        search_name = search.name
        search.delete()
        messages.success(request, f'Saved search "{search_name}" deleted.')
    else:
        messages.error(request, 'Saved search not found.')

    return redirect('accounts.saved_searches')


@login_required
@user_passes_test(is_recruiter_user)
def applicant_map(request):
    recruiter = request.user.recruiter_profile
    selected_job_id = (request.GET.get('job_id') or '').strip()
    applicant_map_data = _build_applicant_map_context(recruiter, selected_job_id)

    template_data = {
        'title': 'Applicant Map',
        **applicant_map_data,
    }
    return render(request, 'accounts/applicant_map.html', {'template_data': template_data})


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

@login_required
def edit_recruiter_profile(request):
    if not is_recruiter_user(request.user):
        return HttpResponseForbidden('Only recruiters can edit a recruiter profile.')
    return redirect('accounts.edit_recruiter_profile_section', section='basic')


@login_required
def edit_recruiter_profile_section(request, section):
    if not is_recruiter_user(request.user):
        return HttpResponseForbidden('Only recruiters can edit a recruiter profile.')
    if section not in RECRUITER_PROFILE_SECTION_LABELS:
        return HttpResponseForbidden('Unknown recruiter profile section.')

    recruiter = request.user.recruiter_profile
    template_data = {
        'title': f'Edit {RECRUITER_PROFILE_SECTION_LABELS[section]}',
        'section': section,
        'section_label': RECRUITER_PROFILE_SECTION_LABELS[section],
        'section_labels': RECRUITER_PROFILE_SECTION_LABELS,
        'recruiter': recruiter,
    }

    if section == 'basic':
        form = RecruiterAccountForm(request.POST or None, instance=request.user)
    else:
        form = RecruiterProfileForm(request.POST or None, request.FILES or None, instance=recruiter)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{RECRUITER_PROFILE_SECTION_LABELS[section]} updated.')
        return redirect('accounts.edit_recruiter_profile_section', section=section)

    template_data['form'] = form
    return render(request, 'accounts/edit_recruiter_profile.html', {'template_data': template_data})
