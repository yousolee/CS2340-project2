def role_context(request):
    """Make user role information available in all templates"""
    is_recruiter = False
    is_job_seeker = False
    is_admin = False
    user_role = None

    if request.user.is_authenticated:
        is_admin = request.user.is_staff or request.user.is_superuser
        is_recruiter = hasattr(request.user, 'recruiter_profile')
        is_job_seeker = hasattr(request.user, 'profile')

        # Determine primary role
        if is_admin:
            user_role = 'administrator'
        elif is_recruiter:
            user_role = 'recruiter'
        elif is_job_seeker:
            user_role = 'job_seeker'

    return {
        'is_recruiter': is_recruiter,
        'is_job_seeker': is_job_seeker,
        'is_admin': is_admin,
        'user_role': user_role,
    }
