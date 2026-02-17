from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import is_job_seeker, is_recruiter
from jobs.models import Job

from .forms import ApplicationFilterForm, ApplicationForm
from .models import Application, ApplicationEvent, Notification

STATUS_TRANSITIONS = {
    Application.Status.UNDER_REVIEW: {
        "move_to_interview": (
            Application.Status.INTERVIEW,
            "Recruiter moved the application to interview.",
        ),
        "reject": (Application.Status.CLOSED_REJECTED, None),
    },
    Application.Status.INTERVIEW: {
        "move_to_offer": (
            Application.Status.OFFER,
            "Recruiter moved the application to offer.",
        ),
        "reject": (Application.Status.CLOSED_REJECTED, None),
    },
    Application.Status.OFFER: {
        "close_accepted": (
            Application.Status.CLOSED_ACCEPTED,
            "Recruiter marked the application as accepted.",
        ),
        "reject": (Application.Status.CLOSED_REJECTED, None),
    },
}


def _is_recruiter_for_application(user, application):
    return (
        is_recruiter(user)
        and application.job.posted_by_id is not None
        and application.job.posted_by.user_id == user.id
    )


def _add_status_event(application, actor, message, new_status):
    ApplicationEvent.objects.create(
        application=application,
        actor=actor,
        message=message,
        new_status=new_status,
    )


def _notify_applicant_status_change(application, actor, previous_status, message):
    Notification.objects.create(
        recipient=application.applicant,
        actor=actor,
        verb="application_status_changed",
        application=application,
        data={
            "job_id": application.job_id,
            "job_title": application.job.title,
            "previous_status": previous_status,
            "new_status": application.status,
            "message": message,
        },
    )


def _transition_application(application, actor, new_status, message):
    previous_status = application.status
    if previous_status == new_status:
        return

    application.status = new_status
    if actor and is_recruiter(actor):
        application.reviewed_by = actor
    application.save()
    _add_status_event(application, actor, message, new_status)
    _notify_applicant_status_change(application, actor, previous_status, message)


@login_required
def apply_for_job(request, job_id):
    if not is_job_seeker(request.user):
        return HttpResponseForbidden("Only job seeker accounts can apply to jobs.")

    job = get_object_or_404(Job, pk=job_id)
    existing = Application.objects.filter(job=job, applicant=request.user).first()
    if existing:
        return redirect("applications:detail", pk=existing.pk)

    if request.method == "POST":
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            app = form.save(commit=False)
            app.job = job
            app.applicant = request.user
            app.status = Application.Status.APPLIED
            app.save()
            _add_status_event(
                app,
                request.user,
                "Application submitted by the job seeker.",
                Application.Status.APPLIED,
            )

            recruiter = job.posted_by.user if job.posted_by else None
            if recruiter:
                Notification.objects.create(
                    recipient=recruiter,
                    actor=request.user,
                    verb="application_received",
                    application=app,
                    data={
                        "job_id": job.pk,
                        "job_title": job.title,
                        "applicant": request.user.username,
                    },
                )
            return redirect("applications:detail", pk=app.pk)
    else:
        form = ApplicationForm()

    return render(request, "applications/application_form.html", {"form": form, "job": job})


@login_required
def application_detail(request, pk):
    app = get_object_or_404(Application.objects.select_related("job", "applicant"), pk=pk)
    user_is_recruiter_for_job = _is_recruiter_for_application(request.user, app)
    user_is_applicant = app.applicant_id == request.user.id
    if not (user_is_recruiter_for_job or user_is_applicant):
        return HttpResponseForbidden("You do not have permission to view this application.")

    if user_is_recruiter_for_job and app.status == Application.Status.APPLIED:
        _transition_application(
            app,
            request.user,
            Application.Status.UNDER_REVIEW,
            "Recruiter started reviewing the application.",
        )

    Notification.objects.filter(
        recipient=request.user,
        application=app,
        is_read=False,
    ).update(is_read=True)

    next_action_by_status = {
        Application.Status.UNDER_REVIEW: ("move_to_interview", "Move to Interview"),
        Application.Status.INTERVIEW: ("move_to_offer", "Move to Offer"),
        Application.Status.OFFER: ("close_accepted", "Close as Accepted"),
    }
    next_action = next_action_by_status.get(app.status)
    can_recruiter_manage = user_is_recruiter_for_job and app.status in STATUS_TRANSITIONS
    status_labels = dict(Application.Status.choices)
    timeline_events = list(
        app.events.filter(new_status__isnull=False).select_related("actor").order_by("created_at")
    )
    timeline_nodes = [
        {
            "status": event.new_status,
            "label": status_labels.get(event.new_status, "Update"),
            "message": event.message,
            "actor": event.actor.username if event.actor else "system",
            "created_at": event.created_at,
        }
        for event in timeline_events
    ]
    has_applied_node = any(
        node["status"] == Application.Status.APPLIED for node in timeline_nodes
    )
    if not has_applied_node:
        timeline_nodes.insert(
            0,
            {
                "status": Application.Status.APPLIED,
                "label": status_labels.get(
                    Application.Status.APPLIED, Application.Status.APPLIED
                ),
                "message": "Application submitted by the job seeker.",
                "actor": app.applicant.username,
                "created_at": app.created_at,
            },
        )

    template_data = {
        "application": app,
        "user_is_recruiter_for_job": user_is_recruiter_for_job,
        "user_is_applicant": user_is_applicant,
        "can_recruiter_manage": can_recruiter_manage,
        "next_action_value": next_action[0] if next_action else None,
        "next_action_label": next_action[1] if next_action else None,
        "timeline_nodes": timeline_nodes,
    }
    return render(request, "applications/application_detail.html", template_data)


@login_required
def update_application_status(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Status updates must use POST.")

    app = get_object_or_404(Application.objects.select_related("job", "applicant"), pk=pk)
    if not _is_recruiter_for_application(request.user, app):
        return HttpResponseForbidden(
            "Only the recruiter who posted this job can update this application."
        )

    action = request.POST.get("action", "").strip()
    allowed_actions = STATUS_TRANSITIONS.get(app.status, {})
    if action not in allowed_actions:
        return HttpResponseForbidden(
            "This status transition is not allowed for the current stage."
        )

    new_status, default_message = allowed_actions[action]
    if action == "reject":
        rejection_note = request.POST.get("rejection_note", "").strip()
        if not rejection_note:
            messages.error(request, "A rejection note is required.")
            return redirect("applications:detail", pk=app.pk)
        message = f"Application rejected: {rejection_note}"
    else:
        custom_message = request.POST.get("status_message", "").strip()
        message = custom_message or default_message

    _transition_application(app, request.user, new_status, message)
    messages.success(request, f"Application moved to {app.get_status_display()}.")
    return redirect("applications:detail", pk=app.pk)


@login_required
def application_list(request):
    recruiter_view = is_recruiter(request.user)
    seeker_view = is_job_seeker(request.user)

    if recruiter_view:
        apps = Application.objects.filter(job__posted_by__user=request.user)
    elif seeker_view:
        apps = Application.objects.filter(applicant=request.user)
    else:
        return HttpResponseForbidden(
            "Only recruiter or job seeker accounts can view applications."
        )

    job_choices = None
    if recruiter_view:
        job_choices = [
            (str(job_id), title)
            for job_id, title in Job.objects.filter(posted_by__user=request.user).values_list(
                "id", "title"
            )
        ]

    filter_form = ApplicationFilterForm(request.GET or None, job_choices=job_choices)
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get("status")
        date_from = filter_form.cleaned_data.get("date_from")
        date_to = filter_form.cleaned_data.get("date_to")
        selected_job = filter_form.cleaned_data.get("job")

        if status:
            apps = apps.filter(status=status)
        if date_from:
            apps = apps.filter(created_at__date__gte=date_from)
        if date_to:
            apps = apps.filter(created_at__date__lte=date_to)
        if recruiter_view and selected_job:
            apps = apps.filter(job_id=selected_job)

    apps = apps.select_related("job", "applicant").order_by("-created_at")

    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
        application_id__in=apps.values("id"),
    ).update(is_read=True)

    return render(
        request,
        "applications/application_list.html",
        {
            "applications": apps,
            "filter_form": filter_form,
            "recruiter_view": recruiter_view,
        },
    )
