from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache
from .models import CustomUser
import os


class UserAuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.protected_url = reverse('protected')

        self.user_data = {
            'email': 'test@example.com',
            'password': 'securepassword123',
            'role': 'silver',
        }

        self.user = CustomUser.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            role=self.user_data['role']
        )
        cache.clear()

    def test_register_user(self):
        response = self.client.post(self.register_url, {
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'role': 'gold'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(email='newuser@example.com').exists())

    def test_login_user(self):
        response = self.client.post(self.login_url, {
            'username': self.user_data['email'],  # AuthenticationForm uses 'username'
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, 302)

    def test_logout_user(self):
        self.client.login(email=self.user_data['email'], password=self.user_data['password'])
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)

    def test_protected_view_access_authenticated(self):
        self.client.login(email=self.user_data['email'], password=self.user_data['password'])
        response = self.client.get(self.protected_url)
        self.assertContains(response, self.user_data['email'])

    def test_protected_view_access_unauthenticated(self):
        response = self.client.get(self.protected_url)
        self.assertContains(response, "Guest")


class RateLimitTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.protected_url = reverse('protected')
        self.user_gold = CustomUser.objects.create_user(email='gold@example.com', password='1234', role='gold')
        self.user_silver = CustomUser.objects.create_user(email='silver@example.com', password='1234', role='silver')
        self.user_bronze = CustomUser.objects.create_user(email='bronze@example.com', password='1234', role='bronze')

    def simulate_requests(self, user, expected_limit):
        self.client.login(email=user.email, password='1234')
        cache_key = 'rate-limit:127.0.0.1'
        cache.delete(cache_key)

        for i in range(expected_limit):
            response = self.client.get(self.protected_url)
            self.assertEqual(response.status_code, 200, f'Failed at request {i+1} for role {user.role}')

        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 429, f'Rate limit not applied to {user.role} user')

    def test_rate_limit_gold(self):
        self.simulate_requests(self.user_gold, expected_limit=10)

    def test_rate_limit_silver(self):
        self.simulate_requests(self.user_silver, expected_limit=5)

    def test_rate_limit_bronze(self):
        self.simulate_requests(self.user_bronze, expected_limit=2)

    def test_rate_limit_unauthenticated(self):
        cache_key = 'rate-limit:127.0.0.1'
        cache.delete(cache_key)

        # First request should pass
        response1 = self.client.get(self.protected_url)
        self.assertEqual(response1.status_code, 200)

        # Second request should be blocked
        response2 = self.client.get(self.protected_url)
        self.assertEqual(response2.status_code, 429)


class MiddlewareLoggingTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.protected_url = reverse('protected')
        self.log_file = 'requests.log'
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def test_logging_middleware_creates_log_entry(self):
        self.client.get(self.protected_url)
        self.assertTrue(os.path.exists(self.log_file))

        with open(self.log_file, 'r') as f:
            log_data = f.read()
            self.assertIn('/protected', log_data)
this is my test.py file