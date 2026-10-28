import datetime as dt

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cats.models import Cat

from .models import Collection, CollectionCatProposal, CollectionMember


class CollectionAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_user('owner', password='Owner-42-strong!')
        cls.editor = user_model.objects.create_user('editor', password='Editor-42-strong!')
        cls.viewer = user_model.objects.create_user('viewer', password='Viewer-42-strong!')
        cls.outsider = user_model.objects.create_user('outsider', password='Outsider-42-strong!')
        year = dt.date.today().year
        cls.owner_cat = Cat.objects.create(
            name='Мурка', color='White', birth_year=year - 2, owner=cls.owner,
        )
        cls.editor_cat = Cat.objects.create(
            name='Барсик', color='Black', birth_year=year - 3, owner=cls.editor,
        )
        cls.outsider_cat = Cat.objects.create(
            name='Рыжик', color='Ginger', birth_year=year - 1, owner=cls.outsider,
        )

    def login(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}'
        )

    def create_collection(self, title='Коты из приютов'):
        self.login(self.owner)
        response = self.client.post(
            '/api/collections/',
            {'title': title, 'description': 'Питомцы, которым нужен дом'},
        )
        self.assertEqual(response.status_code, 201, response.data)
        return Collection.objects.get(pk=response.data['id'])

    def invite(self, collection, user, role):
        self.login(self.owner)
        return self.client.post(
            f'/api/collections/{collection.pk}/members/',
            {'user_id': user.pk, 'role': role},
        )

    def test_create_collection_creates_owner_membership(self):
        collection = self.create_collection()
        membership = CollectionMember.objects.get(collection=collection, user=self.owner)
        self.assertEqual(membership.role, CollectionMember.Role.OWNER)
        self.assertEqual(collection.owner, self.owner)

    def test_title_is_unique_per_owner_but_not_globally(self):
        self.create_collection()
        response = self.client.post('/api/collections/', {'title': 'Коты из приютов'})
        self.assertEqual(response.status_code, 400)
        self.login(self.editor)
        self.assertEqual(
            self.client.post('/api/collections/', {'title': 'Коты из приютов'}).status_code,
            201,
        )

    def test_list_is_limited_to_member_and_filters_by_role(self):
        collection = self.create_collection()
        self.assertEqual(self.invite(collection, self.editor, 'editor').status_code, 201)
        self.login(self.editor)
        response = self.client.get('/api/collections/?role=editor')
        self.assertEqual(response.status_code, 200)
        entries = response.data.get('results', response.data)
        self.assertEqual([entry['id'] for entry in entries], [collection.pk])
        self.assertEqual(entries[0]['my_role'], 'editor')
        self.assertEqual(self.client.get('/api/collections/?role=bad').status_code, 400)

    def test_only_members_may_read_collection_and_members(self):
        collection = self.create_collection()
        self.login(self.outsider)
        self.assertEqual(self.client.get(f'/api/collections/{collection.pk}/').status_code, 403)
        self.assertEqual(
            self.client.get(f'/api/collections/{collection.pk}/members/').status_code,
            403,
        )

    def test_owner_can_invite_but_editor_cannot(self):
        collection = self.create_collection()
        self.assertEqual(self.invite(collection, self.editor, 'editor').status_code, 201)
        self.login(self.editor)
        self.assertEqual(
            self.client.post(
                f'/api/collections/{collection.pk}/members/',
                {'user_id': self.viewer.pk, 'role': 'viewer'},
            ).status_code,
            403,
        )

    def test_cannot_invite_user_twice_or_with_owner_role(self):
        collection = self.create_collection()
        self.assertEqual(self.invite(collection, self.editor, 'editor').status_code, 201)
        self.assertEqual(self.invite(collection, self.editor, 'viewer').status_code, 400)
        self.assertEqual(self.invite(collection, self.viewer, 'owner').status_code, 400)

    def test_only_owner_can_change_member_role_or_remove_member(self):
        collection = self.create_collection()
        self.invite(collection, self.editor, 'editor')
        self.login(self.editor)
        member_url = f'/api/collections/{collection.pk}/members/{self.editor.pk}/'
        self.assertEqual(self.client.patch(member_url, {'role': 'viewer'}).status_code, 403)
        self.login(self.owner)
        self.assertEqual(self.client.patch(member_url, {'role': 'viewer'}).status_code, 200)
        self.assertEqual(self.client.delete(member_url).status_code, 204)

    def test_owner_membership_cannot_be_changed_or_deleted(self):
        collection = self.create_collection()
        url = f'/api/collections/{collection.pk}/members/{self.owner.pk}/'
        self.assertEqual(self.client.patch(url, {'role': 'viewer'}).status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)

    def test_editor_can_add_only_their_own_cat_and_cannot_duplicate(self):
        collection = self.create_collection()
        self.invite(collection, self.editor, 'editor')
        self.login(self.editor)
        url = f'/api/collections/{collection.pk}/cats/'
        self.assertEqual(self.client.post(url, {'cat_id': self.editor_cat.pk}).status_code, 201)
        self.assertEqual(self.client.post(url, {'cat_id': self.editor_cat.pk}).status_code, 400)
        self.assertEqual(self.client.post(url, {'cat_id': self.outsider_cat.pk}).status_code, 403)

    def test_viewer_cannot_change_cats_but_can_read(self):
        collection = self.create_collection()
        self.invite(collection, self.viewer, 'viewer')
        self.login(self.viewer)
        self.assertEqual(self.client.get(f'/api/collections/{collection.pk}/').status_code, 200)
        self.assertEqual(
            self.client.post(
                f'/api/collections/{collection.pk}/cats/',
                {'cat_id': self.owner_cat.pk},
            ).status_code,
            403,
        )

    def test_editor_can_remove_cat_but_viewer_cannot(self):
        collection = self.create_collection()
        self.invite(collection, self.editor, 'editor')
        self.invite(collection, self.viewer, 'viewer')
        collection.cats.add(self.editor_cat)
        url = f'/api/collections/{collection.pk}/cats/{self.editor_cat.pk}/'
        self.login(self.viewer)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.login(self.editor)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_only_owner_may_update_or_delete_collection(self):
        collection = self.create_collection()
        self.invite(collection, self.editor, 'editor')
        self.login(self.editor)
        url = f'/api/collections/{collection.pk}/'
        self.assertEqual(self.client.patch(url, {'title': 'Новое имя'}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.login(self.owner)
        self.assertEqual(self.client.patch(url, {'title': 'Новое имя'}).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_any_user_can_propose_their_own_cat_without_membership(self):
        collection = self.create_collection()
        self.login(self.outsider)
        response = self.client.post(
            f'/api/collections/{collection.pk}/proposals/',
            {'cat_id': self.outsider_cat.pk},
        )
        self.assertEqual(response.status_code, 201, response.data)
        proposal = CollectionCatProposal.objects.get(pk=response.data['id'])
        self.assertEqual(proposal.status, CollectionCatProposal.Status.PENDING)
        self.assertEqual(proposal.proposer, self.outsider)
        self.assertFalse(collection.cats.filter(pk=self.outsider_cat.pk).exists())

    def test_user_cannot_propose_someone_elses_cat_or_duplicate_proposal(self):
        collection = self.create_collection()
        self.login(self.outsider)
        url = f'/api/collections/{collection.pk}/proposals/'
        self.assertEqual(self.client.post(url, {'cat_id': self.owner_cat.pk}).status_code, 403)
        self.assertEqual(self.client.post(url, {'cat_id': self.outsider_cat.pk}).status_code, 201)
        self.assertEqual(self.client.post(url, {'cat_id': self.outsider_cat.pk}).status_code, 400)

    def test_editor_can_approve_proposal_and_only_managers_can_review(self):
        collection = self.create_collection()
        self.invite(collection, self.editor, 'editor')
        self.login(self.outsider)
        proposal = self.client.post(
            f'/api/collections/{collection.pk}/proposals/',
            {'cat_id': self.outsider_cat.pk},
        ).data
        self.login(self.viewer)
        self.assertEqual(
            self.client.get(f'/api/collections/{collection.pk}/proposals/').status_code,
            403,
        )
        self.login(self.editor)
        response = self.client.post(
            f'/api/collections/{collection.pk}/proposals/{proposal["id"]}/approve/'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'approved')
        self.assertEqual(response.data['reviewed_by'], self.editor.pk)
        self.assertTrue(collection.cats.filter(pk=self.outsider_cat.pk).exists())

    def test_owner_can_reject_pending_proposal_once(self):
        collection = self.create_collection()
        self.login(self.outsider)
        proposal = self.client.post(
            f'/api/collections/{collection.pk}/proposals/',
            {'cat_id': self.outsider_cat.pk},
        ).data
        self.login(self.owner)
        url = f'/api/collections/{collection.pk}/proposals/{proposal["id"]}/reject/'
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertFalse(collection.cats.filter(pk=self.outsider_cat.pk).exists())
        self.assertEqual(self.client.post(url).status_code, 400)

    def test_demo_seed_command_creates_expected_fixture_without_duplicates(self):
        call_command('seed_collaborations_demo')
        user_model = get_user_model()
        owner = user_model.objects.get(username='demo_owner')
        editor = user_model.objects.get(username='demo_editor')
        viewer = user_model.objects.get(username='demo_viewer')
        self.assertEqual(Cat.objects.filter(owner=owner, name__startswith='Демо ').count(), 5)
        self.assertEqual(Cat.objects.filter(owner=editor, name__startswith='Демо ').count(), 5)
        self.assertEqual(Cat.objects.filter(owner=viewer, name__startswith='Демо ').count(), 5)
        collections = Collection.objects.filter(owner=owner)
        self.assertEqual(collections.count(), 2)
        self.assertTrue(all(collection.cats.count() == 5 for collection in collections))
        self.assertEqual(CollectionCatProposal.objects.filter(status='pending').count(), 2)
        call_command('seed_collaborations_demo')
        self.assertEqual(Collection.objects.filter(owner=owner).count(), 2)
        self.assertEqual(CollectionCatProposal.objects.filter(status='pending').count(), 2)
