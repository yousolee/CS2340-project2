from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import Recruiter


class EmailDraftViewTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username='draft_recruiter',
            email='recruiter@example.com',
            password='ComplexPass123!',
        )
        Recruiter.objects.create(user=self.recruiter_user, company_name='Acme')
        self.job_seeker = User.objects.create_user(
            username='draft_candidate',
            email='candidate@example.com',
            password='ComplexPass123!',
        )

    def test_only_recruiters_can_open_email_draft(self):
        self.client.login(username='draft_candidate', password='ComplexPass123!')

        response = self.client.get(
            reverse('messaging.send_email', args=[self.job_seeker.username])
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Only recruiters can send emails.', response.content)

    def test_get_prefills_draft_fields_and_mailto_url(self):
        self.client.login(username='draft_recruiter', password='ComplexPass123!')

        response = self.client.get(
            reverse('messaging.send_email', args=[self.job_seeker.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sender_email'], 'recruiter@example.com')
        self.assertEqual(
            response.context['subject'],
            'Opportunity to connect with draft_recruiter',
        )
        self.assertIn('Hi draft_candidate,', response.context['body'])
        self.assertIn('recruiter@example.com', response.context['body'])
        self.assertNotIn('auto_open_draft', response.context)
        self.assertContains(response, 'Send Email')
        self.assertContains(response, 'Your mail app will only open when you click Send Email.')
        self.assertContains(response, 'mailto:candidate@example.com?subject=')
        self.assertContains(response, 'Open in Gmail')
        self.assertContains(response, 'Open in Outlook Web')
        self.assertIn('https://mail.google.com/mail/?', response.context['gmail_url'])
        self.assertIn('https://outlook.office.com/mail/deeplink/compose?', response.context['outlook_url'])
        self.assertNotContains(response, 'window.location.href =')

    def test_post_refreshes_draft_without_sending_email(self):
        self.client.login(username='draft_recruiter', password='ComplexPass123!')

        response = self.client.post(
            reverse('messaging.send_email', args=[self.job_seeker.username]),
            {
                'subject': 'Interview follow-up',
                'body': 'Can we schedule time next week?',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['subject'], 'Interview follow-up')
        self.assertEqual(response.context['body'], 'Can we schedule time next week?')
        self.assertContains(response, 'mailto:candidate@example.com?subject=Interview%20follow-up')
        self.assertEqual(len(mail.outbox), 0)

    def test_view_shows_warning_when_job_seeker_has_no_email(self):
        self.job_seeker.email = ''
        self.job_seeker.save(update_fields=['email'])
        self.client.login(username='draft_recruiter', password='ComplexPass123!')

        response = self.client.get(
            reverse('messaging.send_email', args=[self.job_seeker.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['no_email'])
        self.assertContains(response, "hasn't added an email address")
