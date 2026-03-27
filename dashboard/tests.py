from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard import views as dashboard_views
from voting.models import Maintainer, Region, Role, Subject, Voting, VotingRecord


class DeleteVotingSecurityTokenTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.create(name='admin')
        self.maintainer = Maintainer.objects.create(
            id_role=self.role,
            name='Admin',
            lastname='User',
            mail='admin@example.com',
            password='hashed',
            is_active=True,
        )
        self.region, _ = Region.objects.get_or_create(
            id=9999,
            defaults={'name': 'Region Test Dashboard'},
        )
        now = timezone.now()
        self.voting = Voting.objects.create(
            title='Votación test',
            description='desc',
            id_region=self.region,
            start_date=now - timedelta(days=2),
            finish_date=now - timedelta(days=1),
        )
        self.subject = Subject.objects.create(
            name='Candidato A',
            description='',
            id_voting=self.voting,
        )
        VotingRecord.objects.create(id_voting=self.voting, id_subject=self.subject)

    def _login_session(self):
        session = self.client.session
        session['maintainer_id'] = self.maintainer.id
        session['maintainer_name'] = 'Admin User'
        session.save()

    def test_delete_voting_requires_token(self):
        self._login_session()
        response = self.client.post(reverse('dashboard:delete_voting', args=[self.voting.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Voting.objects.filter(id=self.voting.id).exists())

    def test_delete_voting_with_expired_token_logs_out(self):
        self._login_session()
        session = self.client.session
        session[dashboard_views.DELETE_VOTING_TOKEN_KEY] = 'abc'
        session[dashboard_views.DELETE_VOTING_TOKEN_EXPIRES_KEY] = (timezone.now() - timedelta(seconds=1)).timestamp()
        session.save()

        response = self.client.post(
            reverse('dashboard:delete_voting', args=[self.voting.id]),
            data={'delete_voting_token': 'abc'},
        )
        self.assertRedirects(response, reverse('dashboard:login'))
        self.assertNotIn('maintainer_id', self.client.session)

    def test_delete_voting_with_valid_token_succeeds(self):
        self._login_session()
        token = 'valid-token'
        session = self.client.session
        session[dashboard_views.DELETE_VOTING_TOKEN_KEY] = token
        session[dashboard_views.DELETE_VOTING_TOKEN_EXPIRES_KEY] = (timezone.now() + timedelta(hours=1)).timestamp()
        session.save()

        response = self.client.post(
            reverse('dashboard:delete_voting', args=[self.voting.id]),
            data={'delete_voting_token': token},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Voting.objects.filter(id=self.voting.id).exists())
