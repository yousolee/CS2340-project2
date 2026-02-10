def role_context(request):
    is_recruiter = False
    if request.user.is_authenticated:
        is_recruiter = hasattr(request.user, 'recruiter_profile')
    return {'is_recruiter': is_recruiter}
