import logging
from urllib.parse import quote, urlencode

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.utils import is_recruiter as is_recruiter_check
from .models import Conversation, Message

logger = logging.getLogger(__name__)


def _notify_recipient(sender, recipient, body, conversation_id, request):
    if not recipient.email:
        return
    sender_name = sender.get_full_name() or sender.username
    try:
        url = request.build_absolute_uri(f'/messages/{conversation_id}/')
        email = EmailMessage(
            subject=f'New message from {sender_name}',
            body=(
                f'Hi {recipient.get_full_name() or recipient.username},\n\n'
                f'{sender_name} sent you a message:\n\n'
                f'"{body}"\n\n'
                f'Reply here: {url}\n\n'
                f'— {sender_name}'
            ),
            from_email=f'{sender_name} <onboarding@resend.dev>',
            to=[recipient.email],
            reply_to=[sender.email] if sender.email else [],
        )
        email.send()
    except Exception:
        logger.exception('Failed to send message notification to %s', recipient.email)


def _default_email_subject(sender_name):
    return f'Opportunity to connect with {sender_name}'


def _default_email_body(sender, recipient):
    sender_name = sender.get_full_name() or sender.username
    recipient_name = recipient.get_full_name() or recipient.username
    sender_email = sender.email or '[Add your email address in your profile before sending.]'
    return (
        f'Hi {recipient_name},\n\n'
        'I came across your profile on JobFinder and wanted to reach out.\n\n'
        'Best,\n'
        f'{sender_name}\n'
        f'{sender_email}'
    )


def _build_mailto_url(recipient_email, subject, body):
    query = urlencode({
        'subject': subject,
        'body': body,
    }, quote_via=quote)
    return f'mailto:{recipient_email}?{query}'


def _build_webmail_draft_urls(recipient_email, subject, body):
    gmail_query = urlencode({
        'view': 'cm',
        'fs': '1',
        'to': recipient_email,
        'su': subject,
        'body': body,
    }, quote_via=quote)
    outlook_query = urlencode({
        'to': recipient_email,
        'subject': subject,
        'body': body,
    }, quote_via=quote)
    return {
        'gmail': f'https://mail.google.com/mail/?{gmail_query}',
        'outlook': f'https://outlook.office.com/mail/deeplink/compose?{outlook_query}',
    }


def get_conversations_data(user):
    if is_recruiter_check(user):
        conversations = Conversation.objects.filter(
            recruiter=user
        ).select_related('job_seeker').prefetch_related('messages')
    else:
        conversations = Conversation.objects.filter(
            job_seeker=user
        ).select_related('recruiter').prefetch_related('messages')

    conversations_data = []
    for convo in conversations:
        other = convo.other_participant(user)
        last_msg = convo.messages.last()
        unread = convo.unread_count_for(user)
        conversations_data.append({
            'conversation': convo,
            'other': other,
            'last_message': last_msg,
            'unread': unread,
        })
    return conversations_data


@login_required
def inbox(request):
    user = request.user
    conversations_data = get_conversations_data(user)

    return render(request, 'messaging/inbox.html', {
        'template_data': {'title': 'Messages'},
        'conversations_data': conversations_data,
        'active_conversation': None,
        'is_recruiter': is_recruiter_check(user),
    })


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    user = request.user

    if user != conversation.recruiter and user != conversation.job_seeker:
        return HttpResponseForbidden('You are not a participant in this conversation.')

    conversation.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            Message.objects.create(conversation=conversation, sender=user, body=body)
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
            _notify_recipient(user, conversation.other_participant(user), body, conversation_id, request)
        return redirect('messaging.conversation', conversation_id=conversation_id)

    other = conversation.other_participant(user)
    msgs = conversation.messages.select_related('sender')
    conversations_data = get_conversations_data(user)

    return render(request, 'messaging/inbox.html', {
        'template_data': {'title': f'Chat with {other.username}'},
        'conversations_data': conversations_data,
        'active_conversation': conversation,
        'messages': msgs,
        'other': other,
        'is_recruiter': is_recruiter_check(user),
    })


@login_required
def start_conversation(request, username):
    if not is_recruiter_check(request.user):
        return HttpResponseForbidden('Only recruiters can start conversations.')

    job_seeker = get_object_or_404(User, username=username)
    conversation, _ = Conversation.objects.get_or_create(
        recruiter=request.user,
        job_seeker=job_seeker,
    )
    return redirect('messaging.conversation', conversation_id=conversation.id)


@login_required
def send_email_to_user(request, username):
    if not is_recruiter_check(request.user):
        return HttpResponseForbidden('Only recruiters can send emails.')

    job_seeker = get_object_or_404(User, username=username)

    if not job_seeker.email:
        return render(request, 'messaging/send_email.html', {
            'template_data': {'title': f'Email {job_seeker.get_full_name() or job_seeker.username}'},
            'job_seeker': job_seeker,
            'no_email': True,
        })

    sender_name = request.user.get_full_name() or request.user.username
    initial_subject = _default_email_subject(sender_name)
    initial_body = _default_email_body(request.user, job_seeker)

    subject = request.POST.get('subject', initial_subject).strip() if request.method == 'POST' else initial_subject
    body = request.POST.get('body', initial_body).strip() if request.method == 'POST' else initial_body
    if not subject:
        subject = initial_subject
    if not body:
        body = initial_body

    mailto_url = _build_mailto_url(job_seeker.email, subject, body)
    webmail_urls = _build_webmail_draft_urls(job_seeker.email, subject, body)

    return render(request, 'messaging/send_email.html', {
        'template_data': {'title': f'Email {job_seeker.get_full_name() or job_seeker.username}'},
        'job_seeker': job_seeker,
        'sender_email': request.user.email,
        'subject': subject,
        'body': body,
        'mailto_url': mailto_url,
        'gmail_url': webmail_urls['gmail'],
        'outlook_url': webmail_urls['outlook'],
    })
