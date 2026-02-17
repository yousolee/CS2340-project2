from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Recruiter
from jobs.models import Job

from .models import Application, ApplicationEvent, Notification


class ApplicationPermissionTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username='recruiter1',
            password='ComplexPass123!',
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company_name='Acme',
        )
        self.other_recruiter_user = User.objects.create_user(
            username='recruiter2',
            password='ComplexPass123!',
        )
        Recruiter.objects.create(
            user=self.other_recruiter_user,
            company_name='Other',
        )
        self.seeker_user = User.objects.create_user(
            username='seeker1',
            password='ComplexPass123!',
        )
        self.other_seeker_user = User.objects.create_user(
            username='seeker2',
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

    def test_job_seeker_can_apply(self):
        self.client.login(username='seeker1', password='ComplexPass123!')
        response = self.client.post(
            reverse('applications:apply', kwargs={'job_id': self.job.id}),
            {'note': 'I am interested in this role.'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Application.objects.filter(job=self.job, applicant=self.seeker_user).exists()
        )

    def test_recruiter_cannot_apply(self):
        self.client.login(username='recruiter1', password='ComplexPass123!')
        response = self.client.get(
            reverse('applications:apply', kwargs={'job_id': self.job.id})
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Application.objects.count(), 0)

    def test_applicant_and_posting_recruiter_can_view_application_detail(self):
        application = Application.objects.create(
            job=self.job,
            applicant=self.seeker_user,
            note='Applied',
        )

        self.client.login(username='seeker1', password='ComplexPass123!')
        seeker_response = self.client.get(
            reverse('applications:detail', kwargs={'pk': application.pk})
        )
        self.assertEqual(seeker_response.status_code, 200)

        self.client.login(username='recruiter1', password='ComplexPass123!')
        recruiter_response = self.client.get(
            reverse('applications:detail', kwargs={'pk': application.pk})
        )
        self.assertEqual(recruiter_response.status_code, 200)

    def test_unrelated_users_cannot_view_application_detail(self):
        application = Application.objects.create(
            job=self.job,
            applicant=self.seeker_user,
            note='Applied',
        )

        self.client.login(username='seeker2', password='ComplexPass123!')
        other_seeker_response = self.client.get(
            reverse('applications:detail', kwargs={'pk': application.pk})
        )
        self.assertEqual(other_seeker_response.status_code, 403)

        self.client.login(username='recruiter2', password='ComplexPass123!')
        other_recruiter_response = self.client.get(
            reverse('applications:detail', kwargs={'pk': application.pk})
        )
        self.assertEqual(other_recruiter_response.status_code, 403)


class ApplicationWorkflowTests(TestCase):
    def setUp(self):
        self.recruiter_user = User.objects.create_user(
            username='workflow_recruiter',
            password='ComplexPass123!',
        )
        self.recruiter = Recruiter.objects.create(
            user=self.recruiter_user,
            company_name='Acme',
        )
        self.seeker_user = User.objects.create_user(
            username='workflow_seeker',
            password='ComplexPass123!',
        )
        self.job = Job.objects.create(
            title='Data Engineer',
            company='Acme',
            location='Atlanta, GA',
            description='Build data pipelines',
            skills='Python, SQL',
            mode='hybrid',
            posted_by=self.recruiter,
        )
        self.application = Application.objects.create(
            job=self.job,
            applicant=self.seeker_user,
            note='My application note',
            status=Application.Status.APPLIED,
        )

    def test_recruiter_review_moves_applied_to_under_review_and_notifies_seeker(self):
        self.client.login(username='workflow_recruiter', password='ComplexPass123!')
        response = self.client.get(
            reverse('applications:detail', kwargs={'pk': self.application.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.UNDER_REVIEW)
        self.assertTrue(
            ApplicationEvent.objects.filter(
                application=self.application,
                new_status=Application.Status.UNDER_REVIEW,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.seeker_user,
                application=self.application,
                verb='application_status_changed',
            ).exists()
        )

    def test_recruiter_can_progress_application_to_accepted(self):
        self.application.status = Application.Status.UNDER_REVIEW
        self.application.save(update_fields=['status'])
        self.client.login(username='workflow_recruiter', password='ComplexPass123!')

        interview_response = self.client.post(
            reverse('applications:update_status', kwargs={'pk': self.application.pk}),
            {'action': 'move_to_interview'},
        )
        self.assertEqual(interview_response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.INTERVIEW)

        offer_response = self.client.post(
            reverse('applications:update_status', kwargs={'pk': self.application.pk}),
            {'action': 'move_to_offer'},
        )
        self.assertEqual(offer_response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.OFFER)

        accepted_response = self.client.post(
            reverse('applications:update_status', kwargs={'pk': self.application.pk}),
            {'action': 'close_accepted'},
        )
        self.assertEqual(accepted_response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.CLOSED_ACCEPTED)

    def test_recruiter_custom_forward_message_overrides_default_message(self):
        self.application.status = Application.Status.UNDER_REVIEW
        self.application.save(update_fields=['status'])
        self.client.login(username='workflow_recruiter', password='ComplexPass123!')

        custom_message = 'We liked your background and would like to schedule an interview.'
        response = self.client.post(
            reverse('applications:update_status', kwargs={'pk': self.application.pk}),
            {'action': 'move_to_interview', 'status_message': custom_message},
        )
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.INTERVIEW)

        latest_event = ApplicationEvent.objects.filter(
            application=self.application,
            new_status=Application.Status.INTERVIEW,
        ).latest('created_at')
        self.assertEqual(latest_event.message, custom_message)
        latest_notification = Notification.objects.filter(
            recipient=self.seeker_user,
            application=self.application,
            verb='application_status_changed',
        ).latest('created_at')
        self.assertEqual(latest_notification.data.get('message'), custom_message)

    def test_reject_requires_note_and_sets_closed_rejected(self):
        self.application.status = Application.Status.UNDER_REVIEW
        self.application.save(update_fields=['status'])
        self.client.login(username='workflow_recruiter', password='ComplexPass123!')

        missing_note_response = self.client.post(
            reverse('applications:update_status', kwargs={'pk': self.application.pk}),
            {'action': 'reject', 'rejection_note': ''},
        )
        self.assertEqual(missing_note_response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.UNDER_REVIEW)

        reject_response = self.client.post(
            reverse('applications:update_status', kwargs={'pk': self.application.pk}),
            {'action': 'reject', 'rejection_note': 'Missing required backend experience.'},
        )
        self.assertEqual(reject_response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.CLOSED_REJECTED)
        self.assertTrue(
            ApplicationEvent.objects.filter(
                application=self.application,
                new_status=Application.Status.CLOSED_REJECTED,
                message__icontains='Missing required backend experience.',
            ).exists()
        )

    def test_recruiter_does_not_receive_status_change_notifications(self):
        self.application.status = Application.Status.UNDER_REVIEW
        self.application.save(update_fields=['status'])
        self.client.login(username='workflow_recruiter', password='ComplexPass123!')
        self.client.post(
            reverse('applications:update_status', kwargs={'pk': self.application.pk}),
            {'action': 'move_to_interview'},
        )

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.recruiter_user,
                application=self.application,
                verb='application_status_changed',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.seeker_user,
                application=self.application,
                verb='application_status_changed',
            ).exists()
        )

    def test_recruiter_application_list_filters_by_status_and_date(self):
        older_application = Application.objects.create(
            job=self.job,
            applicant=User.objects.create_user(
                username='workflow_other_seeker',
                password='ComplexPass123!',
            ),
            note='Older app',
            status=Application.Status.INTERVIEW,
        )
        Application.objects.filter(pk=older_application.pk).update(
            created_at=timezone.now() - timedelta(days=7)
        )
        self.client.login(username='workflow_recruiter', password='ComplexPass123!')

        response = self.client.get(
            reverse('applications:list'),
            {'status': Application.Status.APPLIED},
        )
        self.assertEqual(response.status_code, 200)
        applications = list(response.context['applications'])
        self.assertEqual(len(applications), 1)
        self.assertEqual(applications[0].pk, self.application.pk)

        today_str = timezone.localdate().isoformat()
        date_response = self.client.get(
            reverse('applications:list'),
            {'date_from': today_str, 'date_to': today_str},
        )
        self.assertEqual(date_response.status_code, 200)
        date_filtered = list(date_response.context['applications'])
        self.assertEqual(len(date_filtered), 1)
        self.assertEqual(date_filtered[0].pk, self.application.pk)

    def test_application_detail_renders_horizontal_timeline(self):
        self.application.status = Application.Status.UNDER_REVIEW
        self.application.save(update_fields=['status'])
        ApplicationEvent.objects.create(
            application=self.application,
            actor=self.recruiter_user,
            message='Recruiter moved the application to interview.',
            new_status=Application.Status.INTERVIEW,
        )
        self.client.login(username='workflow_seeker', password='ComplexPass123!')
        response = self.client.get(
            reverse('applications:detail', kwargs={'pk': self.application.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'status-track')
        self.assertContains(response, 'timeline-dot')
        self.assertContains(response, 'Applied')
