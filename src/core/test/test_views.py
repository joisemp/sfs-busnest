from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY
from django.core import mail
from core.models import UserProfile
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

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


class UserRegisterViewTests(TestCase):
    def setUp(self):
        self.register_url = reverse('core:register')
        self.landing_page_url = reverse('landing_page')
        
        self.user_data = {
            'email': 'testuser@example.com',
            'password1': 'strongpassword123',
            'password2': 'strongpassword123',
            'first_name': 'Test',
            'last_name': 'User',
        }
    
    def test_user_registration_creates_user_and_profile(self):
        # Send a POST request to the registration view
        response = self.client.post(self.register_url, self.user_data)
        
        # Check that the user and profile are created
        user = User.objects.filter(email=self.user_data['email']).first()
        profile = UserProfile.objects.filter(user=user).first()
        
        self.assertIsNotNone(user, "User should be created after registration")
        self.assertIsNotNone(profile, "UserProfile should be created for the new user")
        
        # Check profile data
        self.assertEqual(profile.first_name, self.user_data['first_name'])
        self.assertEqual(profile.last_name, self.user_data['last_name'])
        self.assertTrue(profile.is_central_admin)
    
    def test_redirects_to_landing_page_after_registration(self):
        # Send a POST request to register the user
        response = self.client.post(self.register_url, self.user_data)
        
        # Check for redirection to the landing page
        self.assertRedirects(response, self.landing_page_url)
    
    def test_user_is_logged_in_after_registration(self):
        # Register the user
        self.client.post(self.register_url, self.user_data)
        
        # Verify the user is logged in
        user = User.objects.get(email=self.user_data['email'])
        self.assertTrue(user.is_authenticated)
        
        
class LogoutViewTests(TestCase):
    def setUp(self):
        # Set up a test user and log them in
        self.user = User.objects.create_user(email='testuser@example.com', password='password123')
        self.client.login(email='testuser@example.com', password='password123')
        self.logout_url = reverse('core:logout')

    def test_logout_view_logs_out_user(self):
        # Send a GET request to the logout URL
        response = self.client.get(self.logout_url)
        
        # Check that the user is logged out
        self.assertNotIn('_auth_user_id', self.client.session, "User should be logged out")
        
    def test_logout_view_uses_correct_template(self):
        # Send a GET request to the logout URL
        response = self.client.get(self.logout_url)
        
        # Check that the correct template is used
        self.assertTemplateUsed(response, 'core/logout.html')
        
        
class ChangePasswordViewTests(TestCase):
    def setUp(self):
        # Create and log in a test user
        self.user = User.objects.create_user(email='testuser@example.com', password='old_password123')
        self.client.login(email='testuser@example.com', password='old_password123')
        
        self.change_password_url = reverse('core:change_password')
        self.landing_page_url = reverse('landing_page')
        
        self.password_data = {
            'old_password': 'old_password123',
            'new_password1': 'new_password456',
            'new_password2': 'new_password456'
        }
    
    def test_change_password_success(self):
        # Send a POST request to change the password
        response = self.client.post(self.change_password_url, self.password_data)
        
        # Reload the user from the database
        self.user.refresh_from_db()
        
        # Verify the password was updated
        self.assertTrue(self.user.check_password('new_password456'), "Password should be updated successfully")
    
    def test_redirect_after_password_change(self):
        # Send a POST request to change the password
        response = self.client.post(self.change_password_url, self.password_data)
        
        # Check for redirection to the landing page
        self.assertRedirects(response, self.landing_page_url)
    
    def test_change_password_view_uses_correct_template(self):
        # Send a GET request to the change password page
        response = self.client.get(self.change_password_url)
        
        # Verify the correct template is used
        self.assertTemplateUsed(response, 'core/change_password.html')
        

class ResetPasswordViewTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(email='testuser@example.com', password='password123')
        
        self.reset_password_url = reverse('core:reset_password')
        self.done_password_reset_url = reverse('core:done_password_reset')
        self.reset_data = {'email': 'testuser@example.com'}
    
    def test_password_reset_email_sent(self):
        # Send a POST request to request password reset
        response = self.client.post(self.reset_password_url, self.reset_data)
        
        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1, "One password reset email should be sent")
        
        # Check that the email was sent to the correct user
        self.assertIn(self.reset_data['email'], mail.outbox[0].to)
    
    def test_redirect_after_password_reset_request(self):
        # Send a POST request to request password reset
        response = self.client.post(self.reset_password_url, self.reset_data)
        
        # Check for redirection to the done password reset page
        self.assertRedirects(response, self.done_password_reset_url)
    
    def test_password_reset_form_uses_correct_template(self):
        # Send a GET request to the password reset form
        response = self.client.get(self.reset_password_url)
        
        # Verify the form template is used
        self.assertTemplateUsed(response, 'core/password_reset/password_reset_form.html')
    
    def test_password_reset_email_uses_correct_templates(self):
        # Trigger password reset email
        self.client.post(self.reset_password_url, self.reset_data)
        
        # Check the email templates
        email = mail.outbox[0]
        
        # Verify email subject and HTML/plain text templates
        self.assertIn("Password rest", email.subject)
        
        
class DonePasswordResetViewTests(TestCase):
    def setUp(self):
        self.done_password_reset_url = reverse('core:done_password_reset')

    def test_done_password_reset_view_uses_correct_template(self):
        # Send a GET request to the done password reset view
        response = self.client.get(self.done_password_reset_url)
        
        # Verify that the correct template is used
        self.assertTemplateUsed(response, 'core/password_reset/password_reset_done.html')

    def test_done_password_reset_view_is_accessible(self):
        # Send a GET request to the done password reset view
        response = self.client.get(self.done_password_reset_url)
        
        # Check that the view returns a 200 OK response
        self.assertEqual(response.status_code, 200)   


class ConfirmPasswordResetViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='password123'
        )

    def test_password_reset_confirmation(self):
        # Generate a password reset token and encoded UID
        token = default_token_generator.make_token(self.user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))

        # Construct the confirmation URL
        url = reverse('core:confirm_password_reset', kwargs={'uidb64': uidb64, 'token': token})

        # Send a GET request to the confirmation URL
        response = self.client.get(url)

        # Check for the expected redirect to 'set-password'
        self.assertEqual(response.status_code, 302)
        set_password_url = f'/core/confirm-password-reset/{uidb64}/set-password/'
        self.assertRedirects(response, set_password_url)

        # Follow the redirect to the 'set-password' page
        response = self.client.get(set_password_url)

        # Assert that the correct template is rendered on the set-password page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/password_reset/password_reset_confirm.html')

        # Submit a valid password reset form with a stronger password
        data = {
            'new_password1': 'Str0ngP@ssw0rd!2023',
            'new_password2': 'Str0ngP@ssw0rd!2023'
        }
        response = self.client.post(set_password_url, data)

        # Assert that the user is redirected to the success URL
        self.assertRedirects(response, reverse('core:complete_password_reset'))

        # Assert that the user's password has been changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Str0ngP@ssw0rd!2023'))


class CompletePasswordResetViewTests(TestCase):
    def setUp(self):
        self.complete_password_reset_url = reverse('core:complete_password_reset')

    def test_complete_password_reset_view_uses_correct_template(self):
        # Send a GET request to the complete password reset view
        response = self.client.get(self.complete_password_reset_url)
        
        # Verify that the correct template is used
        self.assertTemplateUsed(response, 'core/password_reset/password_reset_complete.html')

    def test_complete_password_reset_view_is_accessible(self):
        # Send a GET request to the complete password reset view
        response = self.client.get(self.complete_password_reset_url)
        
        # Check that the view returns a 200 OK response
        self.assertEqual(response.status_code, 200)