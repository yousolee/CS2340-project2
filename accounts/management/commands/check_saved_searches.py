import logging

from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode

from accounts.models import SavedSearch
from accounts.utils import filter_candidate_profiles
from applications.models import Notification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check saved candidate searches for new matching profiles and create notifications.'

    def handle(self, *args, **options):
        saved_searches = SavedSearch.objects.select_related('recruiter__user').all()
        self.stdout.write(f'Checking {saved_searches.count()} saved search(es)...')

        total_notifications = 0

        for saved_search in saved_searches:
            new_matches = filter_candidate_profiles(
                skills=saved_search.skills,
                location=saved_search.location,
                company=saved_search.company,
                job_title=saved_search.job_title,
                updated_after=saved_search.last_checked_at,
            )
            match_count = new_matches.count()

            if match_count > 0:
                params = saved_search.get_query_params()
                search_url = reverse('accounts.candidate_search')
                if params:
                    search_url += '?' + urlencode(params)

                Notification.objects.create(
                    recipient=saved_search.recruiter.user,
                    actor=None,
                    verb='saved_search_new_matches',
                    application=None,
                    data={
                        'search_name': saved_search.name,
                        'match_count': match_count,
                        'saved_search_id': saved_search.id,
                        'search_url': search_url,
                    },
                )
                total_notifications += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  "{saved_search.name}" ({saved_search.recruiter.user.username}): '
                        f'{match_count} new match(es)'
                    )
                )

            saved_search.last_checked_at = timezone.now()
            saved_search.save(update_fields=['last_checked_at'])

        self.stdout.write(
            self.style.SUCCESS(f'Done. Created {total_notifications} notification(s).')
        )
