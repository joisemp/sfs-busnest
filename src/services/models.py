import random
import string
from django.db import models
from core.models import UserProfile
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model

User = get_user_model()


class Institution(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='institutions')
    name = models.CharField(max_length=200, db_index=True)
    label = models.CharField(max_length=50, unique=True)
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')]
    )
    email = models.EmailField(unique=True, db_index=True)
    slug = models.SlugField(unique=True, db_index=True)
    incharge = models.OneToOneField(UserProfile, null=True, on_delete=models.SET_NULL, related_name='institution')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Automatically generate a slug if it hasn't been set
        if not self.slug:
            base_slug = slugify(self.name)
            # Generate a short alphanumeric code for uniqueness
            def generate_code():
                return ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            slug = f"{base_slug}-{generate_code()}"
            # Ensure uniqueness
            while Institution.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{generate_code()}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.label}"
    
