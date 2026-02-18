from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Recruiter
from applications.models import Application
from profiles.models import Experience

from .models import Job, JobDescriptionEmbedding, JobSkillsEmbedding, JobTitleEmbedding
from .recommendations.documents import (
    build_job_description_document,
    build_job_skills_document,
    build_job_title_document,
    build_profile_experience_document,
    build_profile_summary_skills_document,
    build_profile_title_document,
)
from profiles.models import (
    ProfileExperienceEmbedding,
    ProfileSummarySkillsEmbedding,
    ProfileTitleEmbedding,
)
from .recommendations.scoring import (
    PairFeatures,
    compute_fit_score,
    compute_ranking_score,
    embedding_similarity_score,
    fit_band,
    fit_score_to_100,
    mode_location_structured_score,
    recency_boost,
    visa_structured_score,
)
from .recommendations.service import (
    ensure_job_field_embeddings,
    ensure_profile_field_embeddings,
    recommend_jobs_for_profile,
    score_job_fit_for_profile,
)


class DocumentBuilderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="doc_user", password="ComplexPass123!")
        self.profile = self.user.profile
        self.profile.headline = "Backend Engineer"
        self.profile.summary = "I build APIs and data services."
        self.profile.location = "Atlanta, GA"
        self.profile.skills = "Python, Django, SQL"
        self.profile.save()

        Experience.objects.create(
            profile=self.profile,
            company="Acme",
            title="Software Engineer",
            start_date="2024-01-01",
            description="Built backend APIs",
            activities="Mentored interns",
            location="Atlanta, GA",
            location_type="HYBRID",
        )

        self.job = Job.objects.create(
            title="Backend Engineer",
            company="Acme",
            location="Atlanta, GA",
            description="Design and build APIs",
            skills="Python, Django, REST",
            mode="hybrid",
        )

    def test_profile_field_documents_are_targeted(self):
        exp_doc = build_profile_experience_document(self.profile)
        summary_doc = build_profile_summary_skills_document(self.profile)
        title_doc = build_profile_title_document(self.profile)

        self.assertIn("Software Engineer", exp_doc)
        self.assertNotIn("I build APIs and data services.", exp_doc)

        self.assertIn("I build APIs and data services.", summary_doc)
        self.assertIn("python, django, sql", summary_doc)

        self.assertIn("Software Engineer", title_doc)
        self.assertIn("Acme", title_doc)
        self.assertNotIn("Backend Engineer", title_doc)

    def test_job_field_documents_are_targeted(self):
        desc_doc = build_job_description_document(self.job)
        title_doc = build_job_title_document(self.job)
        skills_doc = build_job_skills_document(self.job)

        self.assertIn("Design and build APIs", desc_doc)
        self.assertIn("Backend Engineer", title_doc)
        self.assertIn("python, django, rest", skills_doc)


class FeatureCalculationTests(TestCase):
    def test_embedding_similarity_is_bounded(self):
        self.assertGreaterEqual(embedding_similarity_score([1.0, 0.0], [1.0, 0.0]), 0.0)
        self.assertLessEqual(embedding_similarity_score([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_mode_location_and_visa_structured_rules(self):
        self.assertGreater(mode_location_structured_score("Atlanta", "Seattle", "remote"), 0.7)
        self.assertLess(mode_location_structured_score("Atlanta", "Seattle", "onsite"), 0.4)
        self.assertEqual(visa_structured_score(), 0.5)

    def test_fit_excludes_recency_and_ranking_includes_it(self):
        base_features = PairFeatures(
            exp_desc_embedding=0.9,
            title_embedding=0.8,
            skills_embedding=0.7,
            summary_desc_embedding=0.6,
            mode_location_structured=0.5,
            visa_structured=0.5,
            recency_boost=0.1,
        )
        newer_features = PairFeatures(
            exp_desc_embedding=0.9,
            title_embedding=0.8,
            skills_embedding=0.7,
            summary_desc_embedding=0.6,
            mode_location_structured=0.5,
            visa_structured=0.5,
            recency_boost=1.0,
        )

        fit_a = compute_fit_score(base_features)
        fit_b = compute_fit_score(newer_features)
        self.assertEqual(fit_a, fit_b)

        rank_a = compute_ranking_score(fit_a, base_features.recency_boost)
        rank_b = compute_ranking_score(fit_b, newer_features.recency_boost)
        self.assertLess(rank_a, rank_b)

    def test_fit_score_band_thresholds(self):
        self.assertEqual(fit_band(39), "low")
        self.assertEqual(fit_band(40), "medium")
        self.assertEqual(fit_band(69), "medium")
        self.assertEqual(fit_band(70), "high")
        self.assertEqual(fit_score_to_100(1.2), 100)


class RecommendationServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.recruiter_user = User.objects.create_user(
            username="rec_recruiter", password="ComplexPass123!"
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company_name="Acme",
        )
        self.seeker_user = User.objects.create_user(
            username="rec_seeker", password="ComplexPass123!"
        )
        self.profile = self.seeker_user.profile
        self.profile.headline = "Backend Engineer"
        self.profile.summary = "Python backend engineer with API and data experience"
        self.profile.location = "Atlanta GA"
        self.profile.skills = "Python, Django, REST, PostgreSQL"
        self.profile.save()

        Experience.objects.create(
            profile=self.profile,
            company="Blue Sky",
            title="Software Engineer",
            start_date="2024-01-01",
            description="Built APIs with Python and Django",
            location="Atlanta, GA",
            location_type="HYBRID",
        )

        self.matching_job = Job.objects.create(
            title="Backend Engineer",
            company="Acme",
            location="Atlanta, GA",
            description="Build backend APIs using Python and Django",
            skills="Python, Django, REST",
            mode="hybrid",
            posted_by=self.recruiter,
        )
        self.old_job = Job.objects.create(
            title="Legacy Backend Engineer",
            company="Legacy Co",
            location="Atlanta, GA",
            description="Old backend role",
            skills="Python",
            mode="onsite",
            posted_by=self.recruiter,
        )
        self.old_job.posted_date = timezone.now() - timedelta(days=120)
        self.old_job.save(update_fields=["posted_date"])

    def test_retrieval_uses_experience_by_default_and_fallback_when_sparse(self):
        dense_bundle = ensure_profile_field_embeddings(self.profile)
        self.assertEqual(dense_bundle.retrieval_source, "experience")

        sparse_user = User.objects.create_user(username="sparse", password="ComplexPass123!")
        sparse_profile = sparse_user.profile
        sparse_profile.summary = "Interested in software engineering"
        sparse_profile.skills = "Python"
        sparse_profile.save()

        sparse_bundle = ensure_profile_field_embeddings(sparse_profile)
        self.assertEqual(sparse_bundle.retrieval_source, "summary_skills")

    def test_score_job_fit_returns_v2_component_keys(self):
        result = score_job_fit_for_profile(self.profile.id, self.matching_job.id)

        self.assertGreaterEqual(result.fit_score_raw, 0.0)
        self.assertLessEqual(result.fit_score_raw, 1.0)
        self.assertGreaterEqual(result.fit_score_100, 0)
        self.assertLessEqual(result.fit_score_100, 100)
        self.assertSetEqual(
            set(result.components.keys()),
            {
                "exp_desc_embedding",
                "title_embedding",
                "skills_embedding",
                "summary_desc_embedding",
                "mode_location_structured",
                "visa_structured",
            },
        )

    def test_recommendations_exclude_applied_and_honor_k(self):
        recommendations = recommend_jobs_for_profile(self.profile.id, k=1)
        self.assertLessEqual(len(recommendations), 1)

        Application.objects.create(job=self.matching_job, applicant=self.seeker_user)
        recommendations_after_apply = recommend_jobs_for_profile(self.profile.id, k=8)
        self.assertNotIn(
            self.matching_job.id,
            [item.job.id for item in recommendations_after_apply],
        )

    def test_field_hash_changes_when_source_text_changes(self):
        before = ensure_job_field_embeddings(self.matching_job)
        self.matching_job.description = "Completely new backend requirements"
        self.matching_job.save(update_fields=["description"])
        after = ensure_job_field_embeddings(self.matching_job)

        self.assertNotEqual(before.description_hash, after.description_hash)

    def test_recency_boost_prefers_newer_job(self):
        now = timezone.now()
        new_score = recency_boost(self.matching_job.posted_date, now)
        old_score = recency_boost(self.old_job.posted_date, now)
        self.assertGreater(new_score, old_score)

    def test_score_refreshes_job_embeddings_when_dimension_is_stale(self):
        ensure_profile_field_embeddings(self.profile, force=True)
        ensure_job_field_embeddings(self.matching_job, force=True)

        title_record = JobTitleEmbedding.objects.get(job=self.matching_job)
        title_record.embedding = list(title_record.embedding[:256])
        title_record.save(update_fields=["embedding"])

        result = score_job_fit_for_profile(self.profile.id, self.matching_job.id)

        refreshed = JobTitleEmbedding.objects.get(job=self.matching_job)
        self.assertEqual(len(refreshed.embedding), int(settings.RECOMMENDER_EMBEDDING_DIM))
        self.assertIn("title_embedding", result.components)


class RecommendationViewTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username="view_recruiter", password="ComplexPass123!"
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company_name="Acme",
        )
        self.seeker_user = User.objects.create_user(
            username="view_seeker", password="ComplexPass123!"
        )
        profile = self.seeker_user.profile
        profile.skills = "Python, Django"
        profile.location = "Atlanta, GA"
        profile.summary = "Backend engineering"
        profile.save()

        Experience.objects.create(
            profile=profile,
            company="Acme",
            title="Software Engineer",
            start_date="2024-01-01",
            description="Built APIs",
            location="Atlanta, GA",
            location_type="HYBRID",
        )

        self.job = Job.objects.create(
            title="Python Engineer",
            company="Acme",
            location="Atlanta, GA",
            description="Build APIs",
            skills="Python, Django",
            mode="hybrid",
            posted_by=self.recruiter,
        )

    def test_job_seeker_dashboard_shows_recommendation_scores(self):
        self.client.login(username="view_seeker", password="ComplexPass123!")
        response = self.client.get(reverse("accounts.dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recommended for You")
        self.assertRegex(response.content.decode("utf-8"), r"\b\d{1,3}/100\b")

    def test_job_detail_shows_score_for_job_seeker_only(self):
        self.client.login(username="view_seeker", password="ComplexPass123!")
        seeker_response = self.client.get(
            reverse("jobs.detail", kwargs={"job_id": self.job.id})
        )
        self.assertContains(seeker_response, "Your Match Score")

        self.client.login(username="view_recruiter", password="ComplexPass123!")
        recruiter_response = self.client.get(
            reverse("jobs.detail", kwargs={"job_id": self.job.id})
        )
        self.assertNotContains(recruiter_response, "Your Match Score")


class EmbeddingSignalTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username="signal_recruiter", password="ComplexPass123!"
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company_name="Acme",
        )
        self.seeker_user = User.objects.create_user(
            username="signal_seeker", password="ComplexPass123!"
        )
        self.profile = self.seeker_user.profile

    def test_job_create_populates_all_job_embedding_models(self):
        job = Job.objects.create(
            title="Backend Engineer",
            company="Acme",
            location="Atlanta, GA",
            description="Build backend APIs",
            skills="Python, Django",
            mode="hybrid",
            posted_by=self.recruiter,
        )

        self.assertTrue(JobDescriptionEmbedding.objects.filter(job=job).exists())
        self.assertTrue(JobTitleEmbedding.objects.filter(job=job).exists())
        self.assertTrue(JobSkillsEmbedding.objects.filter(job=job).exists())

    def test_profile_update_refreshes_profile_embedding_hashes(self):
        self.profile.summary = "Initial summary"
        self.profile.skills = "Python"
        self.profile.save()
        before = ProfileSummarySkillsEmbedding.objects.get(profile=self.profile).source_hash

        self.profile.summary = "Updated summary for embedding refresh"
        self.profile.save()
        after = ProfileSummarySkillsEmbedding.objects.get(profile=self.profile).source_hash

        self.assertNotEqual(before, after)
        self.assertTrue(ProfileExperienceEmbedding.objects.filter(profile=self.profile).exists())
        self.assertTrue(ProfileTitleEmbedding.objects.filter(profile=self.profile).exists())
