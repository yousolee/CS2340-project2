from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404, redirect

from .forms import ProfileForm
from .models import Profile

User = get_user_model()

@login_required
def my_profile(request):
    if hasattr(request.user, 'recruiter_profile'):
        return redirect('accounts.dashboard')
    profile, _ = Profile.objects.get_or_create(user=request.user)
    template_data = {'title': 'My Profile', 'profile': profile}
    return render(request, 'profiles/my_profile.html', {'template_data': template_data})

@login_required
def edit_profile(request):
    if hasattr(request.user, 'recruiter_profile'):
        return redirect('accounts.dashboard')
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profiles.me')
    else:
        form = ProfileForm(instance=profile)

    template_data = {'title': 'Edit Profile', 'form': form}
    return render(request, 'profiles/edit_profile.html', {'template_data': template_data})

def public_profile(request, username):
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)
    template_data = {'title': f"{user.username}'s Profile", 'profile': profile, 'profile_user': user}
    return render(request, 'profiles/public_profile.html', {'template_data': template_data})
