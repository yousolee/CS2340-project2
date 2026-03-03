from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Recruiter


class HomeIndexTemplateTests(TestCase):
    def test_anonymous_user_sees_job_seeker_homepage(self):
        response = self.client.get(reverse("home.index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/index.html")

    def test_job_seeker_user_sees_job_seeker_homepage(self):
        User.objects.create_user(username="seeker_home", password="ComplexPass123!")
        self.client.login(username="seeker_home", password="ComplexPass123!")

        response = self.client.get(reverse("home.index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/index.html")
        self.assertNotContains(response, "Find Your Next Great Hire")

    def test_recruiter_user_sees_recruiter_homepage(self):
        user = User.objects.create_user(username="recruiter_home", password="ComplexPass123!")
        Recruiter.objects.create(user=user, company_name="Acme")
        self.client.login(username="recruiter_home", password="ComplexPass123!")

        response = self.client.get(reverse("home.index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/recruiter_index.html")
        self.assertContains(response, "Find Your Next Great Hire")
