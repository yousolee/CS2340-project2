"""
Utility functions for user role management
"""


def is_administrator(user):
    """Check if user is an administrator"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_recruiter(user):
    """Check if user is a recruiter"""
    return user.is_authenticated and hasattr(user, 'recruiter_profile')


def is_job_seeker(user):
    """Check if user is a job seeker"""
    return user.is_authenticated and hasattr(user, 'profile')


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
