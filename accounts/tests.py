from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from applications.models import Application, Notification
from jobs.models import Job
from .models import Recruiter
from profiles.models import Experience, Profile


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


class CandidateSearchRecommendationTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username="candidate_recruiter",
            password="ComplexPass123!",
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company_name="Acme",
        )
        self.other_recruiter_user = User.objects.create_user(
            username="other_recruiter",
            password="ComplexPass123!",
        )
        self.other_recruiter = Recruiter.objects.create(
            user=self.other_recruiter_user,
            company_name="OtherCo",
        )
        self.job = Job.objects.create(
            title="Backend Engineer",
            company="Acme",
            location="Atlanta, GA",
            description="Build backend APIs using Python and Django",
            skills="Python, Django, REST",
            mode="hybrid",
            posted_by=self.recruiter,
        )
        self.other_job = Job.objects.create(
            title="Data Analyst",
            company="OtherCo",
            location="Atlanta, GA",
            description="Analyze reporting data",
            skills="SQL, BI",
            mode="onsite",
            posted_by=self.other_recruiter,
        )
        self.seeker_user = User.objects.create_user(
            username="candidate_seeker",
            password="ComplexPass123!",
        )
        self.seeker_profile = self.seeker_user.profile
        self.seeker_profile.summary = "Backend engineer with Django API experience"
        self.seeker_profile.skills = "Python, Django, REST"
        self.seeker_profile.location = "Atlanta, GA"
        self.seeker_profile.save()
        Experience.objects.create(
            profile=self.seeker_profile,
            company="Blue Sky",
            title="Software Engineer",
            start_date="2024-01-01",
            description="Built APIs with Python and Django",
            location="Atlanta, GA",
            location_type="HYBRID",
        )

        self.client.login(username="candidate_recruiter", password="ComplexPass123!")

    def test_candidate_search_shows_only_recruiter_jobs_in_dropdown(self):
        response = self.client.get(reverse("accounts.candidate_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Engineer")
        self.assertNotContains(response, "Data Analyst")

    def test_candidate_search_recommendations_for_selected_job(self):
        response = self.client.get(
            reverse("accounts.candidate_search"),
            {"recommended_job_id": self.job.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Showing top candidates for")
        self.assertContains(response, self.seeker_user.username)
        self.assertRegex(response.content.decode("utf-8"), r"\b\d{1,3}/100\b")
        self.assertContains(
            response,
            reverse("profiles.public", args=[self.seeker_user.username]),
        )
        self.assertContains(
            response,
            reverse("messaging.start", args=[self.seeker_user.username]),
        )

        template_data = response.context["template_data"]
        self.assertEqual(template_data["selected_recommended_job"].id, self.job.id)
        self.assertGreaterEqual(len(template_data["candidate_recommendations"]), 1)

    def test_candidate_search_rejects_other_recruiter_job_id(self):
        response = self.client.get(
            reverse("accounts.candidate_search"),
            {"recommended_job_id": self.other_job.id},
        )
        self.assertEqual(response.status_code, 200)

        template_data = response.context["template_data"]
        self.assertIsNone(template_data["selected_recommended_job"])
        self.assertEqual(template_data["candidate_recommendations"], [])
