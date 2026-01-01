from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import UserProfile

User = get_user_model()


# Test User model
class UserModelTests(TestCase):
    def setUp(self):
        # Create a user for testing
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword123"
        )
    
    def test_user_creation(self):
        """Test that a User instance is created with the expected email."""
        user = User.objects.get(email="testuser@example.com")
        self.assertEqual(user.email, "testuser@example.com")
        
    def test_user_email_unique(self):
        """Test that the email field enforces uniqueness."""
        with self.assertRaises(Exception):
            User.objects.create_user(email="testuser@example.com", password="newpassword")

    def test_user_string_representation(self):
        """Test that the string representation of the user is the email."""
        self.assertEqual(str(self.user), "testuser@example.com")


# Test UserProfile model
class UserProfileModelTests(TestCase):
    def setUp(self):
        # Create a user and associated profile
        self.user = User.objects.create_user(
            email="profileuser@example.com",
            password="testpassword123"
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            role=UserProfile.CENTRAL_ADMIN
        )
    
    def test_user_profile_creation(self):
        """Test that a UserProfile instance is created with correct fields."""
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.first_name, "John")
        self.assertEqual(profile.last_name, "Doe")
        self.assertEqual(profile.role, UserProfile.CENTRAL_ADMIN)
        self.assertTrue(profile.is_central_admin)
        self.assertFalse(profile.is_institution_admin)
        self.assertFalse(profile.is_student)

    def test_user_profile_string_representation(self):
        """Test that the string representation of the UserProfile is 'FirstName LastName'."""
        self.assertEqual(str(self.profile), "John Doe")
    
    def test_user_profile_uniqueness(self):
        """Test that only one UserProfile can be created per user."""
        with self.assertRaises(Exception):
            UserProfile.objects.create(user=self.user, first_name="Jane", last_name="Smith")

