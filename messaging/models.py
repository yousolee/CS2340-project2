from django.contrib.auth.models import User
from django.db import models


class Conversation(models.Model):
    recruiter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recruiter_conversations'
    )
    job_seeker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='job_seeker_conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('recruiter', 'job_seeker')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation: {self.recruiter.username} ↔ {self.job_seeker.username}"

    def other_participant(self, user):
        if user == self.recruiter:
            return self.job_seeker
        return self.recruiter

    def unread_count_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.sent_at}"
