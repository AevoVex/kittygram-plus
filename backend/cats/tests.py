import datetime as dt
import unittest
from django.conf import settings

if settings.ROOT_URLCONF == 'lessons.urls':
    raise unittest.SkipTest('Run final API tests with config.settings')

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Achievement, AchievementCat, Cat


class CatAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('owner', password='Owner-42-strong!')
        cls.other = get_user_model().objects.create_user('other', password='Other-42-strong!')
        cls.admin = get_user_model().objects.create_user('staff', is_staff=True)
        cls.year = dt.date.today().year
        cls.cat = Cat.objects.create(name='Барсик', color='White', birth_year=cls.year - 2, owner=cls.owner)

    def login(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')

    def setUp(self):
        self.login(self.owner)
        self.url = f'/cats/{self.cat.pk}/'
        self.payload = {'name': 'Мурка', 'color': 'Black', 'birth_year': self.year - 1}

    def test_registration_login_refresh_verify_and_me(self):
        self.client.credentials()
        credentials = {'username': 'newuser', 'password': 'Long-New-User-82!'}
        response = self.client.post('/auth/users/', credentials)
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        user = get_user_model().objects.get(username='newuser')
        self.assertTrue(user.check_password(credentials['password']))
        token = self.client.post('/auth/jwt/create/', credentials)
        self.assertEqual(token.status_code, 200)
        self.assertEqual(self.client.post('/auth/jwt/verify/', {'token': token.data['access']}).status_code, 200)
        refreshed = self.client.post('/auth/jwt/refresh/', {'refresh': token.data['refresh']})
        self.assertEqual(refreshed.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refreshed.data["access"]}')
        self.assertEqual(self.client.get('/auth/users/me/').data['username'], 'newuser')

    def test_registration_rejects_weak_password_and_duplicate_username(self):
        self.client.credentials()
        self.assertEqual(self.client.post('/auth/users/', {'username': 'new', 'password': '123'}).status_code, 400)
        self.assertEqual(self.client.post('/auth/users/', {'username': 'owner', 'password': 'Strong-22-password!'}).status_code, 400)

    def test_invalid_login_and_refresh(self):
        self.client.credentials()
        self.assertEqual(self.client.post('/auth/jwt/create/', {'username': 'owner', 'password': 'wrong'}).status_code, 401)
        self.assertEqual(self.client.post('/auth/jwt/refresh/', {'refresh': 'invalid'}).status_code, 401)

    def test_anonymous_bad_and_expired_tokens(self):
        self.client.credentials()
        for url in ['/cats/', self.url, '/users/', '/achievements/', '/mycats/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid')
        self.assertEqual(self.client.get('/cats/').status_code, 401)
        token = RefreshToken.for_user(self.owner).access_token
        token.set_exp(lifetime=dt.timedelta(seconds=-1))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(self.client.get('/cats/').status_code, 401)

    def test_list_short_detail_full(self):
        response = self.client.get('/cats/')
        cats = response.data.get('results', response.data)
        self.assertEqual(set(cats[0]), {'id', 'name', 'color'})
        response = self.client.get(self.url)
        self.assertEqual(response.data['age'], 2)
        self.assertEqual(response.data['owner'], self.owner.pk)
        self.assertEqual(response.data['achievements'], [])

    def test_create_owner_cannot_be_forged(self):
        response = self.client.post('/cats/', {**self.payload, 'owner': self.other.pk})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['owner'], self.owner.pk)
        self.assertEqual(response.data['age'], 1)

    def test_create_with_nested_achievements_reuses_names(self):
        items = [{'achievement_name': 'Уронил ёлку'}, {'achievement_name': 'Уронил ёлку'}]
        response = self.client.post('/cats/', {**self.payload, 'achievements': items})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data['achievements']), 1)
        self.assertEqual(Achievement.objects.count(), 1)
        self.assertEqual(AchievementCat.objects.count(), 1)
        self.assertEqual(self.client.post('/cats/', {**self.payload, 'name': 'Другой', 'achievements': items}).status_code, 201)
        self.assertEqual(Achievement.objects.count(), 1)

    def test_nested_update_omit_preserve_replace_and_clear(self):
        item = {'achievement_name': 'Спит'}
        self.assertEqual(self.client.patch(self.url, {'achievements': [item]}).status_code, 200)
        self.assertEqual(len(self.client.patch(self.url, {'color': 'Gray'}).data['achievements']), 1)
        replaced = self.client.put(self.url, {**self.payload, 'achievements': [{'achievement_name': 'Бегает'}]})
        self.assertEqual(replaced.status_code, 200, replaced.data)
        self.assertEqual(replaced.data['achievements'][0]['achievement_name'], 'Бегает')
        self.assertEqual(self.client.patch(self.url, {'achievements': []}).data['achievements'], [])

    def test_invalid_nested_data_does_not_create_cat_or_achievement(self):
        response = self.client.post('/cats/', {**self.payload, 'achievements': [{'achievement_name': 'OK'}, {}]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Cat.objects.count(), 1)
        self.assertEqual(Achievement.objects.count(), 0)

    def test_invalid_birth_year_boundaries(self):
        for year in [self.year + 1, self.year - 40, 20, '2020.5', None]:
            with self.subTest(year=year):
                self.assertEqual(self.client.post('/cats/', {**self.payload, 'birth_year': year}).status_code, 400)
        for age in [0, 39]:
            self.assertEqual(self.client.post('/cats/', {**self.payload, 'name': f'Возраст{age}', 'birth_year': self.year - age}).status_code, 201)

    def test_invalid_color_name_and_required_fields(self):
        for data in [{}, {**self.payload, 'color': '#123456'}, {**self.payload, 'name': 'x' * 17}, {**self.payload, 'name': 'Black'}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post('/cats/', data).status_code, 400)

    def test_hex_color_is_accepted_and_returned_for_frontend(self):
        response = self.client.post('/cats/', {**self.payload, 'color': '#ffffff'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['color'], '#FFFFFF')

    def test_patch_validates_against_existing_other_field(self):
        self.assertEqual(self.client.patch(self.url, {'name': 'White'}).status_code, 400)
        self.assertEqual(self.client.patch(self.url, {'name': 'Gray'}).status_code, 200)
        self.assertEqual(self.client.patch(self.url, {'color': 'Gray'}).status_code, 400)
        self.assertEqual(self.client.patch(self.url, {'birth_year': self.year}).status_code, 200)

    def test_duplicate_name_per_owner_and_rename(self):
        self.assertEqual(self.client.post('/cats/', {**self.payload, 'name': self.cat.name}).status_code, 400)
        new = self.client.post('/cats/', self.payload)
        self.assertEqual(new.status_code, 201, new.data)
        self.assertEqual(self.client.patch(f'/cats/{new.data["id"]}/', {'name': self.cat.name}).status_code, 400)
        self.assertEqual(self.client.patch(self.url, {'name': self.cat.name}).status_code, 200)
        self.login(self.other)
        self.assertEqual(self.client.post('/cats/', {**self.payload, 'name': self.cat.name}).status_code, 201)

    def test_database_unique_constraints(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cat.objects.create(name=self.cat.name, color='Black', birth_year=self.year, owner=self.owner)
        achievement = Achievement.objects.create(name='Спит')
        AchievementCat.objects.create(cat=self.cat, achievement=achievement)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AchievementCat.objects.create(cat=self.cat, achievement=achievement)

    def test_other_user_cannot_modify_or_delete(self):
        self.login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        for method in ['put', 'patch', 'delete']:
            self.assertEqual(getattr(self.client, method)(self.url, self.payload).status_code, 403)
        self.cat.refresh_from_db()
        self.assertEqual(self.cat.name, 'Барсик')

    def test_update_owner_ignored_and_delete(self):
        response = self.client.patch(self.url, {'owner': self.other.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['owner'], self.owner.pk)
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_recent_white_cats_five_newest(self):
        cats = [Cat.objects.create(name=f'Кот{i}', color='White', birth_year=self.year, owner=self.owner) for i in range(7)]
        Cat.objects.create(name='Чёрный', color='Black', birth_year=self.year, owner=self.owner)
        response = self.client.get('/cats/recent-white-cats/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c['id'] for c in response.data], [c.pk for c in reversed(cats[-5:])])

    def test_light_viewset_only_create_retrieve(self):
        response = self.client.post('/mycats/', self.payload)
        self.assertEqual(response.status_code, 201, response.data)
        url = f'/mycats/{response.data["id"]}/'
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get('/mycats/').status_code, 405)
        for method in ['put', 'patch', 'delete']:
            self.assertEqual(getattr(self.client, method)(url, self.payload).status_code, 405)

    def test_users_read_only_and_no_private_fields(self):
        response = self.client.get(f'/users/{self.owner.pk}/')
        self.assertEqual(response.data['cats'], ['Барсик'])
        self.assertNotIn('password', response.data)
        self.assertNotIn('email', response.data)
        self.assertEqual(self.client.post('/users/', {}).status_code, 405)
        self.assertEqual(self.client.patch(f'/users/{self.other.pk}/', {'username': 'hacked'}).status_code, 405)

    def test_achievement_crud_and_shared_dictionary_protection(self):
        response = self.client.post('/achievements/', {'achievement_name': 'Прыгает'})
        self.assertEqual(response.status_code, 201)
        url = f'/achievements/{response.data["id"]}/'
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post('/achievements/', {'achievement_name': 'Прыгает'}).status_code, 400)
        self.assertEqual(self.client.patch(url, {'achievement_name': 'Лежит'}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.client.patch(url, {'achievement_name': 'Лежит'}).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)
