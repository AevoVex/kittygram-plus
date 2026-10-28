import unittest
from django.apps import apps
from django.conf import settings

if not apps.is_installed('lessons'):
    raise unittest.SkipTest('Run lessons with --settings=config.lesson_settings')

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from .models import Cat


class LessonTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('learner', password='Learning-42!')
        cls.token = Token.objects.create(user=cls.user)

    def setUp(self):
        # Works both with anonymous lessons and the token-protected lesson mode.
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.data = {'name': 'Леопольд', 'color': 'Рыжий', 'birth_year': 1975}

    def test_initial_function_create_list_and_errors(self):
        url = '/functions/cats/'
        self.assertEqual(self.client.get(url).data, [])
        response = self.client.post(url, self.data)
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('id', response.data)
        self.assertEqual(self.client.get(url).data[0]['name'], self.data['name'])
        self.assertEqual(self.client.post(url, {**self.data, 'birth_year': '10.2020'}).status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_function_detail_crud(self):
        cat = Cat.objects.create(**self.data)
        url = f'/functions/cats/{cat.pk}/'
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.patch(url, {'color': 'Белый'}).status_code, 200)
        self.assertEqual(self.client.put(url, self.data).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_bulk_create_and_atomic_validation(self):
        response = self.client.post('/bulk/cats/', [self.data, {**self.data, 'name': 'Мурка'}])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Cat.objects.count(), 2)
        self.assertEqual(self.client.post('/bulk/cats/', [self.data, {'name': 'Invalid'}]).status_code, 400)
        self.assertEqual(Cat.objects.count(), 2)
        self.assertEqual(self.client.post('/bulk/cats/', self.data).status_code, 400)

    def test_apiview_and_generic_list_create(self):
        for url in ['/apiview/cats/', '/generics/cats/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, self.data).status_code, 201)
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_generic_detail_crud(self):
        cat = Cat.objects.create(**self.data)
        url = f'/generics/cats/{cat.pk}/'
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.patch(url, {'color': 'Белый'}).status_code, 200)
        self.assertEqual(self.client.put(url, self.data).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_owner_relations(self):
        owner = self.client.post('/owners/', {'first_name': 'Theodor', 'last_name': 'Voland'})
        self.assertEqual(owner.status_code, 201)
        response = self.client.post('/cats/', {**self.data, 'owner_id': owner.data['id']})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['owner'], 'Theodor Voland')
        self.assertEqual(self.client.get(f'/owners/{owner.data["id"]}/').data['cats'], ['Леопольд'])
        self.assertEqual(self.client.patch(f'/cats/{response.data["id"]}/', {'color': 'Чёрный'}).status_code, 200)

    def test_unknown_birth_year(self):
        response = self.client.post('/cats/', {'name': 'Кот', 'color': 'Серый'})
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data['age'])

    def test_hex_color_conversion_and_bad_input(self):
        response = self.client.post('/hex-cats/', {**self.data, 'color': '#228B22'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['color'], 'forestgreen')
        self.assertEqual(Cat.objects.get(pk=response.data['id']).color, 'forestgreen')
        for color in ['#123456', 'not-a-color', 42, [], None]:
            with self.subTest(color=color):
                self.assertEqual(self.client.post('/hex-cats/', {**self.data, 'color': color}).status_code, 400)

    def test_base_viewset_read_only(self):
        cat = Cat.objects.create(**self.data)
        self.assertEqual(self.client.get('/readonly-cats/').status_code, 200)
        self.assertEqual(self.client.get(f'/readonly-cats/{cat.pk}/').status_code, 200)
        self.assertEqual(self.client.post('/readonly-cats/', self.data).status_code, 405)

    def test_token_endpoint(self):
        self.client.credentials()
        token_mode = 'rest_framework.permissions.IsAuthenticated' in settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']
        self.assertEqual(self.client.get('/cats/').status_code, 401 if token_mode else 200)
        response = self.client.post('/api-token-auth/', {'username': 'learner', 'password': 'Learning-42!'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['token'], self.token.key)
