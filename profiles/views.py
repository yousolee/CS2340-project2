from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from applications.models import Application
from django.urls import reverse

from accounts.utils import is_job_seeker
from .forms import (
    AboutProfileForm,
    BasicProfileForm,
    EducationFormSet,
    ExperienceFormSet,
    LinksProfileForm,
    SkillsProfileForm,
)
from .models import Profile

User = get_user_model()

SECTION_LABELS = {
    "basic": "Basic Info",
    "about": "About",
    "skills": "Skills",
    "experience": "Experience",
    "education": "Education",
    "links": "Links",
}

PROFILE_SECTION_FORMS = {
    "basic": BasicProfileForm,
    "about": AboutProfileForm,
    "skills": SkillsProfileForm,
    "links": LinksProfileForm,
}

@login_required
def my_profile(request):
    if not is_job_seeker(request.user):
        return HttpResponseForbidden('Only job seeker accounts can view this page.')
    profile, _ = Profile.objects.get_or_create(user=request.user)
    template_data = {
        "title": "My Profile",
        "profile": profile,
        "experiences": profile.experiences.all(),
        "educations": profile.educations.all(),
    }
    return render(request, "profiles/my_profile.html", {"template_data": template_data})

@login_required
def edit_profile(request):
    if not is_job_seeker(request.user):
        return HttpResponseForbidden('Only job seeker accounts can edit a profile.')
    return redirect("profiles.edit_section", section="basic")


@login_required
def edit_profile_section(request, section):
    if not is_job_seeker(request.user):
        return HttpResponseForbidden('Only job seeker accounts can edit a profile.')
    if section not in SECTION_LABELS:
        raise Http404("Unknown profile section.")

    profile, _ = Profile.objects.get_or_create(user=request.user)
    template_data = {
        "title": f"Edit {SECTION_LABELS[section]}",
        "section": section,
        "section_label": SECTION_LABELS[section],
        "section_labels": SECTION_LABELS,
    }

    if section in PROFILE_SECTION_FORMS:
        form_class = PROFILE_SECTION_FORMS[section]
        form = form_class(request.POST or None, instance=profile, prefix="profile")
        if request.method == "POST" and form.is_valid():
            form.save()
            return redirect("profiles.me")
        template_data["form"] = form
    elif section == "experience":
        experience_formset = ExperienceFormSet(
            request.POST or None, instance=profile, prefix="experience"
        )
        if request.method == "POST" and experience_formset.is_valid():
            experience_formset.save()
            return redirect("profiles.me")
        template_data["experience_formset"] = experience_formset
    else:
        education_formset = EducationFormSet(instance=profile, prefix="education")
        if request.method == "POST":
            education_formset = EducationFormSet(
                request.POST, instance=profile, prefix="education"
            )
            if education_formset.is_valid():
                education_formset.save()
                return redirect("profiles.me")
        template_data["education_formset"] = education_formset

    return render(request, "profiles/edit_profile.html", {"template_data": template_data})

def public_profile(request, username):
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.user != user:
        if profile.visibility == Profile.Visibility.HIDDEN:
            has_application = False
            try:
                has_application = Application.objects.filter(applicant=user, job__posted_by=request.user.recruiter_profile).exists()
            except Exception:
                pass
            if not has_application:
                raise Http404('Profile is not available')          

    template_data = {
        "title": f"{user.username}'s Profile",
        "profile": profile,
        "profile_user": user,
        "experiences": profile.experiences.all(),
        "educations": profile.educations.all(),
    }
    return render(request, "profiles/public_profile.html", {"template_data": template_data})

@login_required
def toggle_visibility(request):
    if not is_job_seeker(request.user):
        return HttpResponseForbidden()
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.visibility == Profile.Visibility.OPEN:
        profile.visibility = Profile.Visibility.HIDDEN
    else:
        profile.visibility = Profile.Visibility.OPEN
    profile.save()
    return redirect(reverse('accounts.dashboard'))