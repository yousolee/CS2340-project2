from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Recruiter


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
