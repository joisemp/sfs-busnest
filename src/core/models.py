from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from . user_manager import UserManager
from services.models import Organisation
from django.utils.text import slugify
from config.utils import generate_unique_slug
from django.db.models.signals import post_delete
from django.dispatch import receiver
    
    
class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique = True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE, related_name='profile')
    org = models.ForeignKey(Organisation, null=True, on_delete=models.SET_NULL, related_name='org')
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    is_central_admin = models.BooleanField(_('is central admin'), default=False)
    is_institution_admin = models.BooleanField(_('is institution admin'), default=False)
    is_student = models.BooleanField(_('is student'), default=False)
    slug = models.SlugField(unique=True, db_index=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.first_name}-{self.last_name}{self.org}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{str(self.first_name)} {str(self.last_name)}"
    

# Signals
# Delete User that is associated with UserProfile on its delete
@receiver(post_delete, sender=UserProfile)
def delete_user_on_profile_delete(sender, instance, **kwargs):
    try:
        user = instance.user
        user.delete()
        print(f"User {user.email} and associated profile deleted successfully.")
    except Exception as e:
        print(f"Error occurred while deleting user: {str(e)}")    