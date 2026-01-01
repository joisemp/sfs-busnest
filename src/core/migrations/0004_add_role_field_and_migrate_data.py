# Generated migration for role field refactoring
from django.db import migrations, models
import django.contrib.postgres.fields


def migrate_roles_forward(apps, schema_editor):
    """
    Migrate existing boolean role fields to the new role CharField.
    Priority: central_admin > institution_admin > driver > student (default)
    """
    UserProfile = apps.get_model('core', 'UserProfile')
    
    for profile in UserProfile.objects.all():
        # Determine role based on priority
        if profile.is_central_admin:
            profile.role = 'central_admin'
        elif profile.is_institution_admin:
            profile.role = 'institution_admin'
        elif profile.is_driver:
            profile.role = 'driver'
        else:
            profile.role = 'student'
        
        profile.save()


def migrate_roles_backward(apps, schema_editor):
    """
    Reverse migration: Convert role field back to boolean fields.
    """
    UserProfile = apps.get_model('core', 'UserProfile')
    
    for profile in UserProfile.objects.all():
        # Reset all boolean fields
        profile.is_central_admin = False
        profile.is_institution_admin = False
        profile.is_driver = False
        profile.is_student = False
        
        # Set the appropriate boolean based on role
        if profile.role == 'central_admin':
            profile.is_central_admin = True
        elif profile.role == 'institution_admin':
            profile.is_institution_admin = True
        elif profile.role == 'driver':
            profile.is_driver = True
        else:
            profile.is_student = True
        
        profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_userprofile_is_driver'),
    ]

    operations = [
        # Step 1: Add the new role field (nullable for now)
        migrations.AddField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[
                    ('central_admin', 'Central Admin'),
                    ('institution_admin', 'Institution Admin'),
                    ('driver', 'Driver'),
                    ('student', 'Student')
                ],
                default='student',
                help_text='Role assigned to this user',
                max_length=50
            ),
        ),
        
        # Step 2: Migrate existing data from boolean fields to role field
        migrations.RunPython(migrate_roles_forward, migrate_roles_backward),
        
        # Step 3: Remove old boolean fields
        migrations.RemoveField(
            model_name='userprofile',
            name='is_central_admin',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='is_institution_admin',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='is_driver',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='is_student',
        ),
    ]
