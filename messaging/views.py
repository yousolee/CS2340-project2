from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.utils import is_recruiter as is_recruiter_check
from .models import Conversation, Message


@login_required
def inbox(request):
    user = request.user
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

    return render(request, 'messaging/inbox.html', {
        'template_data': {'title': 'Messages'},
        'conversations_data': conversations_data,
    })


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    user = request.user

    if user != conversation.recruiter and user != conversation.job_seeker:
        return HttpResponseForbidden('You are not a participant in this conversation.')

    # Mark incoming messages as read
    conversation.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            Message.objects.create(conversation=conversation, sender=user, body=body)
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
        return redirect('messaging.conversation', conversation_id=conversation_id)

    other = conversation.other_participant(user)
    msgs = conversation.messages.select_related('sender')

    return render(request, 'messaging/conversation.html', {
        'template_data': {'title': f'Chat with {other.username}'},
        'conversation': conversation,
        'messages': msgs,
        'other': other,
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
