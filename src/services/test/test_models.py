from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from services.models import Institution, UserProfile
from django.utils.text import slugify

User = get_user_model()

class InstitutionModelTest(TestCase):
    def setUp(self):
        # Create a user and user profile for testing
        self.user = User.objects.create_user(email="user@example.com", password="password")
        self.incharge_profile = UserProfile.objects.create(user=self.user)

    def test_create_institution(self):
        institution = Institution.objects.create(
            user=self.user,
            name="Test Institution",
            label="TestLabel",
            contact_no="1234567890",
            email="institution@example.com",
            incharge=self.incharge_profile,
        )
        self.assertEqual(institution.name, "Test Institution")
        self.assertEqual(institution.label, "TestLabel")
        self.assertEqual(institution.contact_no, "1234567890")
        self.assertEqual(institution.email, "institution@example.com")
        self.assertEqual(institution.incharge, self.incharge_profile)
        self.assertIsNotNone(institution.created_at)
        self.assertIsNotNone(institution.updated_at)

    def test_slug_generation_on_create(self):
        institution_name = "Unique Institution"
        expected_slug = slugify(institution_name)
        
        institution = Institution.objects.create(
            user=self.user,
            name=institution_name,
            label="Unique Institution Label",
            contact_no="1234567890",
            email="unique@example.com",
        )

        # Check that the generated slug starts with the expected_slug
        self.assertTrue(
            institution.slug.startswith(expected_slug),
            f"Slug '{institution.slug}' does not start with expected '{expected_slug}'"
        )
        # Check that the slug has the expected format with a short suffix
        self.assertRegex(
            institution.slug,
            rf"^{expected_slug}(-[a-z0-9]{{4}})?$",
            f"Slug '{institution.slug}' does not match expected pattern"
        )

    def test_slug_uniqueness(self):
        institution1 = Institution.objects.create(
            user=self.user,
            name="Duplicate Institution",
            label="Label1",
            contact_no="1234567890",
            email="duplicate1@example.com",
            incharge=self.incharge_profile,
        )
        
        # Create a new User and UserProfile to avoid the unique constraint violation
        new_user = User.objects.create_user(email="newuser@example.com", password="password")
        new_user_profile = UserProfile.objects.create(user=new_user)
        
        # Create a second institution with the same name and new incharge
        institution2 = Institution.objects.create(
            user=new_user,
            name="Duplicate Institution",
            label="Label2",
            contact_no="0987654321",
            email="duplicate2@example.com",
            incharge=new_user_profile,
        )
        
        # Check that slugs are unique
        self.assertNotEqual(institution1.slug, institution2.slug)
        self.assertTrue(institution2.slug.startswith(slugify("Duplicate Institution")))
        
    def test_str_method(self):
        institution = Institution.objects.create(
            user=self.user,
            name="Readable Institution",
            label="ReadLabel",
            contact_no="1234567890",
            email="readable@example.com",
            incharge=self.incharge_profile,
        )
        self.assertEqual(str(institution), "Readable Institution - ReadLabel")

    def test_contact_no_validation(self):
        with self.assertRaises(ValidationError):
            institution = Institution(
                user=self.user,
                name="Invalid Contact",
                label="InvalidLabel",
                contact_no="123",  # Invalid contact number
                email="invalid@example.com",
                incharge=self.incharge_profile,
            )
            institution.full_clean()  # Manually trigger validation

    def test_email_unique_constraint(self):
        Institution.objects.create(
            user=self.user,
            name="Email Institution",
            label="EmailLabel",
            contact_no="1234567890",
            email="uniqueemail@example.com",
            incharge=self.incharge_profile,
        )
        with self.assertRaises(Exception):
            Institution.objects.create(
                user=self.user,
                name="Another Institution",
                label="AnotherLabel",
                contact_no="0987654321",
                email="uniqueemail@example.com",  # Duplicate email
                incharge=self.incharge_profile,
            )
