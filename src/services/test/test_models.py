from django.test import TestCase
from django.utils.text import slugify
from core.models import User, UserProfile
from services.models import Institution, Bus


class InstitutionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="password123")
        self.incharge_profile = UserProfile.objects.create(user=self.user)
    
    def test_institution_creation(self):
        institution = Institution.objects.create(
            user=self.user,
            name="Test Institution",
            label="TI",
            contact_no="1234567890",
            email="institution@example.com",
            incharge=self.incharge_profile
        )
        self.assertEqual(institution.name, "Test Institution")
        self.assertEqual(institution.label, "TI")
        self.assertEqual(institution.contact_no, "1234567890")
        self.assertEqual(institution.email, "institution@example.com")
        self.assertEqual(institution.incharge, self.incharge_profile)

    def test_institution_slug_generation(self):
        institution = Institution.objects.create(
            user=self.user,
            name="Test Institution",
            label="TI",
            contact_no="1234567890",
            email="institution2@example.com",
            incharge=self.incharge_profile
        )
        base_slug = slugify(institution.name)
        self.assertTrue(institution.slug.startswith(base_slug))
        self.assertEqual(len(institution.slug), len(base_slug) + 5)

    def test_institution_unique_email(self):
        Institution.objects.create(
            user=self.user,
            name="Institution 1",
            label="Inst1",
            contact_no="1234567890",
            email="unique@example.com",
            incharge=self.incharge_profile
        )
        with self.assertRaises(Exception):
            Institution.objects.create(
                user=self.user,
                name="Institution 2",
                label="Inst2",
                contact_no="0987654321",
                email="unique@example.com",
                incharge=self.incharge_profile
            )

    def test_institution_contact_no_validation(self):
        institution = Institution(
            user=self.user,
            name="Invalid Contact Institution",
            label="ICI",
            contact_no="invalid_number",
            email="invalid_contact@example.com",
            incharge=self.incharge_profile
        )
        with self.assertRaises(Exception):
            institution.full_clean()


class BusModelTest(TestCase):
    def test_bus_creation(self):
        bus = Bus.objects.create(
            label="School Bus",
            bus_no="BUS123"
        )
        self.assertEqual(bus.label, "School Bus")
        self.assertEqual(bus.bus_no, "BUS123")

    def test_bus_slug_generation(self):
        bus = Bus.objects.create(
            label="School Bus",
            bus_no="BUS123"
        )
        base_slug = slugify(bus.bus_no)
        self.assertTrue(bus.slug.startswith(base_slug))
        self.assertEqual(len(bus.slug), len(base_slug) + 5)
