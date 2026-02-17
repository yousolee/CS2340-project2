from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from applications.models import Application, Notification
from jobs.models import Job
from .models import Recruiter
from profiles.models import Profile


class SignupRoleTests(TestCase):
    def test_signup_as_recruiter_creates_recruiter_profile(self):
        response = self.client.post(
            reverse('accounts.signup'),
            {
                'username': 'recruiter_user',
                'password1': 'ComplexPass123!',
                'password2': 'ComplexPass123!',
                'account_type': 'recruiter',
                'company_name': 'Acme Hiring',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Recruiter.objects.filter(user__username='recruiter_user').exists())
        self.assertEqual(
            Profile.objects.get(user__username='recruiter_user').role,
            Profile.Role.RECRUITER,
        )

    def test_signup_as_job_seeker_sets_job_seeker_profile_role(self):
        response = self.client.post(
            reverse('accounts.signup'),
            {
                'username': 'seeker_user',
                'password1': 'ComplexPass123!',
                'password2': 'ComplexPass123!',
                'account_type': 'job_seeker',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Recruiter.objects.filter(user__username='seeker_user').exists())
        self.assertEqual(
            Profile.objects.get(user__username='seeker_user').role,
            Profile.Role.JOB_SEEKER,
        )


class RoleBasedScreenTests(TestCase):
    def test_recruiter_login_redirects_to_recruiter_dashboard(self):
        user = User.objects.create_user(username='recruiter_login', password='ComplexPass123!')
        Recruiter.objects.create(user=user, company_name='Acme')

        response = self.client.post(
            reverse('accounts.login'),
            {'username': 'recruiter_login', 'password': 'ComplexPass123!'},
        )

        self.assertRedirects(response, reverse('accounts.dashboard'))
        dashboard_response = self.client.get(reverse('accounts.dashboard'))
        self.assertContains(dashboard_response, 'Recruiter Dashboard')

    def test_job_seeker_login_redirects_to_job_seeker_dashboard(self):
        User.objects.create_user(username='seeker_login', password='ComplexPass123!')

        response = self.client.post(
            reverse('accounts.login'),
            {'username': 'seeker_login', 'password': 'ComplexPass123!'},
        )

        self.assertRedirects(response, reverse('accounts.dashboard'))
        dashboard_response = self.client.get(reverse('accounts.dashboard'))
        self.assertContains(dashboard_response, 'Job Seeker Dashboard')


class DashboardNotificationTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username='notify_recruiter',
            password='ComplexPass123!',
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company_name='Acme',
        )
        self.seeker_user = User.objects.create_user(
            username='notify_seeker',
            password='ComplexPass123!',
        )
        self.job = Job.objects.create(
            title='Backend Engineer',
            company='Acme',
            location='Atlanta, GA',
            description='Build APIs',
            skills='Python, Django',
            mode='hybrid',
            posted_by=self.recruiter,
        )
        self.application = Application.objects.create(
            job=self.job,
            applicant=self.seeker_user,
            status=Application.Status.APPLIED,
        )

    def test_recruiter_dashboard_shows_and_marks_notifications_read(self):
        notification = Notification.objects.create(
            recipient=self.recruiter_user,
            actor=self.seeker_user,
            verb='application_received',
            application=self.application,
            data={'applicant': self.seeker_user.username, 'job_title': self.job.title},
        )
        self.client.login(username='notify_recruiter', password='ComplexPass123!')
        response = self.client.get(reverse('accounts.dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Notifications')
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_job_seeker_dashboard_shows_unread_notification_until_opened(self):
        notification = Notification.objects.create(
            recipient=self.seeker_user,
            actor=self.recruiter_user,
            verb='application_status_changed',
            application=self.application,
            data={
                'previous_status': Application.Status.APPLIED,
                'new_status': Application.Status.UNDER_REVIEW,
            },
        )
        self.client.login(username='notify_seeker', password='ComplexPass123!')
        response = self.client.get(reverse('accounts.dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Notifications')
        self.assertContains(response, 'unread notification')
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

        self.client.get(reverse('applications:detail', kwargs={'pk': self.application.pk}))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
