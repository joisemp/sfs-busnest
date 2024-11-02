from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY

User = get_user_model()

class LoginViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user
        cls.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123'
        )

    def test_login_success(self):
        # Define the login URL
        login_url = reverse('core:login')

        # Simulate a login post request with correct credentials
        response = self.client.post(login_url, {
            'username': 'testuser@example.com',
            'password': 'testpassword123'
        })

        # Check if it redirects to 'landing_page'
        self.assertRedirects(response, reverse('landing_page'))

        # Check if the user is authenticated by inspecting the session
        self.assertIn(SESSION_KEY, self.client.session)

    def test_login_failure(self):
        # Define the login URL
        login_url = reverse('core:login')

        # Simulate a login post request with incorrect credentials
        response = self.client.post(login_url, {
            'username': 'testuser@example.com',
            'password': 'wrongpassword'
        })

        # Check that it does not redirect (stays on the login page)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/login.html')
        self.assertContains(response, "Please enter a correct email address and password. Note that both fields may be case-sensitive.")
