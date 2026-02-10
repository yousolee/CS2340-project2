from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Education, Experience, Profile


User = get_user_model()


class ProfileModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="password123")
        self.profile = Profile.objects.get(user=self.user)

    def test_experience_rejects_end_date_before_start_date(self):
        experience = Experience(
            profile=self.profile,
            company="Example Corp",
            title="Engineer",
            start_date="2025-06-01",
            end_date="2025-05-01",
        )
        with self.assertRaises(ValidationError):
            experience.full_clean()

    def test_education_rejects_end_date_when_current(self):
        education = Education(
            profile=self.profile,
            school="Georgia Tech",
            degree="MS",
            start_date="2024-08-01",
            end_date="2025-05-01",
            is_current=True,
        )
        with self.assertRaises(ValidationError):
            education.full_clean()

    def test_experience_section_post_saves_and_shows_on_profile_page(self):
        self.client.login(username="tester", password="password123")
        response = self.client.post(
            reverse("profiles.edit_section", kwargs={"section": "experience"}),
            data={
                "experience-TOTAL_FORMS": "1",
                "experience-INITIAL_FORMS": "0",
                "experience-MIN_NUM_FORMS": "0",
                "experience-MAX_NUM_FORMS": "1000",
                "experience-0-company": "Acme Inc",
                "experience-0-title": "Software Engineer",
                "experience-0-employment_type": "FULL_TIME",
                "experience-0-location": "Atlanta, GA",
                "experience-0-location_type": "HYBRID",
                "experience-0-start_date": "2025-01-01",
                "experience-0-end_date": "",
                "experience-0-is_current": "on",
                "experience-0-description": "Built backend APIs.",
                "experience-0-activities": "Mentored interns.",
            },
        )

        self.assertRedirects(response, reverse("profiles.me"))
        self.assertTrue(
            Experience.objects.filter(
                profile=self.profile, company="Acme Inc", title="Software Engineer"
            ).exists()
        )

        profile_response = self.client.get(reverse("profiles.me"))
        self.assertContains(profile_response, "Software Engineer")
