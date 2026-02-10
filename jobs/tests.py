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
