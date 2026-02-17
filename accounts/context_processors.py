from .utils import (
    get_user_role,
    is_administrator,
    is_job_seeker as is_job_seeker_user,
    is_recruiter as is_recruiter_user,
)


def role_context(request):
    """Make user role information available in all templates"""
    is_recruiter = False
    is_job_seeker = False
    is_admin = False
    user_role = None

    if request.user.is_authenticated:
        is_admin = is_administrator(request.user)
        is_recruiter = is_recruiter_user(request.user)
        is_job_seeker = is_job_seeker_user(request.user)
        user_role = get_user_role(request.user)

    return {
        'is_recruiter': is_recruiter,
        'is_job_seeker': is_job_seeker,
        'is_admin': is_admin,
        'user_role': user_role,
    }
