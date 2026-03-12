from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from applications.models import Application, Notification
from jobs.models import Job
from .models import Recruiter, SavedSearch
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


class SavedSearchTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username='search_recruiter', password='ComplexPass123!'
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user, company_name='Acme'
        )
        self.seeker_user = User.objects.create_user(
            username='search_seeker', password='ComplexPass123!'
        )
        self.seeker_profile = self.seeker_user.profile
        self.seeker_profile.skills = 'Python, Django'
        self.seeker_profile.location = 'Atlanta, GA'
        self.seeker_profile.save()

        self.client.login(username='search_recruiter', password='ComplexPass123!')

    def test_save_search_creates_saved_search(self):
        response = self.client.post(reverse('accounts.save_search'), {
            'name': 'Django Devs',
            'skills': 'Python, Django',
            'location': 'Atlanta',
            'company': '',
            'job_title': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SavedSearch.objects.filter(
            recruiter=self.recruiter, name='Django Devs'
        ).exists())

    def test_save_search_requires_name(self):
        response = self.client.post(reverse('accounts.save_search'), {
            'name': '',
            'skills': 'Python',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SavedSearch.objects.count(), 0)

    def test_saved_searches_list_view(self):
        SavedSearch.objects.create(
            recruiter=self.recruiter, name='Test Search',
            skills='Python', location='Atlanta',
        )
        response = self.client.get(reverse('accounts.saved_searches'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Search')

    def test_delete_saved_search(self):
        search = SavedSearch.objects.create(
            recruiter=self.recruiter, name='To Delete', skills='Java',
        )
        response = self.client.post(
            reverse('accounts.delete_saved_search', kwargs={'search_id': search.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SavedSearch.objects.filter(pk=search.id).exists())

    def test_delete_other_recruiter_search_fails(self):
        other_user = User.objects.create_user(
            username='other_recruiter2', password='ComplexPass123!'
        )
        other_recruiter = Recruiter.objects.create(
            user=other_user, company_name='OtherCo'
        )
        search = SavedSearch.objects.create(
            recruiter=other_recruiter, name='Not Mine', skills='Go',
        )
        response = self.client.post(
            reverse('accounts.delete_saved_search', kwargs={'search_id': search.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SavedSearch.objects.filter(pk=search.id).exists())

    def test_candidate_search_shows_save_button_with_filters(self):
        response = self.client.get(
            reverse('accounts.candidate_search'),
            {'skills': 'Python'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Save This Search')

    def test_candidate_search_hides_save_button_without_filters(self):
        response = self.client.get(reverse('accounts.candidate_search'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Save This Search')

    def test_saved_search_get_search_url(self):
        search = SavedSearch.objects.create(
            recruiter=self.recruiter, name='URL Test',
            skills='Python', location='Atlanta',
        )
        url = search.get_search_url()
        self.assertIn('skills=Python', url)
        self.assertIn('location=Atlanta', url)
        self.assertIn('/accounts/candidate-search/', url)

    def test_save_search_redirects_with_filters(self):
        response = self.client.post(reverse('accounts.save_search'), {
            'name': 'Redirect Test',
            'skills': 'React',
            'location': 'NYC',
            'company': '',
            'job_title': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('skills=React', response.url)
        self.assertIn('location=NYC', response.url)


class CheckSavedSearchesCommandTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username='cmd_recruiter', password='ComplexPass123!'
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user, company_name='Acme'
        )

    def test_command_creates_notification_for_new_match(self):
        search = SavedSearch.objects.create(
            recruiter=self.recruiter,
            name='Python Search',
            skills='Python',
        )
        SavedSearch.objects.filter(pk=search.pk).update(
            last_checked_at=timezone.now() - timezone.timedelta(days=1)
        )
        seeker = User.objects.create_user(username='new_seeker', password='ComplexPass123!')
        profile = seeker.profile
        profile.skills = 'Python, Flask'
        profile.save()

        out = StringIO()
        call_command('check_saved_searches', stdout=out)

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.recruiter_user,
                verb='saved_search_new_matches',
            ).exists()
        )

    def test_command_no_notification_when_no_new_matches(self):
        SavedSearch.objects.create(
            recruiter=self.recruiter,
            name='Rare Skill Search',
            skills='COBOL',
        )
        out = StringIO()
        call_command('check_saved_searches', stdout=out)

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.recruiter_user,
                verb='saved_search_new_matches',
            ).exists()
        )

    def test_command_updates_last_checked_at(self):
        search = SavedSearch.objects.create(
            recruiter=self.recruiter,
            name='Timestamp Test',
            skills='Java',
        )
        old_checked = timezone.now() - timezone.timedelta(hours=1)
        SavedSearch.objects.filter(pk=search.pk).update(last_checked_at=old_checked)

        out = StringIO()
        call_command('check_saved_searches', stdout=out)

        search.refresh_from_db()
        self.assertGreater(search.last_checked_at, old_checked)


class ApplicantMapTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username='map_recruiter', password='ComplexPass123!'
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user, company_name='Acme'
        )
        self.seeker_user = User.objects.create_user(
            username='map_seeker', password='ComplexPass123!'
        )
        self.seeker_profile = self.seeker_user.profile
        self.seeker_profile.location = 'Atlanta, GA'
        self.seeker_profile.save()

        self.seeker_user2 = User.objects.create_user(
            username='map_seeker2', password='ComplexPass123!'
        )
        self.seeker_profile2 = self.seeker_user2.profile
        self.seeker_profile2.location = 'Remote'
        self.seeker_profile2.save()

        self.seeker_user3 = User.objects.create_user(
            username='map_seeker3', password='ComplexPass123!'
        )
        self.seeker_profile3 = self.seeker_user3.profile
        self.seeker_profile3.location = ''
        self.seeker_profile3.save()

        self.job = Job.objects.create(
            title='Backend Engineer', company='Acme',
            location='Atlanta, GA', description='Build APIs',
            skills='Python', mode='hybrid', posted_by=self.recruiter,
        )
        self.job2 = Job.objects.create(
            title='Frontend Dev', company='Acme',
            location='NYC', description='Build UIs',
            skills='React', mode='remote', posted_by=self.recruiter,
        )
        Application.objects.create(
            job=self.job, applicant=self.seeker_user,
            status=Application.Status.APPLIED,
        )
        Application.objects.create(
            job=self.job, applicant=self.seeker_user2,
            status=Application.Status.APPLIED,
        )
        Application.objects.create(
            job=self.job, applicant=self.seeker_user3,
            status=Application.Status.APPLIED,
        )
        Application.objects.create(
            job=self.job2, applicant=self.seeker_user,
            status=Application.Status.APPLIED,
        )

        self.client.login(username='map_recruiter', password='ComplexPass123!')

    def test_applicant_map_loads_for_recruiter(self):
        response = self.client.get(reverse('accounts.applicant_map'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'applicant-map')
        self.assertContains(response, 'leaflet')

    def test_applicant_map_with_job_filter(self):
        response = self.client.get(
            reverse('accounts.applicant_map'),
            {'job_id': self.job2.id},
        )
        self.assertEqual(response.status_code, 200)
        template_data = response.context['template_data']
        self.assertEqual(template_data['selected_job'].id, self.job2.id)

    def test_applicant_map_excludes_remote_and_blank(self):
        response = self.client.get(reverse('accounts.applicant_map'))
        template_data = response.context['template_data']
        locations = [d['location'] for d in template_data['location_data']]
        self.assertIn('Atlanta, GA', locations)
        self.assertNotIn('Remote', locations)
        self.assertNotIn('', locations)

    def test_dashboard_includes_applicant_map_data(self):
        response = self.client.get(reverse('accounts.dashboard'))
        self.assertEqual(response.status_code, 200)

        template_data = response.context['template_data']
        self.assertEqual(template_data['total_applicants'], 1)
        self.assertEqual(
            template_data['location_data'],
            [{'location': 'Atlanta, GA', 'count': 1}],
        )
        self.assertContains(response, 'Applicant Map')

    def test_dashboard_applicant_map_with_job_filter(self):
        response = self.client.get(
            reverse('accounts.dashboard'),
            {
                'section': 'candidates',
                'tab': 'applicant-map-tab',
                'job_id': self.job2.id,
            },
        )
        self.assertEqual(response.status_code, 200)

        template_data = response.context['template_data']
        self.assertEqual(template_data['selected_job'].id, self.job2.id)
        self.assertEqual(
            template_data['location_data'],
            [{'location': 'Atlanta, GA', 'count': 1}],
        )
        self.assertContains(response, 'Showing applicants for')

    def test_applicant_map_requires_recruiter_role(self):
        self.client.logout()
        seeker_only = User.objects.create_user(
            username='plain_seeker', password='ComplexPass123!'
        )
        self.client.login(username='plain_seeker', password='ComplexPass123!')
        response = self.client.get(reverse('accounts.applicant_map'))
        self.assertNotEqual(response.status_code, 200)


class RecruiterProfileEditTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username='edit_recruiter',
            password='ComplexPass123!',
            first_name='Old',
            last_name='Name',
            email='old@example.com',
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company_name='Old Company',
        )
        self.job_seeker = User.objects.create_user(
            username='just_seeker',
            password='ComplexPass123!',
        )

    def test_recruiter_profile_root_redirects_to_basic_section(self):
        self.client.login(username='edit_recruiter', password='ComplexPass123!')

        response = self.client.get(reverse('accounts.edit_recruiter_profile'))

        self.assertRedirects(
            response,
            reverse('accounts.edit_recruiter_profile_section', kwargs={'section': 'basic'}),
        )

    def test_non_recruiter_cannot_access_recruiter_profile_editor(self):
        self.client.login(username='just_seeker', password='ComplexPass123!')

        response = self.client.get(reverse('accounts.edit_recruiter_profile'))

        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Only recruiters can edit a recruiter profile.', response.content)

    def test_basic_section_updates_recruiter_user_fields(self):
        self.client.login(username='edit_recruiter', password='ComplexPass123!')

        response = self.client.post(
            reverse('accounts.edit_recruiter_profile_section', kwargs={'section': 'basic'}),
            {
                'first_name': 'Taylor',
                'last_name': 'Recruiter',
                'email': 'taylor@acme.com',
            },
        )

        self.assertRedirects(
            response,
            reverse('accounts.edit_recruiter_profile_section', kwargs={'section': 'basic'}),
        )
        self.recruiter_user.refresh_from_db()
        self.assertEqual(self.recruiter_user.first_name, 'Taylor')
        self.assertEqual(self.recruiter_user.last_name, 'Recruiter')
        self.assertEqual(self.recruiter_user.email, 'taylor@acme.com')

    def test_company_section_updates_recruiter_company_name(self):
        self.client.login(username='edit_recruiter', password='ComplexPass123!')

        response = self.client.post(
            reverse('accounts.edit_recruiter_profile_section', kwargs={'section': 'company'}),
            {
                'company_name': 'Acme Talent',
                'logo-clear': '',
            },
        )

        self.assertRedirects(
            response,
            reverse('accounts.edit_recruiter_profile_section', kwargs={'section': 'company'}),
        )
        self.recruiter.refresh_from_db()
        self.assertEqual(self.recruiter.company_name, 'Acme Talent')
