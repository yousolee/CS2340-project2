"""
Utility functions for user role management
"""

from django.core.exceptions import ObjectDoesNotExist

from profiles.models import Profile


def is_administrator(user):
    """Check if user is an administrator"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_recruiter(user):
    """Check if user is a recruiter"""
    return user.is_authenticated and hasattr(user, 'recruiter_profile')


def is_job_seeker(user):
    """Check if user is a job seeker"""
    if not user.is_authenticated or is_administrator(user) or is_recruiter(user):
        return False
    try:
        return user.profile.role == Profile.Role.JOB_SEEKER
    except ObjectDoesNotExist:
        return False


def get_user_role(user):
    """Get the primary role of a user"""
    if not user.is_authenticated:
        return None

    if is_administrator(user):
        return 'administrator'
    elif is_recruiter(user):
        return 'recruiter'
    elif is_job_seeker(user):
        return 'job_seeker'
    return None


def filter_candidate_profiles(skills='', location='', company='', job_title='', updated_after=None):
    """Filter job seeker profiles by the given criteria."""
    from django.db.models import Q

    profiles = (
        Profile.objects.filter(
            role=Profile.Role.JOB_SEEKER,
            visibility=Profile.Visibility.OPEN,
        )
        .select_related('user')
        .prefetch_related('experiences', 'educations')
    )

    if updated_after:
        profiles = profiles.filter(updated_at__gt=updated_after)

    if skills:
        skills_list = [s.strip() for s in skills.split(',')]
        skill_query = Q()
        for skill in skills_list:
            skill_query |= Q(skills__icontains=skill)
        profiles = profiles.filter(skill_query)

    if location:
        profiles = profiles.filter(location__icontains=location)

    if company:
        profiles = profiles.filter(experiences__company__icontains=company).distinct()

    if job_title:
        profiles = profiles.filter(experiences__title__icontains=job_title).distinct()

    return profiles
