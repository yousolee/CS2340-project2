from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Recruiter
from .models import Job


class JobCreatePermissionTests(TestCase):
    def setUp(self):
        self.job_payload = {
            'title': 'Software Engineer',
            'company': 'Acme',
            'location': 'Atlanta, GA',
            'description': 'Build and maintain services',
            'skills': 'Python, Django',
            'min_salary': '100000',
            'max_salary': '140000',
            'mode': 'hybrid',
            'visa_sponsorship': True,
        }

    def test_recruiter_can_create_job(self):
        user = User.objects.create_user(username='recruiter1', password='ComplexPass123!')
        recruiter = Recruiter.objects.create(user=user, company_name='Acme')
        self.client.login(username='recruiter1', password='ComplexPass123!')

        response = self.client.post(reverse('jobs.create'), self.job_payload)

        self.assertEqual(response.status_code, 302)
        job = Job.objects.get(title='Software Engineer')
        self.assertEqual(job.posted_by, recruiter)

    def test_non_recruiter_cannot_create_job(self):
        User.objects.create_user(username='seeker1', password='ComplexPass123!')
        self.client.login(username='seeker1', password='ComplexPass123!')

        response = self.client.post(reverse('jobs.create'), self.job_payload)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Job.objects.count(), 0)


class JobEditPermissionTests(TestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(
            username='recruiter_owner',
            password='ComplexPass123!',
        )
        self.owner_recruiter = Recruiter.objects.create(
            user=self.owner_user,
            company_name='Acme',
        )
        self.other_user = User.objects.create_user(
            username='recruiter_other',
            password='ComplexPass123!',
        )
        self.other_recruiter = Recruiter.objects.create(
            user=self.other_user,
            company_name='Other Corp',
        )
        self.job = Job.objects.create(
            title='Backend Engineer',
            company='Acme',
            location='Atlanta, GA',
            description='Build APIs',
            skills='Python, Django',
            mode='hybrid',
            posted_by=self.owner_recruiter,
        )

    def test_owner_can_edit_job(self):
        self.client.login(username='recruiter_owner', password='ComplexPass123!')
        response = self.client.post(
            reverse('jobs.edit', kwargs={'job_id': self.job.id}),
            {
                'title': 'Senior Backend Engineer',
                'company': 'Acme',
                'location': 'Atlanta, GA',
                'description': 'Build and scale APIs',
                'skills': 'Python, Django, PostgreSQL',
                'min_salary': '130000',
                'max_salary': '170000',
                'mode': 'remote',
                'visa_sponsorship': True,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, 'Senior Backend Engineer')
        self.assertEqual(self.job.mode, 'remote')
        self.assertTrue(self.job.visa_sponsorship)

    def test_non_owner_recruiter_cannot_edit_job(self):
        self.client.login(username='recruiter_other', password='ComplexPass123!')
        response = self.client.post(
            reverse('jobs.edit', kwargs={'job_id': self.job.id}),
            {
                'title': 'Tampered Title',
                'company': 'Acme',
                'location': 'Atlanta, GA',
                'description': 'Build APIs',
                'skills': 'Python, Django',
                'mode': 'hybrid',
                'visa_sponsorship': False,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, 'Backend Engineer')


class JobDetailRecruiterActionTests(TestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(
            username='detail_recruiter_owner',
            password='ComplexPass123!',
        )
        self.owner_recruiter = Recruiter.objects.create(
            user=self.owner_user,
            company_name='Acme',
        )
        self.other_user = User.objects.create_user(
            username='detail_recruiter_other',
            password='ComplexPass123!',
        )
        self.other_recruiter = Recruiter.objects.create(
            user=self.other_user,
            company_name='Other Corp',
        )
        self.job = Job.objects.create(
            title='Backend Engineer',
            company='Acme',
            location='Atlanta, GA',
            description='Build APIs',
            skills='Python, Django',
            mode='hybrid',
            posted_by=self.owner_recruiter,
        )

    def test_owner_sees_top_candidate_search_button(self):
        self.client.login(username='detail_recruiter_owner', password='ComplexPass123!')
        response = self.client.get(reverse('jobs.detail', kwargs={'job_id': self.job.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Search Top Candidates')
        self.assertContains(
            response,
            f"{reverse('accounts.candidate_search')}?recommended_job_id={self.job.id}",
        )

    def test_non_owner_does_not_see_top_candidate_search_button(self):
        self.client.login(username='detail_recruiter_other', password='ComplexPass123!')
        response = self.client.get(reverse('jobs.detail', kwargs={'job_id': self.job.id}))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Search Top Candidates')
