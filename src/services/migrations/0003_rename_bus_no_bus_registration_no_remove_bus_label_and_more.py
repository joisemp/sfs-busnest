# Generated by Django 4.2 on 2025-01-20 08:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_alter_bus_slug_alter_busrequest_slug_alter_faq_slug_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bus',
            old_name='bus_no',
            new_name='registration_no',
        ),
        migrations.RemoveField(
            model_name='bus',
            name='label',
        ),
        migrations.RemoveField(
            model_name='bus',
            name='route',
        ),
        migrations.RemoveField(
            model_name='bus',
            name='schedule',
        ),
    ]
